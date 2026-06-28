# Indexierung im Detail

Dieser Abschnitt beschreibt präzise, was beim Ausführen des Befehls `mcp-uni index` geschieht.

## Prozessablauf

Die Indexierung erfolgt in mehreren Phasen:

1.  **Initialisierung:**  
    - Die Konfiguration wird aus `config/folders.yaml`, `config/user.yaml` und `config/models.yaml` geladen.  
    - Verbindungen zur SQLite-Metadatenbank (`data/metadata/university.db`) und zum Qdrant-Vektorindex (`data/indexes/qdrant`) werden hergestellt.  
    - Die Parser-Fabrik wird initialisiert (unterstützt PDF, Docx, Text, E-Mail).  

2.  **Crawling (Ordner-Scan):**  
    - Der Crawler durchläuft rekursiv alle in `config/folders.yaml` definierten Pfade.  
    - Für jeden Ordner wird geprüft, ob er bereits in der Datenbank existiert (Tabelle `folders`). Falls nicht, wird er neu angelegt.  
    - Integration mit `qmd` (Quick Markdown): Der Crawler versucht, die Ordner als `qmd`-Kollektionen hinzuzufügen, um die Dateisuche zu beschleunigen.  

3.  **Dateiverarbeitung:**  
    - Für jede Datei wird ein SHA-256 Hash berechnet.  
    - Der Hash wird mit dem Eintrag in der Tabelle `files` verglichen.  
    - **Nur neue oder geänderte Dateien werden verarbeitet.**  

4.  **Parsing & Extraktion:**  
    - Je nach Dateityp wird der entsprechende Parser aufgerufen:  
        - `PDFParser`: Nutzt primär `liteparse` zur schnellen Extraktion. Schlägt dies fehl, wird `docling` als robusterer Fallback verwendet.  
        - `MailParser`: Extrahiert Metadaten (Von, An, Datum) und Text aus `.eml` und `.msg`. Behandelt auch signierte E-Mails (`SignedAttachment`) sicher.  
        - `TextParser`: Liest Plaintext aus `.md`, `.txt`, `.py`, `.json`, etc.  

5.  **Zusammenfassung (Summarization):**  
    - Der extrahierte Text wird an das konfigurierte LLM (standardmäßig Ollama) gesendet.  
    - Es wird eine strukturierte Markdown-Zusammenfassung erstellt.  

6.  **Spezialfall: E-Mail-Konversationen:**  
    - Erkennt der Crawler eine Struktur mit `Inbox` und `SentItems` Unterordnern, gruppiert er E-Mails nach Konversationspartnern.  
    - Es wird eine aggregierte Zusammenfassung der gesamten Kommunikation mit einer Person erstellt.  
    - Diese wird als `.emails_summary.md` im Ordner gespeichert.  

7.  **Spezialfall: Ordner-Zusammenfassungen:**  
    - Nachdem alle Dateien eines Ordners verarbeitet wurden, erstellt das LLM eine Zusammenfassung des gesamten Ordnerinhalts basierend auf den Einzelzusammenfassungen.  
    - Schlägt die Zusammenfassung fehl, wird automatisch ein **Retry-Mechanismus** ausgelöst, der Debug-Informationen in `.folder_summary_items_debug.txt` und `.folder_summary_combined_debug.txt` schreibt.  
    - Diese wird als versteckte Datei `.<Ordnername>_summary.md` im **Elternverzeichnis** gespeichert. Dies gilt auch für Wurzelordner (die im selben Verzeichnis wie der Ordner selbst liegen).  
    - Der Crawler erzwingt eine Neu-Summarisierung, falls die Datei auf der Festplatte fehlt, selbst wenn die Datenbank sie als aktuell markiert.  

8.  **Speicherung & Indexierung:**  
    - **Metadaten:** Dateipfade, Hashes, Zeitstempel und die Markdown-Zusammenfassungen werden in der SQLite-Datenbank gespeichert.  
    - **Vektorsuche:** Die **Zusammenfassungen** (nicht der Volltext) werden vektorisiert (standardmäßig mit `BAAI/bge-m3`) und im Qdrant-Index gespeichert.  

## Beispiel: Vor und nach der Indexierung

Angenommen, Sie haben folgende Struktur:
```text
Vorlesungen/
├── KI/
│   ├── vorlesung1.pdf
│   └── script.txt
└── Mathe/
    └── analysis.pdf
```

Nach der Indexierung sieht es so aus:
```text
.Vorlesungen_summary.md
Vorlesungen/
├── .KI_summary.md
├── KI/
│   ├── vorlesung1.pdf
│   └── script.txt
├── .Mathe_summary.md
└── Mathe/
    └── analysis.pdf
```

### Beispiel: E-Mail-Strukturen

**Fall 1: Nur ein Posteingang (Standardverarbeitung)**
Vorher:
```text
Student_A/
└── Inbox/
    └── frage.msg
```
Nachher:
```text
.Student_A_summary.md
Student_A/
├── .Inbox_summary.md
└── Inbox/
    └── frage.msg
```

**Fall 2: Nur ein "Gesendete Objekte" Ordner (Standardverarbeitung)**
Vorher:
```text
Student_B/
└── SentItems/
    └── antwort.msg
```
Nachher:
```text
.Student_B_summary.md
Student_B/
├── .SentItems_summary.md
└── SentItems/
    └── antwort.msg
```

**Fall 3: Kombinierte E-Mail-Konversation (Spezialfall)**

Wenn sowohl `Inbox` und `SentItems` vorhanden sind, erkennt der Crawler dies als Konversation und erstellt eine gemeinsame Zusammenfassung (`.emails_summary.md`).

*Wichtiger Hinweis:* Während der **Crawler** diese Datei bei einer vollständigen Indexierung des Archivs anlegt, wird sie im täglichen **E-Mail-Workflow** (via `scripts/process_sorted_emails.py`) erst "Just-in-Time" in Phase 6 (Ausführung) generiert.

Vorher:
```text
Student_C/
├── Inbox/
│   └── frage.msg
└── SentItems/
    └── antwort.msg
```
Nachher:
```text
.Student_C_summary.md
Student_C/
├── .emails_summary.md
├── Inbox/
│   └── frage.msg
└── SentItems/
    └── antwort.msg
```

## Unterstützte Dateiformate

| Status | Formate |
| :--- | :--- |
| **Unterstützt** | `.pdf`, `.docx`, `.md`, `.txt`, `.eml`, `.msg`, `.py`, `.ipynb`, `.json`, `.html` |
| **Geplant / Nicht unterstützt** | `.pptx`, `.xlsx`, `.csv`, Bildformate (OCR erforderlich) |

**Hinweis zu Markdown-Dateien:** Alle `.md` Dateien werden indiziert und zusammengefasst, außer sie starten mit einem Punkt (`.`) und enden auf `_summary.md`. Diese werden als systemeigene Zusammenfassungen übersprungen.

## Erzeugte Dateien und Speicherorte

| Typ | Ort | Beschreibung |
| :--- | :--- | :--- |
| **SQLite DB** | `data/metadata/university.db` | Speichert Metadaten, Hashes, Pfade und Zusammenfassungen. |
| **Vektorindex** | `data/indexes/qdrant/` | Binäre Dateien des Qdrant-Suchindex. |
| **Ordner-Zusammenfassung** | `../.<Ordnername>_summary.md` | Versteckte Markdown-Datei im Elternverzeichnis. |
| **E-Mail-Zusammenfassung**| `./.emails_summary.md` | Aggregierte Konversationshistorie bei E-Mails. |
| **Logs** | `data/logs/mcp-university.log` | Detaillierte Protokollierung des Indexierungsprozesses. |
| **Cache** | `data/cache/` | Temporäre Artefakte des PDF-Parsers. |

## Zustandsprüfung

Der Befehl ist idempotent. Bei einem erneuten Aufruf werden nur Dateien verarbeitet, deren Hash sich seit der letzten Ausführung geändert hat. Gelöschte Dateien im Dateisystem werden bei der Indexierung auch aus der Datenbank entfernt.
