# Installation

Das MCP University Memory System kann auf verschiedene Arten installiert werden.

## Standard Installation (User)

Für die normale Nutzung empfehlen wir die Installation in einer virtuellen Umgebung:

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# oder
venv\Scripts\activate     # Windows

pip install .
```

## Entwickler Installation (Editable)

Wenn Sie am Code arbeiten möchten oder die neuesten Änderungen direkt testen wollen:

```bash
pip install -e .
```

### Zusätzliche Entwickler-Abhängigkeiten

Für Tests und Dokumentationserstellung:

```bash
pip install pytest pytest-asyncio mkdocs-material mkdocs-static-i18n mkdocstrings[python] interrogate git-cliff mike
```

## System-Abhängigkeiten

### Ollama (LLM Backend)

Das System setzt eine laufende Ollama-Instanz voraus.
- **Download:** [ollama.com](https://ollama.com)
- **Modelle:** Standardmäßig wird `gemma2:2b` verwendet. Sie können dies in `config/models.yaml` ändern.

### qmd (Search Backend)

`qmd` ist für die hybride Suche erforderlich. Stellen Sie sicher, dass es installiert und über die Kommandozeile erreichbar ist.

### MinerU (PDF Parsing)

Für eine optimale PDF-Extraktion nutzt das System MinerU.
```bash
pip install "magic-pdf[full]"
```
Stellen Sie sicher, dass die notwendigen Modellgewichte für MinerU initialisiert sind (geschieht meist automatisch beim ersten Start).

## Installation verifizieren

Prüfen Sie, ob das CLI-Tool korrekt installiert wurde:

```bash
mcp-uni --help
```
