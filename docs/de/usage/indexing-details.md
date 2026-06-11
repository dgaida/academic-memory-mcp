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
        - `PDFParser`: Nutzt `liteparse` (Primär) oder `docling` (Fallback) für PDF/Docx.
        - `MailParser`: Extrahiert Metadaten (Von, An, Datum) und Text aus `.eml` und `.msg`.
        - `TextParser`: Liest Plaintext aus `.md`, `.txt`, `.py`, `.json`, etc.

5.  **Zusammenfassung (Summarization):**
    - Der extrahierte Text wird an das konfigurierte LLM (standardmäßig Ollama) gesendet.
    - Es wird eine strukturierte Markdown-Zusammenfassung erstellt.

6.  **Spezialfall: E-Mail-Konversationen:**
    - Erkennt der Crawler eine Struktur mit `Inbox` und `SentItems` Unterordnern, gruppiert er E-Mails nach Konversationspartnern.
    - Es wird eine aggregierte Zusammenfassung der gesamten Kommunikation mit einer Person erstellt.
    - Diese wird als `.Inbox_Sentitems_Summary.md` im Ordner gespeichert.

7.  **Spezialfall: Ordner-Zusammenfassungen:**
    - Nachdem alle Dateien eines Ordners verarbeitet wurden, erstellt das LLM eine Zusammenfassung des gesamten Ordnerinhalts basierend auf den Einzelzusammenfassungen.
    - Diese wird als versteckte Datei `.<Ordnername>_summary.md` im Elternverzeichnis gespeichert.

8.  **Speicherung & Indexierung:**
    - **Metadaten:** Dateipfade, Hashes, Zeitstempel und die Markdown-Zusammenfassungen werden in der SQLite-Datenbank (`summaries` Tabelle) gespeichert.
    - **Vektorsuche:** Die **Zusammenfassungen** (nicht der Volltext) werden vektorisiert (standardmäßig mit `BAAI/bge-m3`) und im Qdrant-Index gespeichert.

## Erzeugte Dateien und Speicherorte

| Typ | Ort | Beschreibung |
| :--- | :--- | :--- |
| **SQLite DB** | `data/metadata/university.db` | Speichert Metadaten, Hashes, Pfade und Zusammenfassungen. |
| **Vektorindex** | `data/indexes/qdrant/` | Binäre Dateien des Qdrant-Suchindex. |
| **Ordner-Zusammenfassung** | `./.<Ordnername>_summary.md` | Versteckte Markdown-Datei mit der Übersicht des Ordners. |
| **E-Mail-Zusammenfassung**| `./.Inbox_Sentitems_Summary.md` | Aggregierte Konversationshistorie bei E-Mails. |
| **Logs** | `data/logs/mcp-university.log` | Detaillierte Protokollierung des Indexierungsprozesses. |
| **Cache** | `data/cache/` | Temporäre Artefakte des PDF-Parsers. |

## Zustandsprüfung

Der Befehl ist idempotent. Bei einem erneuten Aufruf werden nur Dateien verarbeitet, deren Hash sich seit der letzten Ausführung geändert hat. Gelöschte Dateien im Dateisystem werden bei der Indexierung auch aus der Datenbank entfernt.
