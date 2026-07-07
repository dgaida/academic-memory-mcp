import sys
from unittest.mock import MagicMock

# Mock problematic dependencies globally for tests
if "pytest" in sys.modules:
    sys.modules['torch'] = MagicMock()
    sys.modules['sentence_transformers'] = MagicMock()
    sys.modules['dotenv'] = MagicMock()
    sys.modules['numpy'] = MagicMock()
    sys.modules['qdrant_client'] = MagicMock()
    sys.modules['extract_msg'] = MagicMock()
    sys.modules['beautifulsoup4'] = MagicMock()
    sys.modules['bs4'] = MagicMock()

from . import utils
from . import agent
from . import mcp_server
