# Parser Sub-Package

Das `academic_parser` Sub-Package bietet eine einheitliche und leistungsstarke Schnittstelle zur Text- und Metadaten-Extraktion aus verschiedenen Dateiformaten. Es abstrahiert die Komplexität verschiedener spezialisierter Python-Bibliotheken unter einer gemeinsamen, einfachen API.

## Übersicht der Parser

Das Package umfasst drei spezialisierte Haupt-Parser, die über eine gemeinsame Fabrik (`ParserFactory`) bereitgestellt werden:

### 1. PDF & DOCX Parser (`PDFParser`)
Der PDF-Parser ist darauf ausgelegt, formatierte Texte aus PDF- und DOCX-Dokumenten (wie z.B. Vorlesungsfolien, Aufgabenblättern oder Modulhandbüchern) zu extrahieren.
- **Primärer Ansatz:** Nutzt `LiteParse` für eine schnelle und strukturierte Extraktion.
- **Fallbacks:** Verwendet `docling` und `python-docx` bei fehlenden Abhängigkeiten oder komplexeren Layouts.
- **Offline-Modus:** Erkennt und unterstützt den Offline-Betrieb.

### 2. Mail-Parser (`MailParser`)
Der Mail-Parser verarbeitet `.eml` und `.msg` Dateien (wie sie aus Outlook oder Thunderbird exportiert werden).
- Extrahiert Sender, Empfänger (To, Cc), Datum und Betreff.
- Verarbeitet Multipart-Nachrichten und dekodiert Textinhalte zuverlässig mit verschiedenen Encodings (inkl. Latin-1 Fallback).
- Ermöglicht das Extrahieren und Speichern von E-Mail-Anhängen.
- Beinhaltet die komplexe Logik zur Extraktion und Normalisierung von Nachnamen für die Sortierung.

### 3. Text-Parser (`TextParser`)
Ein schlanker Parser für Standard-Textdateien.
- Unterstützt `.txt`, `.md`, `.py`, `.json`, `.html`, `.ipynb`.
- Liest Inhalte mit UTF-8 Kodierung und bietet robuste Fehlerbehandlung.

---

## Die Parser-Fabrik (`ParserFactory`)

Die `ParserFactory` ist die zentrale Anlaufstelle für das Gesamtsystem. Sie entscheidet anhand der Dateiendung automatisch, welcher Parser geladen und ausgeführt werden soll.

### Beispielhafte Nutzung

```python
from pathlib import Path
from academic_parser.factory import ParserFactory

# Initialisierung mit einem Cache-Verzeichnis für PDF-Artefakte
factory = ParserFactory(cache_dir=Path("./cache"))

# Parsen einer beliebigen Datei
text = factory.parse(Path("studienverlaufsplan.pdf"))
print(text)
```

## Weitere Themen
- [**E-Mail-Parsing & Namensextraktion im Detail**](email-parsing.md)
