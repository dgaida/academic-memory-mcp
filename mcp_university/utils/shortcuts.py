"""Utility functions for resolving file shortcuts and symlinks."""
import struct
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def resolve_lnk(lnk_path: Path) -> Optional[Path]:
    """
    Best-effort parsing of Windows .lnk files to extract the target path.
    Based on Shell Link Binary Format (MS-SHLLINK).

    Args:
        lnk_path (Path): Path to the .lnk file.

    Returns:
        Optional[Path]: The resolved target path if successful, otherwise None.
    """
    try:
        with open(lnk_path, 'rb') as f:
            data = f.read()

        if len(data) < 76 or data[0:4] != b'L\x00\x00\x00':
            return None

        flags = struct.unpack('<I', data[20:24])[0]
        offset = 76

        if flags & 0x01:  # HasTargetIDList
            if len(data) < offset + 2:
                return None
            id_list_size = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2 + id_list_size

        # Try LinkInfo first (Absolute Path)
        if flags & 0x02:  # HasLinkInfo
            if len(data) >= offset + 4:
                link_info_size = struct.unpack('<I', data[offset:offset+4])[0]
                if len(data) >= offset + link_info_size:
                    link_info = data[offset:offset+link_info_size]
                    if len(link_info) >= 20:
                        local_base_path_offset = struct.unpack('<I', link_info[16:20])[0]
                        if local_base_path_offset and local_base_path_offset < len(link_info):
                            path_bytes = link_info[local_base_path_offset:]
                            null_idx = path_bytes.find(b'\x00')
                            if null_idx != -1:
                                path_str = path_bytes[:null_idx].decode('cp1252', errors='replace')
                                return Path(path_str)

        # Fallback to RelativePath in StringData
        string_offset = offset
        if flags & 0x02:  # Skip LinkInfo
            link_info_size = struct.unpack('<I', data[offset:offset+4])[0]
            string_offset += link_info_size

        # Name
        if flags & 0x04:  # HasName
            if len(data) >= string_offset + 2:
                u_len = struct.unpack('<H', data[string_offset:string_offset+2])[0]
                string_offset += 2 + (u_len * 2 if flags & 0x80 else u_len)

        # RelativePath
        if flags & 0x08:  # HasRelativePath
            if len(data) >= string_offset + 2:
                u_len = struct.unpack('<H', data[string_offset:string_offset+2])[0]
                is_unicode = bool(flags & 0x80)
                path_data_len = u_len * 2 if is_unicode else u_len
                path_data = data[string_offset+2 : string_offset+2+path_data_len]
                if is_unicode:
                    rel_path = path_data.decode('utf-16le', errors='replace')
                else:
                    rel_path = path_data.decode('cp1252', errors='replace')

                try:
                    return (lnk_path.parent / rel_path).resolve()
                except Exception:
                    pass

    except Exception as e:
        logger.debug(f"Failed to parse .lnk file {lnk_path}: {e}")

    return None

def resolve_path(path: Path) -> Path:
    """
    Resolves symlinks and .lnk files.

    Args:
        path (Path): Path to resolve.

    Returns:
        Path: The resolved path if successful, otherwise the original path.
    """
    if not path.exists():
        # If it doesn't exist, it might be a broken symlink or .lnk
        # We still try to resolve .lnk if the file itself exists
        if not path.is_symlink() and path.suffix.lower() == '.lnk':
            pass # continue to .lnk check
        else:
            return path

    # Handle symlinks (OS level)
    if path.is_symlink():
        try:
            return path.resolve()
        except Exception:
            return path

    # Handle Windows .lnk files
    if path.suffix.lower() == '.lnk':
        target = resolve_lnk(path)
        if target and target.exists():
            return target

    return path
