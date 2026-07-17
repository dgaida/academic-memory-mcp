# Installation

Das MCP University Memory System kann auf verschiedene Arten installiert werden.

## Voraussetzungen

- Python 3.10 oder höher  
- Ollama (für lokale LLM-Unterstützung)  
- Outlook (für die Arbeit mit .msg Dateien und Kalenderintegration unter Windows)  

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


## Installation mit Anaconda / Conda (Alternativ)

Als Alternative zur standardmäßigen Python-Umgebung können Sie das System auch über ein Anaconda/Miniconda Environment installieren. Das Projekt enthält eine vorkonfigurierte `environment.yml` Datei.

### Prozess der Conda-Installation:

1. **Conda-Umgebung erstellen:**  
   Erstellen Sie die neue Umgebung mit allen Abhängigkeiten (einschließlich Python, PyTorch und aller Bibliotheken wie Docling):
   ```bash
   conda env create -f environment.yml
   ```

2. **Umgebung aktivieren:**  
   Aktivieren Sie die erstellte Umgebung:
   ```bash
   conda activate mcp-university
   ```

3. **Installieren des Projekts im Entwicklungsmodus (Editable):**  
   Damit die CLI-Befehle und die Python-Pfade korrekt registriert sind, installieren Sie das Paket in der aktivierten Conda-Umgebung im editierbaren Modus:
   ```bash
   pip install -e .
   ```

4. **Installation verifizieren:**  
   Überprüfen Sie anschließend die korrekte Installation:
   ```bash
   mcp-uni --help
   ```

## GPU Unterstützung (Optional)

Für das Training und die Ausführung der Transformer-Modelle kann eine GPU verwendet werden. Dafür muss die entsprechende Version von PyTorch installiert sein.

### NVIDIA GPU (CUDA)
Besuchen Sie [pytorch.org](https://pytorch.org/get-started/locally/), um den passenden Installationsbefehl für Ihre CUDA-Version zu erhalten. Beispiel für CUDA 12.1:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Apple Silicon (MPS)
Auf Macs mit M1/M2/M3 Chips wird die GPU (Metal Performance Shaders) automatisch unterstützt, sofern eine aktuelle PyTorch-Version installiert ist.

## System-Abhängigkeiten

### Ollama (LLM Backend)

Das System setzt eine laufende Ollama-Instanz voraus.  
- **Download:** [ollama.com](https://ollama.com)  
- **Modelle:** Standardmäßig wird das Modell [gemma4:e2b](https://ollama.com/library/gemma4) (`gemma4:e2b`) verwendet. Sie können dies in `config/models.yaml` ändern.  



### Docling (PDF Parsing)

Für eine optimale PDF-Extraktion nutzt das System Docling. Dieses wird bereits bei der Installation von `mcp-university` (mittels `pip install -e .`) automatisch mitinstalliert.
Sollte es dennoch separat benötigt werden:
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
