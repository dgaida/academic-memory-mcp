"""Tests to increase coverage of mcp_university/config.py."""

import os
import pathlib
from unittest.mock import patch
from typing import Any
from mcp_university.config import Config, get_config, FolderConfig


def test_config_default_dir() -> None:
    """Test Config initialization with default directory (config_dir=None).

    Returns:
        None
    """
    with patch("mcp_university.config.load_dotenv"):
        config = Config()
        assert config.config_dir is not None
        assert config.config_dir.name == "config"


def test_config_sync_vba_macros_no_macro_dir(tmp_path: pathlib.Path) -> None:
    """Test that _sync_vba_macros returns early if outlook_macro directory does not exist.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    # Create empty user.yaml, folders.yaml, ontology.yaml, models.yaml
    (cfg_dir / "user.yaml").write_text("name: 'Test'\nemail: 'test@example.com'", encoding="utf-8")
    (cfg_dir / "folders.yaml").write_text("folders: []", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    # Load Config with custom config_dir. The parent has no 'outlook_macro' directory.
    with patch("mcp_university.config.load_dotenv"):
        config = Config(config_dir=cfg_dir)
    assert config.user.email == "test@example.com"


def test_config_sync_vba_macros_no_user_email(tmp_path: pathlib.Path) -> None:
    """Test that _sync_vba_macros returns early if user.email is empty.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    # Create empty user.yaml with empty email
    (cfg_dir / "user.yaml").write_text("name: 'Test'\nemail: ''", encoding="utf-8")
    (cfg_dir / "folders.yaml").write_text("folders: []", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    # Create dummy outlook_macro directory
    macro_dir = tmp_path / "outlook_macro"
    macro_dir.mkdir()

    with patch("mcp_university.config.load_dotenv"):
        config = Config(config_dir=cfg_dir)
    assert config.user.email == ""


def test_config_sync_vba_macros_exceptions(tmp_path: pathlib.Path) -> None:
    """Test exception handling in _sync_vba_macros.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    (cfg_dir / "user.yaml").write_text("name: 'Test'\nemail: 'test@example.com'", encoding="utf-8")
    (cfg_dir / "folders.yaml").write_text("folders: []", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    # Create dummy outlook_macro directory
    macro_dir = tmp_path / "outlook_macro"
    macro_dir.mkdir()

    bas_file = macro_dir / "DummyExport.bas"
    bas_file.write_text('Private Const ACCOUNT_NAME As String = "daniel.gaida@th-koeln.de"', encoding="utf-8")

    # Case 1: Exception during read_text (e.g. mock read_text to raise an exception)
    def mock_read_text(self: pathlib.Path, *args: Any, **kwargs: Any) -> str:
        """Mock read_text to raise an exception.

        Args:
            self: The Path instance.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            IOError: Simulated file reading error.
        """
        raise IOError("Simulated read error")

    with patch("mcp_university.config.load_dotenv"):
        with patch.object(pathlib.Path, "read_text", mock_read_text):
            config = Config(config_dir=cfg_dir)

    # Case 2: Exception at the top-level of _sync_vba_macros (e.g. parent.exists() raises exception)
    original_exists = pathlib.Path.exists

    def mock_exists(self: pathlib.Path) -> bool:
        """Mock exists to raise an exception.

        Args:
            self: The Path instance.

        Returns:
            bool: Always raises Exception.

        Raises:
            Exception: Simulated error checking existence.
        """
        if "outlook_macro" in str(self):
            raise Exception("Simulated top-level error")
        return original_exists(self)

    with patch("mcp_university.config.load_dotenv"):
        with patch.object(pathlib.Path, "exists", mock_exists):
            config = Config(config_dir=cfg_dir)


def test_config_load_yaml_not_exists(tmp_path: pathlib.Path) -> None:
    """Test that loading a non-existent YAML file returns the default model instance.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    # Loading a non-existent folders.yaml should return default FolderConfig
    (cfg_dir / "user.yaml").write_text("name: 'Test'\nemail: 'test@example.com'", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    with patch("mcp_university.config.load_dotenv"):
        config = Config(config_dir=cfg_dir)
        assert isinstance(config.folders, FolderConfig)
        assert config.folders.folders == []


def test_config_load_raw_yaml_direct(tmp_path: pathlib.Path) -> None:
    """Test _load_raw_yaml directly covering all branches.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "user.yaml").write_text("name: 'Test'\nemail: 'test@example.com'", encoding="utf-8")
    (cfg_dir / "folders.yaml").write_text("folders: []", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    with patch("mcp_university.config.load_dotenv"):
        config = Config(config_dir=cfg_dir)
        # 1. Path does not exist
        assert config._load_raw_yaml(cfg_dir / "not_exist.yaml") == {}
        # 2. Path exists and is empty
        empty_yaml = cfg_dir / "empty.yaml"
        empty_yaml.write_text("", encoding="utf-8")
        assert config._load_raw_yaml(empty_yaml) == {}
        # 3. Path exists and has content
        content_yaml = cfg_dir / "content.yaml"
        content_yaml.write_text("key: value", encoding="utf-8")
        assert config._load_raw_yaml(content_yaml) == {"key": "value"}


def test_config_properties(tmp_path: pathlib.Path) -> None:
    """Test path properties of Config.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    (cfg_dir / "user.yaml").write_text("name: 'Test'\nemail: 'test@example.com'", encoding="utf-8")
    (cfg_dir / "folders.yaml").write_text("folders: []", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    with patch("mcp_university.config.load_dotenv"):
        config = Config(config_dir=cfg_dir)
        assert config.data_dir == tmp_path / "data"
        assert config.log_path == tmp_path / "data" / "logs"
        assert config.th_personal_path == tmp_path / "data" / "metadata" / "th_personal.db"
        assert config.sqlite_path == tmp_path / "data" / "metadata" / "university.db"
        assert config.qdrant_path == tmp_path / "data" / "indexes" / "qdrant"


def test_config_offline_mode(tmp_path: pathlib.Path) -> None:
    """Test offline mode behavior of Config.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    (cfg_dir / "user.yaml").write_text("name: 'Test'\nemail: 'test@example.com'", encoding="utf-8")
    (cfg_dir / "folders.yaml").write_text("folders: []", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    # Case 1: Offline is True
    with patch.dict(os.environ, {"MCP_UNIVERSITY_OFFLINE": "yes"}):
        with patch("mcp_university.config.load_dotenv"):
            config = Config(config_dir=cfg_dir)
            assert config.offline is True
            assert os.environ.get("HF_HUB_OFFLINE") == "1"
            assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"

    # Case 2: Offline is False
    with patch.dict(os.environ, {"MCP_UNIVERSITY_OFFLINE": "0"}):
        with patch("mcp_university.config.load_dotenv"):
            config = Config(config_dir=cfg_dir)
            assert config.offline is False


def test_get_config_singleton() -> None:
    """Test the get_config helper function.

    Returns:
        None
    """
    with patch("mcp_university.config.load_dotenv"):
        config = get_config()
        assert isinstance(config, Config)
