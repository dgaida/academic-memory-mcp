import sys
from zoneinfo import ZoneInfo

file_path = 'process_sorted_emails.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add ZoneInfo import
if 'from zoneinfo import ZoneInfo' not in content:
    content = content.replace('from datetime import datetime, timedelta', 'from datetime import datetime, timedelta\nfrom zoneinfo import ZoneInfo')

# Update HEUTE IST in prompts
content = content.replace(
    "HEUTE IST: {datetime.now().strftime('%A, den %d.%m.%Y %H:%M')}",
    "HEUTE IST: {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%A, den %d.%m.%Y %H:%M')}"
)

content = content.replace(
    '        if "NO_APPOINTMENT_RELEVANCE" not in content:',
    '        # Erklärung: "ANHANG: JA" im Agent-Output dient als Signal für das Skript,\n        # ob Dateien (wie PO-Wechsel-Infos) angehängt werden sollen.\n        if "NO_APPOINTMENT_RELEVANCE" not in content:'
)

content = content.replace(
    '            should_attach = "ANHANG: JA" in content',
    '            # Signalprüfung für Anhänge (z.B. PO-Infos)\n            should_attach = "ANHANG: JA" in content'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
