"""Utilities for PyTorch device management."""
import torch
import logging

logger = logging.getLogger(__name__)

def get_device() -> torch.device:
    """Bestimmt das am besten geeignete verfügbare Gerät für PyTorch.

    Prüft nacheinander auf CUDA (NVIDIA GPU), MPS (Apple Silicon GPU) und CPU.

    Returns:
        torch.device: Das am besten geeignete verfügbare Gerät.
    """
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info("Verwende CUDA GPU.")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
        logger.info("Verwende Apple Silicon MPS GPU.")
    else:
        device = torch.device("cpu")
        logger.info("Keine GPU gefunden, verwende CPU.")
    return device
