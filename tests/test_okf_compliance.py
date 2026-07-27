"""Tests for OKF v0.2 email compliance check and attested computation tool."""

from pathlib import Path
from datetime import datetime, timedelta
import yaml
import pytest
from unittest.mock import MagicMock, patch

from mcp_university.agent.engine import Agent
from email_classifier.controller import EmailController


@pytest.fixture
def temp_okf_bundle(tmp_path: Path) -> Path:
    """Creates a temporary mock OKF bundle directory with concept files.

    Args:
        tmp_path: Pytest temporary directory path.

    Returns:
        The Path to the temporary OKF bundle.
    """
    okf_dir = tmp_path / "okf"
    okf_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir = okf_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Valid Attested Computation Concept
    valid_concept_content = """---
type: Attested Computation
status: stable
stale_after: 2099-12-31
parameters:
  - x
  - y
executor:
  resource: python_calc
attester:
  resource: py_attester
---
# Computation
```python
result = x + y
```
"""
    (concepts_dir / "calc_sum.md").write_text(valid_concept_content, encoding="utf-8")

    # 2. Stale Attested Computation Concept
    stale_concept_content = """---
type: Attested Computation
status: stable
stale_after: 2020-01-01
parameters:
  - x
executor:
  resource: python_calc
attester:
  resource: py_attester
---
# Computation
```python
result = x * 2
```
"""
    (concepts_dir / "calc_stale.md").write_text(stale_concept_content, encoding="utf-8")

    # 3. Deprecated Attested Computation Concept
    deprecated_concept_content = """---
type: Attested Computation
status: deprecated
stale_after: 2099-12-31
parameters:
  - x
executor:
  resource: python_calc
attester:
  resource: py_attester
---
# Computation
```python
result = x * 3
```
"""
    (concepts_dir / "calc_deprecated.md").write_text(deprecated_concept_content, encoding="utf-8")

    # 4. Wrong Type Concept
    wrong_type_content = """---
type: Reference
status: stable
---
# Not a computation
"""
    (concepts_dir / "not_calc.md").write_text(wrong_type_content, encoding="utf-8")

    return okf_dir


@pytest.fixture
def mock_controller_deps(tmp_path: Path):
    """Mocks dependencies for EmailController.

    Args:
        tmp_path: Pytest temporary directory path.

    Yields:
        A tuple of (EmailController, config_mock).
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    config_path = config_dir / "folders.yaml"
    memory_config_path = config_dir / "classifier_memory_paths.yaml"

    class_paths = {"PAV_PO-Wechsel": str(tmp_path / "exams")}
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump({"class_paths": class_paths}, f)

    memory_paths = {"PAV_PO-Wechsel": str(tmp_path / "okf")}
    with open(memory_config_path, "w", encoding="utf-8") as f:
        yaml.dump({"class_paths": memory_paths}, f)

    with patch("email_classifier.controller.MEMORY_CONFIG_PATH", memory_config_path):
        with patch('email_classifier.controller.get_config') as mock_get_config:
            mock_cfg = MagicMock()
            mock_cfg.config_dir = config_dir
            mock_cfg.data_dir = tmp_path / "data"
            mock_cfg.data_dir.mkdir()
            mock_cfg.embeddings.model = "test-emb-model"
            mock_cfg.user.emails = ["prof@th-koeln.de"]
            mock_get_config.return_value = mock_cfg

            with patch('email_classifier.controller.MCPAgent'), \
                 patch('email_classifier.controller.Agent'), \
                 patch('email_classifier.controller.Summarizer'):
                controller = EmailController(config_path=str(config_path))
                controller.class_to_memory_index = {"PAV_PO-Wechsel": "exam_memory"}
                yield controller, mock_cfg


def test_controller_adds_okf_bundle_path_and_skill(mock_controller_deps: tuple, tmp_path: Path) -> None:
    """Verifies that EmailController appends SKILL_okfv02.md and supplies OKF_BUNDLE_PATH for PAV_PO-Wechsel.

    Args:
        mock_controller_deps: Mocked controller dependencies.
        tmp_path: Pytest temporary directory path.

    Returns:
        None
    """
    controller, _ = mock_controller_deps

    # Setup skills directory mock and files
    skills_dir = Path("skills")
    skills_dir.mkdir(exist_ok=True)

    # Ensure SKILL_okfv02.md content exists
    okf_skill = skills_dir / "SKILL_okfv02.md"
    okf_skill_existed = okf_skill.exists()
    if not okf_skill_existed:
        okf_skill.write_text("okf-email-compliance rules and checks", encoding="utf-8")

    try:
        # Define a mock mail path
        mail_path = tmp_path / "student_mail.msg"
        mail_path.write_text("Draft my reply please.", encoding="utf-8")

        with patch.object(controller.mail_parser, 'parse', return_value="Draft my reply please."), \
             patch.object(controller.mail_parser, 'extract_latest_message', return_value="Draft my reply please."), \
             patch.object(controller.agent, 'chat', side_effect=[
                 "NO_APPOINTMENT_RELEVANCE",
                 "TEXT: Response Draft"
             ]) as mock_chat:

            controller.generate_reply(
                mail_path=mail_path,
                email_class="PAV_PO-Wechsel",
                action_idx=0
            )

            # Check that Agent.chat was called multiple times
            assert mock_chat.call_count == 2

            # The 2nd call is Step 2 (Regular Reply) where skill_content is passed
            step2_call_args = mock_chat.call_args_list[1][1]
            step2_prompt = step2_call_args["messages"][0]["content"]

            # Assert OKF_BUNDLE_PATH was injected
            assert "OKF_BUNDLE_PATH" in step2_prompt
            # Assert SKILL_okfv02.md content was appended to prompt
            assert "okf-email-compliance" in step2_prompt or "okfv02" in step2_prompt

    finally:
        # Clean up temporary mock file if we created it
        if not okf_skill_existed and okf_skill.exists():
            okf_skill.unlink()


def test_execute_okf_computation_success(temp_okf_bundle: Path) -> None:
    """Tests execute_okf_computation tool on a valid concept with correct parameters.

    Args:
        temp_okf_bundle: Path to the temporary OKF bundle.

    Returns:
        None
    """
    # Create an agent instance
    agent = Agent()
    concept_path = str(temp_okf_bundle / "concepts" / "calc_sum.md")

    # Run sum computation
    res = agent._tool_execute_okf_computation(concept_path, {"x": 10, "y": 20})

    assert "ERFOLG" in res
    assert "Ergebnis: 30" in res
    assert "Job ID: job_" in res


def test_execute_okf_computation_stale_gates(temp_okf_bundle: Path) -> None:
    """Tests execute_okf_computation tool refuses execution when stale_after has passed.

    Args:
        temp_okf_bundle: Path to the temporary OKF bundle.

    Returns:
        None
    """
    agent = Agent()
    concept_path = str(temp_okf_bundle / "concepts" / "calc_stale.md")

    # Run stale computation
    res = agent._tool_execute_okf_computation(concept_path, {"x": 5})

    assert "FEHLER" in res
    assert "veraltet" in res
    assert "stale_after" in res


def test_execute_okf_computation_deprecated_gates(temp_okf_bundle: Path) -> None:
    """Tests execute_okf_computation tool refuses execution when status is deprecated.

    Args:
        temp_okf_bundle: Path to the temporary OKF bundle.

    Returns:
        None
    """
    agent = Agent()
    concept_path = str(temp_okf_bundle / "concepts" / "calc_deprecated.md")

    # Run deprecated computation
    res = agent._tool_execute_okf_computation(concept_path, {"x": 4})

    assert "FEHLER" in res
    assert "veraltet" in res
    assert "deprecated" in res


def test_execute_okf_computation_missing_param_fails(temp_okf_bundle: Path) -> None:
    """Tests execute_okf_computation tool fails when required parameters are missing.

    Args:
        temp_okf_bundle: Path to the temporary OKF bundle.

    Returns:
        None
    """
    agent = Agent()
    concept_path = str(temp_okf_bundle / "concepts" / "calc_sum.md")

    # y parameter is missing
    res = agent._tool_execute_okf_computation(concept_path, {"x": 10})

    assert "FEHLER" in res
    assert "Parameter 'y' fehlt" in res


def test_execute_okf_computation_wrong_type_fails(temp_okf_bundle: Path) -> None:
    """Tests execute_okf_computation tool fails when concept is not of type Attested Computation.

    Args:
        temp_okf_bundle: Path to the temporary OKF bundle.

    Returns:
        None
    """
    agent = Agent()
    concept_path = str(temp_okf_bundle / "concepts" / "not_calc.md")

    res = agent._tool_execute_okf_computation(concept_path, {})

    assert "FEHLER" in res
    assert "nicht vom Typ 'Attested Computation'" in res
