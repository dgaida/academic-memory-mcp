"""Tests for mcp_university/utils/torch_utils.py."""
import torch
import unittest
from unittest.mock import patch, MagicMock
from mcp_university.utils.torch_utils import get_device

class TestTorchUtils(unittest.TestCase):
    """Test cases for PyTorch device management utilities."""

    def test_get_device_cuda(self) -> None:
        """Tests that get_device returns cuda device when CUDA is available.

        Args:
            None

        Returns:
            None
        """
        with patch("torch.cuda.is_available", return_value=True):
            device = get_device()
            self.assertEqual(device.type, "cuda")

    def test_get_device_mps(self) -> None:
        """Tests that get_device returns mps device when MPS is available and CUDA is not.

        Args:
            None

        Returns:
            None
        """
        with patch("torch.cuda.is_available", return_value=False):
            mock_mps = MagicMock()
            mock_mps.is_available.return_value = True
            with patch("torch.backends.mps", mock_mps, create=True):
                device = get_device()
                self.assertEqual(device.type, "mps")

    def test_get_device_cpu_no_mps_attr(self) -> None:
        """Tests get_device returns cpu device when hasattr(torch.backends, 'mps') is False.

        Args:
            None

        Returns:
            None
        """
        class FakeBackends:
            """Fake backends object without mps attribute."""
            pass

        with patch("torch.cuda.is_available", return_value=False):
            with patch("torch.backends", FakeBackends()):
                device = get_device()
                self.assertEqual(device.type, "cpu")

    def test_get_device_cpu_mps_not_available(self) -> None:
        """Tests get_device returns cpu device when MPS is not available.

        Args:
            None

        Returns:
            None
        """
        with patch("torch.cuda.is_available", return_value=False):
            mock_mps = MagicMock()
            mock_mps.is_available.return_value = False
            with patch("torch.backends.mps", mock_mps, create=True):
                device = get_device()
                self.assertEqual(device.type, "cpu")


if __name__ == "__main__":
    unittest.main()
