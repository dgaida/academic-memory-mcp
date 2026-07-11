# Einrichtung der Software

Diese Seite beschreibt die notwendigen Schritte zur ersten Einrichtung und Installation des MCP University Systems.

## Voraussetzungen

- Python 3.10 oder höher  
- Ollama (für lokale LLM-Unterstützung)  
- Outlook (für die Arbeit mit .msg Dateien und Kalenderintegration unter Windows)  

## Installation

1. Klonen Sie das Repository.  
2. Erstellen Sie eine virtuelle Umgebung und installieren Sie die Abhängigkeiten:  

```bash
pip install -e .
```

Oder nutzen Sie die bereitgestellte `environment.yml` mit Conda:

```bash
conda env create -f environment.yml
conda activate mcp-university
```

## Erst-Einrichtung (Initialer Setup-Ablauf)

Um das System betriebsbereit zu machen, führen Sie folgende Schritte aus:

1. **Konfigurationsdateien vorbereiten:**
   Kopieren Sie die `.example` Konfigurationsdateien im Verzeichnis `config/`:
   ```bash
   cp config/user.yaml.example config/user.yaml
   cp config/ontology.yaml.example config/ontology.yaml
   cp config/classifier_paths.yaml.example config/classifier_paths.yaml
   ```

2. **Benutzerdaten anpassen:**
   Tragen Sie Ihren Namen und Ihre Hochschul-E-Mail in `config/user.yaml` ein.

3. **Studierendendaten synchronisieren:**
   Falls Sie bereits eine `students.yaml` (z.B. über die Outlook-Makros) erstellt haben, synchronisieren Sie diese mit der SQLite-Datenbank:
   ```bash
   mcp-uni db sync-students
   ```

Eine detaillierte Beschreibung aller Konfigurationsoptionen und der verschiedenen `.yaml` Dateien finden Sie auf der Seite **[Konfiguration](configuration.md)**.
