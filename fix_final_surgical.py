import re
from pathlib import Path

path = Path("mcp_university/classifier/controller.py")
content = path.read_text(encoding="utf-8")

# Fix multiple _detect_language if any
# Actually it seems I inserted it twice or re-insertion happened.
# I'll just restore from master first.
