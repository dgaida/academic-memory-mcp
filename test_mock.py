from unittest.mock import MagicMock, patch
import sys
mock_win32 = MagicMock()
sys.modules["win32com"] = mock_win32
sys.modules["win32com.client"] = mock_win32.client

import win32com.client

def test():
    with patch("win32com.client.Dispatch", side_effect=Exception("fail")):
        try:
            win32com.client.Dispatch("test")
            print("No exception")
        except Exception:
            print("Caught exception")

test()
