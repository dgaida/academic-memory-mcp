import sys
from pathlib import Path

path = Path('docs/de/usage/email-workflow.md')
content = path.read_text(encoding='utf-8')

old_info = '''!!! info "SentItems Archivierung"
    E-Mails im Ordner `SentItems` werden grundsätzlich nur archiviert. Sie benötigen nie eine Antwort-Aktion, unabhängig von ihrem Alter oder dem Status der Konversation.'''

new_info = '''!!! info "Automatische Archivierung"
    Das System schlägt für bestimmte E-Mails automatisch die Aktion **"4) Nur archivieren"** vor:
    - **Alte E-Mails:** E-Mails, die älter als der konfigurierte Schwellenwert (z.B. 6 Monate) sind.
    - **SentItems:** E-Mails im Ordner `SentItems` benötigen nie eine Antwort-Aktion.
    - **Bereits beantwortet:** E-Mails, für die das System erkennt, dass kein Handlungsbedarf besteht.'''

if old_info in content:
    content = content.replace(old_info, new_info)
else:
    # Try searching for a subset if exact match fails due to line endings
    content = content.replace('!!! info "SentItems Archivierung"', '!!! info "Automatische Archivierung"')

path.write_text(content, encoding='utf-8')
