"""Tests to increase coverage of mcp_university/cli/memory.py."""

import pathlib
from typer.testing import CliRunner
from unittest.mock import patch, mock_open, MagicMock
from mcp_university.cli.main import app


def test_memory_update_non_existent_config() -> None:
    """Test memory_update command with a non-existent configuration file.

    Returns:
        None
    """
    runner = CliRunner()
    with patch("mcp_university.cli.main.setup_logging"):
        result = runner.invoke(app, ["memory", "update", "-c", "non_existent_file.yaml"])
    assert result.exit_code == 0


def test_memory_update_empty_class_paths() -> None:
    """Test memory_update command with a configuration missing class_paths.

    Returns:
        None
    """
    runner = CliRunner()
    original_exists = pathlib.Path.exists

    def custom_exists(self: pathlib.Path) -> bool:
        """Mocked exists function.

        Args:
            self: The Path instance.

        Returns:
            bool: True if the path should exist in the test scenario.
        """
        if "empty_config.yaml" in str(self):
            return True
        return original_exists(self)

    with patch.object(pathlib.Path, "exists", custom_exists):
        with patch("mcp_university.cli.memory.open", mock_open(read_data="class_paths: null")):
            with patch("mcp_university.cli.main.setup_logging"):
                result = runner.invoke(app, ["memory", "update", "-c", "empty_config.yaml"])
    assert result.exit_code == 0


@patch("mcp_university.cli.memory.process_memory_folder")
@patch("mcp_university.cli.memory.SearchIndex")
@patch("mcp_university.cli.memory.ParserFactory")
@patch("mcp_university.cli.memory.AutoTokenizer")
@patch("mcp_university.cli.memory.get_config")
@patch("mcp_university.cli.memory.resolve_memory_index_names")
@patch("mcp_university.cli.memory.yaml.safe_load")
def test_memory_update_partial_exists(
    mock_load: MagicMock,
    mock_resolve: MagicMock,
    mock_config: MagicMock,
    mock_tokenizer: MagicMock,
    mock_pf: MagicMock,
    mock_idx: MagicMock,
    mock_process: MagicMock
) -> None:
    """Test memory_update command when one base_path exists and another does not.

    Args:
        mock_load: Mock safe_load.
        mock_resolve: Mock resolve_memory_index_names.
        mock_config: Mock get_config.
        mock_tokenizer: Mock AutoTokenizer.
        mock_pf: Mock ParserFactory.
        mock_idx: Mock SearchIndex.
        mock_process: Mock process_memory_folder.

    Returns:
        None
    """
    runner = CliRunner()
    mock_load.return_value = {
        "class_paths": {
            "class1": "/existent_path",
            "class2": "/non_existent_path"
        }
    }
    mock_resolve.return_value = {
        "class1": "index1",
        "class2": "index2"
    }

    original_exists = pathlib.Path.exists

    def custom_exists(self: pathlib.Path) -> bool:
        """Mocked exists function.

        Args:
            self: The Path instance.

        Returns:
            bool: True if the path should exist in the test scenario.
        """
        path_str = str(self)
        if "some_config.yaml" in path_str:
            return True
        if "non_existent_path" in path_str:
            return False
        if "existent_path" in path_str:
            return True
        return original_exists(self)

    with patch.object(pathlib.Path, "exists", custom_exists):
        with patch("mcp_university.cli.memory.open", mock_open(read_data="class_paths: {}")):
            with patch("mcp_university.cli.main.setup_logging"):
                result = runner.invoke(app, ["memory", "update", "-c", "some_config.yaml"])

    assert result.exit_code == 0
