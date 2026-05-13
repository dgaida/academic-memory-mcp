# Erste Schritte

Diese Anleitung führt Sie durch die Einrichtung und die ersten Schritte mit dem MCP University Memory System.

## Voraussetzungen

Stellen Sie sicher, dass die folgende Software installiert ist:

*   **Python 3.10+**
*   **Ollama:** Installieren Sie Ollama und laden Sie das Standardmodell herunter:
    ```bash
    ollama pull gemma2:2b
    ```
*   **qmd:** Das CLI-Tool für die hybride Suche (muss im PATH verfügbar sein).
*   **MinerU (magic-pdf):** Für das PDF-Parsing (wird über pip installiert).

## Installation

Klonen Sie das Repository und installieren Sie die Abhängigkeiten:

```bash
git clone https://github.com/example/mcp-university.git
cd mcp-university
pip install -e .
```

## Konfiguration

Passen Sie die zu überwachenden Ordner in `config/folders.yaml` an:

```yaml
folders:
  - /pfad/zu/deinen/vorlesungen
  - /pfad/zu/studenten/unterlagen
exclude_patterns:
  - ".git"
  - "node_modules"
```

## Erster Index-Lauf

Starten Sie den Crawler, um Ihre Dokumente zu analysieren und Zusammenfassungen zu erstellen:

```bash
mcp-uni index
```

Der Prozess führt folgende Schritte aus:
1. Scannt die konfigurierten Ordner.
2. Extrahiert Text aus PDF, DOCX, MD, etc.
3. Generiert Zusammenfassungen mittels Ollama.
4. Speichert Metadaten in SQLite und indiziert den Text in qmd.

## Suche verwenden

Testen Sie die Suche direkt über das CLI:

```bash
mcp-uni search "Wann ist die Abgabe für die Masterarbeit von Max Mustermann?"
```

## MCP Server starten

Stellen Sie die Tools für Ihre KI-Agenten (z.B. in Claude Desktop) bereit:

```bash
mcp-uni serve-mcp
```

Nun kann Ihr Agent auf Dokumente zugreifen, E-Mail-Antworten entwerfen und Kontext zu Studenten abrufen.
