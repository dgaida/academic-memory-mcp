# Academic Parser Package

Dieses Package stellt verschiedene Parser für das MCP University System zur Verfügung. Es unterstützt das Extrahieren von Texten aus PDF, E-Mail (EML/MSG), Text- (TXT, MD, PY, JSON, etc.) und Word-Dokumenten (DOCX).

## Features

- **PDF Parser:** Extrahiert Text aus PDF- und DOCX-Dateien (mit Docling und LiteParse Fallbacks).
- **Mail Parser:** Extrahiert Details und Anhänge aus E-Mails (.eml und .msg).
- **Text Parser:** Liest Standard-Textformate.
- **Parser Factory:** Stellt automatisch den passenden Parser für einen gegebenen Dateityp bereit.

## Installation

```bash
pip install -e packages/parser
```
