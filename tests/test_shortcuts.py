"""Tests for test_shortcuts.py."""
from pathlib import Path
from unittest.mock import patch, mock_open
from mcp_university.utils.shortcuts import resolve_path, resolve_lnk

def test_resolve_path_non_existent():
    """Test function docstring."""
    p = Path("non_existent_file_xyz.txt")
    assert resolve_path(p) == p

def test_resolve_path_regular_file(tmp_path):
    """Test function docstring."""
    p = tmp_path / "test.txt"
    p.touch()
    assert resolve_path(p) == p

def test_resolve_path_symlink(tmp_path):
    """Test function docstring."""
    target = tmp_path / "target.txt"
    target.touch()
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    assert resolve_path(link) == target.resolve()

def test_resolve_path_lnk_file(tmp_path):
    """Test function docstring."""
    lnk = tmp_path / "test.lnk"
    lnk.touch()
    target = tmp_path / "target.txt"
    target.touch()
    
    with patch("mcp_university.utils.shortcuts.resolve_lnk", return_value=target) as mock_resolve:
        assert resolve_path(lnk) == target
        mock_resolve.assert_called_once_with(lnk)

def test_resolve_lnk_invalid_header():
    """Test function docstring."""
    with patch("builtins.open", mock_open(read_data=b"INVALID")):
        assert resolve_lnk(Path("test.lnk")) is None

def test_resolve_lnk_too_short():
    """Test function docstring."""
    with patch("builtins.open", mock_open(read_data=b"L\x00\x00\x00" + b"\x00"*10)):
        assert resolve_lnk(Path("test.lnk")) is None

def test_resolve_lnk_minimal_valid_structure():
    """Test function docstring."""
    # Header 76 bytes. 
    # data[0:4] == b'L\x00\x00\x00'
    # flags at data[20:24]. Let's say no flags.
    header = b'L\x00\x00\x00' + b'\x00' * 16 + b'\x00\x00\x00\x00' + b'\x00' * 52
    with patch("builtins.open", mock_open(read_data=header)):
        assert resolve_lnk(Path("test.lnk")) is None

def test_resolve_lnk_with_local_base_path():
    """Test function docstring."""
    # flags & 0x02 (HasLinkInfo)
    flags = 0x02
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    
    # LinkInfo structure
    # offset 76: link_info_size (4 bytes)
    # offset 80: link_info_header_size (4 bytes)
    # offset 92: local_base_path_offset (4 bytes)
    
    local_path = b"C:\\Target\\Path\x00"
    link_info_header_size = 28
    local_base_path_offset = 28
    link_info_size = link_info_header_size + len(local_path)
    
    link_info = link_info_size.to_bytes(4, 'little') +                 link_info_header_size.to_bytes(4, 'little') +                 b'\x00' * 8 +                 local_base_path_offset.to_bytes(4, 'little') +                 b'\x00' * 8 +                 local_path
    
    data = header + link_info
    
    with patch("builtins.open", mock_open(read_data=data)):
        result = resolve_lnk(Path("test.lnk"))
        # Compare strings to avoid PosixPath vs WindowsPath issues on Linux
        assert str(result).replace('\\', '/') == "C:/Target/Path"

def test_resolve_lnk_with_relative_path():
    """Test function docstring."""
    # flags & 0x08 (HasRelativePath)
    flags = 0x08
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    
    # RelativePath is in StringData.
    rel_path_str = "target.txt"
    rel_path_data = len(rel_path_str).to_bytes(2, 'little') + rel_path_str.encode('cp1252')
    
    data = header + rel_path_data
    
    lnk_path = Path("/tmp/test.lnk")
    with patch("builtins.open", mock_open(read_data=data)):
        with patch("pathlib.Path.resolve", return_value=Path("/tmp/target.txt")):
            result = resolve_lnk(lnk_path)
            assert result == Path("/tmp/target.txt")

def test_resolve_lnk_exception():
    """Test function docstring."""
    with patch("builtins.open", side_effect=Exception("Read error")):
        assert resolve_lnk(Path("test.lnk")) is None

def test_resolve_lnk_with_id_list():
    """Test function docstring."""
    # flags & 0x01 (HasTargetIDList)
    flags = 0x01
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    
    id_list_size = 10
    id_list = id_list_size.to_bytes(2, 'little') + b'\x00' * id_list_size
    
    # After IDList, let's put a relative path
    flags |= 0x08
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    
    rel_path_str = "target.txt"
    rel_path_data = len(rel_path_str).to_bytes(2, 'little') + rel_path_str.encode('cp1252')
    
    data = header + id_list + rel_path_data
    
    with patch("builtins.open", mock_open(read_data=data)):
        with patch("pathlib.Path.resolve", return_value=Path("/tmp/target.txt")):
            result = resolve_lnk(Path("/tmp/test.lnk"))
            assert result == Path("/tmp/target.txt")


def test_resolve_lnk_id_list_too_short() -> None:
    """Tests that resolve_lnk returns None when ID list exists but data is too short.

    Args:
        None

    Returns:
        None
    """
    flags = 0x01
    data = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    with patch("builtins.open", mock_open(read_data=data)):
        assert resolve_lnk(Path("test.lnk")) is None


def test_resolve_lnk_link_info_skip_fallback() -> None:
    """Tests that resolve_lnk skips LinkInfo and falls back to RelativePath if absolute path fails.

    Args:
        None

    Returns:
        None
    """
    flags = 0x02 | 0x08
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    link_info_size = 4
    link_info = link_info_size.to_bytes(4, 'little')
    rel_path_str = "target.txt"
    rel_path_data = len(rel_path_str).to_bytes(2, 'little') + rel_path_str.encode('cp1252')
    data = header + link_info + rel_path_data

    with patch("builtins.open", mock_open(read_data=data)):
        with patch("pathlib.Path.resolve", return_value=Path("/tmp/target.txt")):
            result = resolve_lnk(Path("/tmp/test.lnk"))
            assert result == Path("/tmp/target.txt")


def test_resolve_lnk_with_name_and_relative_path() -> None:
    """Tests that resolve_lnk correctly skips the Name field when HasName is set.

    Args:
        None

    Returns:
        None
    """
    flags = 0x04 | 0x08
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    name_str = "MyLinkName"
    name_data = len(name_str).to_bytes(2, 'little') + name_str.encode('cp1252')
    rel_path_str = "target.txt"
    rel_path_data = len(rel_path_str).to_bytes(2, 'little') + rel_path_str.encode('cp1252')
    data = header + name_data + rel_path_data

    with patch("builtins.open", mock_open(read_data=data)):
        with patch("pathlib.Path.resolve", return_value=Path("/tmp/target.txt")):
            result = resolve_lnk(Path("/tmp/test.lnk"))
            assert result == Path("/tmp/target.txt")


def test_resolve_lnk_with_name_unicode_and_relative_path() -> None:
    """Tests that resolve_lnk correctly skips Name field under Unicode.

    Args:
        None

    Returns:
        None
    """
    flags = 0x04 | 0x08 | 0x80
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    name_str = "MyLinkName"
    name_data = len(name_str).to_bytes(2, 'little') + name_str.encode('utf-16le')
    rel_path_str = "target.txt"
    rel_path_data = len(rel_path_str).to_bytes(2, 'little') + rel_path_str.encode('utf-16le')
    data = header + name_data + rel_path_data

    with patch("builtins.open", mock_open(read_data=data)):
        with patch("pathlib.Path.resolve", return_value=Path("/tmp/target.txt")):
            result = resolve_lnk(Path("/tmp/test.lnk"))
            assert result == Path("/tmp/target.txt")


def test_resolve_lnk_resolve_exception() -> None:
    """Tests that resolve_lnk handles resolve exception gracefully.

    Args:
        None

    Returns:
        None
    """
    flags = 0x08
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    rel_path_str = "target.txt"
    rel_path_data = len(rel_path_str).to_bytes(2, 'little') + rel_path_str.encode('cp1252')
    data = header + rel_path_data

    with patch("builtins.open", mock_open(read_data=data)):
        with patch("pathlib.Path.resolve", side_effect=OSError("Resolve failed")):
            result = resolve_lnk(Path("/tmp/test.lnk"))
            assert result is None


def test_resolve_path_non_existent_lnk() -> None:
    """Tests resolve_path on non-existent .lnk file.

    Args:
        None

    Returns:
        None
    """
    lnk = Path("non_existent_file.lnk")
    assert resolve_path(lnk) == lnk


def test_resolve_path_symlink_exception() -> None:
    """Tests that resolve_path returns original path when symlink resolution raises exception.

    Args:
        None

    Returns:
        None
    """
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.is_symlink", return_value=True):
            with patch("pathlib.Path.resolve", side_effect=OSError("Symlink loop/broken")):
                p = Path("symlink_broken")
                assert resolve_path(p) == p

def test_resolve_lnk_unicode_relative_path():
    """Test function docstring."""
    # flags & 0x08 (HasRelativePath) and flags & 0x80 (IsUnicode)
    flags = 0x08 | 0x80
    header = b'L\x00\x00\x00' + b'\x00' * 16 + flags.to_bytes(4, 'little') + b'\x00' * 52
    
    rel_path_str = "target.txt"
    rel_path_data = len(rel_path_str).to_bytes(2, 'little') + rel_path_str.encode('utf-16le')
    
    data = header + rel_path_data
    
    with patch("builtins.open", mock_open(read_data=data)):
        with patch("pathlib.Path.resolve", return_value=Path("/tmp/target.txt")):
            result = resolve_lnk(Path("/tmp/test.lnk"))
            assert result == Path("/tmp/target.txt")
