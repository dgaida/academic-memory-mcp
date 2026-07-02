"""Tests für die Termin-Sortierung in der GUI."""
import pandas as pd
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from scripts.appointment_gui import parse_appointments

def test_parse_appointments_sorting_and_range(tmp_path):
    """Prüft ob alle Termine sortiert sind und der Zeitraum korrekt ist.

    Args:
        tmp_path: Temporäres Verzeichnis für Testdaten.
    """
    # Setup mock data directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Mock config to point to our temp data directory
    mock_config = MagicMock()
    mock_config.data_dir = data_dir

    now = datetime.now()
    # Today 10:00
    t1 = (now.replace(hour=10, minute=0)).strftime("%Y-%m-%d %H:%M")
    # Tomorrow 09:00
    t2 = (now + timedelta(days=1)).replace(hour=9, minute=0).strftime("%Y-%m-%d %H:%M")
    # Today 14:00 (In file after tomorrow's appointment)
    t3 = (now.replace(hour=14, minute=0)).strftime("%Y-%m-%d %H:%M")

    # Past appointment (should be excluded)
    t_past = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    # Future appointment (within 7 days)
    t_future = (now + timedelta(days=6)).strftime("%Y-%m-%d %H:%M")
    # Too far future (should be excluded)
    t_far_future = (now + timedelta(days=8)).strftime("%Y-%m-%d %H:%M")

    # Mock appointments.md with different "calendars" (sections)
    # We put them out of chronological order to test sorting
    content = f"""
# Kalender Privat
| Start | Betreff | Teilnehmer |
| --- | --- | --- |
| {t2} | Morgen Termin | Privat |
| {t_past} | Gestern | Privat |

# Kalender Arbeit
| Start | Betreff | Teilnehmer |
| --- | --- | --- |
| {t1} | Heute Früh | Arbeit |
| {t3} | Heute Nachmittag | Arbeit |
| {t_future} | Nächste Woche | Arbeit |
| {t_far_future} | In 8 Tagen | Arbeit |
"""

    appointments_file = data_dir / "appointments.md"
    appointments_file.write_text(content, encoding="utf-8")

    with patch("scripts.appointment_gui.get_config", return_value=mock_config):
        df = parse_appointments()

    # Assertions
    # 1. Past and far future appointments should be excluded
    # Expected: t1 (Today 10:00), t3 (Today 14:00), t2 (Tomorrow 09:00), t_future (6 days)
    assert len(df) == 4

    # 2. Check sorting
    starts = df["Start"].tolist()
    # Convert to datetime for comparison
    dt_starts = [datetime.strptime(s, "%Y-%m-%d %H:%M") for s in starts]

    # Check if they are strictly non-decreasing
    for i in range(len(dt_starts) - 1):
        assert dt_starts[i] <= dt_starts[i+1], f"Appointments not sorted: {starts[i]} before {starts[i+1]}"

    # Check specific order
    assert "Heute Früh" in df.iloc[0]["Betreff"]
    assert "Heute Nachmittag" in df.iloc[1]["Betreff"]
    assert "Morgen Termin" in df.iloc[2]["Betreff"]
    assert "Nächste Woche" in df.iloc[3]["Betreff"]

def run_tests():
    """Hilfsfunktion zum Ausführen der Tests."""
    pytest.main([__file__])

if __name__ == "__main__":
    run_tests()
