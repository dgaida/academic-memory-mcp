"""Tests for test_profiler_extended.py."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta
from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def mock_profiler_deps():
    """Test function."""
    with patch('mcp_university.summarizer.profiler.get_config') as mock_get:
        cfg = MagicMock()
        cfg.data_dir = Path("/tmp/data")
        cfg.llm.model = "m"
        cfg.llm.base_url = "http://b"
        mock_get.return_value = cfg
        
        with patch('mcp_university.summarizer.profiler.MetadataStore'),              patch('mcp_university.summarizer.profiler.MailParser'),              patch('mcp_university.summarizer.profiler.LLMClientWrapper'),              patch('mcp_university.summarizer.profiler.ProfileStore'):
            yield cfg

def test_profiler_init_fallback(tmp_path):
    """Tests test_profiler_init_fallback."""
    # Force exception in storage_path.mkdir
    with patch('mcp_university.summarizer.profiler.get_config') as mock_get:
        cfg = MagicMock()
        cfg.data_dir = tmp_path / "data"
        mock_get.return_value = cfg
        
        with patch('mcp_university.summarizer.profiler.MetadataStore'),              patch('mcp_university.summarizer.profiler.MailParser'),              patch('mcp_university.summarizer.profiler.LLMClientWrapper'),              patch('mcp_university.summarizer.profiler.ProfileStore'):
            
            with patch('pathlib.Path.mkdir', side_effect=[Exception("fail"), None]):
                profiler = PersonProfiler(storage_path=Path("/invalid/path"))
                assert profiler.storage_path == Path("Steckbriefe")

def test_optimize_batches_gap(mock_profiler_deps):
    """Tests test_optimize_batches_gap."""
    profiler = PersonProfiler()
    
    date1 = datetime(2024, 1, 1)
    date2 = date1 + timedelta(days=100) # Large gap
    date3 = date2 + timedelta(days=1)
    
    all_emails = [
        {"details": {"date": date1, "body": "B1"}},
        {"details": {"date": date2, "body": "B2"}},
        {"details": {"date": date3, "body": "B3"}}
    ]
    
    # Need to trigger the gaps logic: len(all_emails) >= 2
    # and avg_gap * 2 < gap or gap > 30 days
    # In my case: gap1 = 100 days, gap2 = 1 day. avg = 50.5. threshold = max(101, 30) = 101.
    # Ah, threshold is max(avg*2, 30 days). So 100 days is NOT > 101.
    # Let's make it more extreme.
    
    date1 = datetime(2024, 1, 1)
    date2 = date1 + timedelta(days=200) 
    date3 = date2 + timedelta(days=1)
    # gaps = [200, 1]. avg = 100.5. threshold = 201. Still not >.
    
    # Use only 2 emails to make avg easy.
    all_emails = [
        {"details": {"date": date1, "body": "B1"}},
        {"details": {"date": date1 + timedelta(days=40), "body": "B2"}}
    ]
    # gap = 40. avg = 40. threshold = max(80, 30) = 80. Still 40 < 80.
    
    # If I have [date1, date1+40, date1+41]
    # gaps = [40, 1]. avg = 20.5. threshold = max(41, 30) = 41. 
    # Still 40 is NOT > 41.
    
    # Try: [date1, date1+100, date1+101]
    # gaps = [100, 1]. avg = 50.5. threshold = max(101, 30) = 101.
    
    # The only way is to have one gap MUCH larger than others.
    # [date1, date1+1000, date1+1001] -> gaps [1000, 1]. avg 500.5. threshold 1001.
    
    # Wait, the threshold is max(avg_gap * 2, 30 days).
    # If I have [date1, date1+40] -> gaps [40]. avg 40. threshold 80.
    
    # Let's use 3 emails: [0, 100, 101] -> gaps [100, 1]. avg 50.5. threshold 101.
    # [0, 200, 201] -> gaps [200, 1]. avg 100.5. threshold 201.
    
    # If I want it to split, gap must be > threshold.
    # [0, 31, 32] -> gaps [31, 1]. avg 16. threshold max(32, 30) = 32. 31 < 32.
    
    # [0, 61, 62, 63] -> gaps [61, 1, 1]. avg 21. threshold max(42, 30) = 42.
    # 61 > 42! SUCCESS.
    
    d = datetime(2024, 1, 1)
    all_emails = [
        {"details": {"date": d, "body": "B1"}},
        {"details": {"date": d + timedelta(days=61), "body": "B2"}},
        {"details": {"date": d + timedelta(days=62), "body": "B3"}},
        {"details": {"date": d + timedelta(days=63), "body": "B4"}}
    ]
    
    batches = [all_emails]
    optimized = profiler._optimize_batches(batches)
    assert len(optimized) >= 2

def test_optimize_batches_too_large(mock_profiler_deps):
    """Tests test_optimize_batches_too_large."""
    profiler = PersonProfiler()
    
    all_emails = [
        {"details": {"date": datetime.now(), "body": "A" * 15000}},
        {"details": {"date": datetime.now(), "body": "B" * 15000}}
    ]
    
    batches = [all_emails]
    optimized = profiler._optimize_batches(batches)
    assert len(optimized) == 2
