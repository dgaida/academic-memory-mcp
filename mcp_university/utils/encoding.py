"""Utilities for handling string encodings."""
import email.header
import logging

logger = logging.getLogger(__name__)

def decode_mime_header(s: str) -> str:
    """Decodes an RFC 2047 encoded MIME header.

    Args:
        s (str): The string to decode.

    Returns:
        str: The decoded string.
    """
    if not s or not isinstance(s, str):
        return s
    
    try:
        decoded_parts = email.header.decode_header(s)
        decoded_str = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or 'utf-8', errors='replace')
            else:
                decoded_str += part
        # Clean up any remaining artifacts like quotes that sometimes surround decoded names
        return decoded_str.strip().strip("'\"")
    except Exception as e:
        logger.error(f"Error decoding MIME header {s}: {e}")
        return s
