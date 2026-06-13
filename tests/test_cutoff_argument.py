import pytest
import argparse
from datetime import datetime
from process_sorted_emails import valid_date

def test_valid_date_correct():
    d = valid_date("2024-05-20")
    assert d == datetime(2024, 5, 20)

def test_valid_date_invalid():
    with pytest.raises(argparse.ArgumentTypeError):
        valid_date("20-05-2024")
    with pytest.raises(argparse.ArgumentTypeError):
        valid_date("invalid")
