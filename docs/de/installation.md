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



### Docling (PDF Parsing)

Für eine optimale PDF-Extraktion nutzt das System Docling.
```bash
pip install "docling"
```
Stellen Sie sicher, dass die notwendigen Modellgewichte für Docling initialisiert sind (geschieht meist automatisch beim ersten Start).

## Installation verifizieren

Prüfen Sie, ob das CLI-Tool korrekt installiert wurde:

```bash
mcp-uni --help
```

### qmd (Suchindex-Backend)
`qmd` ist für eine hochwertige hybride Suche erforderlich. Es handelt sich um ein Node.js-basiertes Tool, das global installiert sein muss.

**Voraussetzungen:**  
- Node.js >= 22 oder Bun >= 1.0.0  

**Installation:**
```bash
npm install -g @tobilu/qmd
# oder
bun install -g @tobilu/qmd
```

Falls `qmd` nicht gefunden wird, nutzt das System automatisch eine native Python-Suche (Qdrant + BM25). Funktionen wie LLM-Re-Ranking und Query-Expansion stehen dann jedoch nicht zur Verfügung.
