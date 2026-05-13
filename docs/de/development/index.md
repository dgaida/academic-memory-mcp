# Entwickler-Dokumentation

Willkommen zur Entwicklung am MCP University Memory System.

## Architektur-Prinzipien

1.  **Offline-First:** Keine Abhängigkeit von Cloud-APIs (außer optional für Modell-Downloads).
2.  **Modularität:** Parser, Crawler und Summarizer sind entkoppelt.
3.  **Typsicherheit:** Konsequente Nutzung von Python Type Hints und Pydantic.

## Lokales Setup

1.  Repository klonen.
2.  Virtuelle Umgebung erstellen und aktivieren.
3.  Editierbare Installation: `pip install -e ".[dev]"`

## Coding Standards

### Docstrings
Wir nutzen konsequent das **Google-Style** Format für alle Funktionen und Klassen. Siehe [Docstring Guide](docstring-guide.md).

### Testing
Tests werden mit `pytest` durchgeführt:
```bash
python3 -m pytest
```

### Qualitätssicherung
Vor jedem Commit sollten folgende Tools laufen:
*   `interrogate`: Prüft die Docstring-Abdeckung (Ziel: >95%).
*   `markdownlint`: Prüft die Dokumentations-Dateien.

## Dokumentation bauen

Lokal können Sie die Dokumentation wie folgt ansehen:
```bash
mkdocs serve
```

Dies startet einen Server auf `http://127.0.0.1:8000` mit Live-Reload.
