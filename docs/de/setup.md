# Einrichtung der Software

Diese Seite beschreibt die notwendigen Schritte zur Einrichtung des MCP University Systems.

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

## Konfiguration

Das System nutzt YAML-Dateien im Verzeichnis `config/` für die Konfiguration. Kopieren Sie die Beispiel-Dateien und passen Sie diese an.

### 1. Nutzer-Konfiguration (`user.yaml`)

Erstellen Sie eine Datei `config/user.yaml` basierend auf `config/user.yaml.example`:

```yaml
name: "Ihr Name"
email: "ihre.email@th-koeln.de"
```

Diese Information wird für die Anonymisierung, die Kalenderbuchung und das Sortieren von E-Mails verwendet.

### 2. Ordner-Konfiguration (`folders.yaml`)

Geben Sie an, welche Ordner überwacht werden sollen:

```yaml
folders:
  - "C:/Pfad/zu/Ihren/Dokumenten"
```

### 3. Klassifikator-Pfade (`classifier_paths.yaml`)

Definieren Sie die Zielpfade für die E-Mail-Einsortierung:

```yaml
class_paths:
  BachelorThesis: "D:/BachelorThesis"
  MasterThesis: "D:/MasterThesis"
  # ... weitere Klassen
```

### 4. Modell-Konfiguration (`models.yaml`)

Konfigurieren Sie die zu verwendenden LLM- und Embedding-Modelle.

## Nutzung der Skripte

### E-Mails nach Richtung sortieren

Wenn Sie einen Ordner mit E-Mails haben, die noch nicht in Inbox/SentItems unterteilt sind, nutzen Sie:

```bash
python -m mcp_university.classifier.sort_by_direction /pfad/zu/emails
```

### E-Mails nach Klassen sortieren

Um E-Mails basierend auf ihrem Inhalt in die entsprechenden Projektordner zu sortieren:

```bash
python -m mcp_university.classifier.sort_emails /pfad/zu/emails --config config/classifier_paths.yaml
```
