# E-Mail-Klassifikator (email_classifier)

Dieses Package enthält alle Funktionalitäten für das Training, die Validierung und den Test des E-Mail-Klassifikators für studentische E-Mails.

## Features  
- **Multi-Modell-Unterstützung:** Klassifizierung mittels RandomForest, XGBoost oder Transformer (MiniLM).  
- **Flexible Merkmalsextraktion:** Unterstützt TF-IDF, semantische Embeddings (BGE-M3) oder eine Kombination aus beiden.  
- **Automatisierte Sortierung:** Skripte zur Einsortierung von E-Mails in Semester- und Studentenordner.  
- **Explainable AI (XAI):** Integration von SHAP zur Interpretation von Modellentscheidungen.  
- **Visualisierung:** Tools zur Analyse der Datenverteilung.  

## Ordnerstruktur  
- `src/email_classifier/`: Kernlogik und Controller.  
- `src/email_classifier/scripts/`: Benutzerorientierte CLI-Skripte.  
- `tests/`: Umfassende Testsuite für alle Komponenten.  

## Wichtige Skripte

Die Skripte befinden sich im Unterordner `scripts` und werden als Modul aufgerufen:

### Training
```bash
python -m email_classifier.scripts.train /pfad/zu/daten --method transformer
```

### Sortierung
```bash
python -m email_classifier.scripts.sort_emails /quell/ordner --config config/class_paths.yaml
```

### Vorhersage
```bash
python -m email_classifier.scripts.predict /pfad/zur/email.msg
```

## Installation
Innerhalb des Hauptprojekts:
```bash
pip install -e .
```
Oder als separates Package:
```bash
cd packages/email_classifier
pip install -e .
```

Für detaillierte Informationen zur Nutzung und Architektur besuchen Sie bitte die [Dokumentation](https://dgaida.github.io/academic-memory-mcp/dev/packages/email-classifier/).
