# E-Mail-Klassifikator (Package)

Dieses Package bietet eine umfassende Lösung zur automatisierten Klassifizierung und Sortierung von studentischen E-Mails. Es unterstützt verschiedene Machine-Learning-Modelle und bietet Werkzeuge zur Analyse und Visualisierung.

## Struktur des Packages

Das Package ist in funktionale Bereiche unterteilt:

### Benutzer-Skripte (`email_classifier.scripts`)
Diese Skripte sind für den direkten Aufruf durch den Benutzer gedacht:
- **Training & Evaluierung:** `train.py`, `evaluate.py`
- **Vorhersage & Sortierung:** `predict.py`, `sort_emails.py`, `classify_folder.py`, `sort_by_direction.py`
- **Analyse & Visualisierung:** `xai_analysis.py`, `plot_data_distribution.py`, `top_words.py`

### Interne Module
Diese Module bilden den Kern des Systems und werden meist intern verwendet:
- **`engine.py`:** Das Herzstück mit den Modell-Implementierungen (XGBoost, Random Forest, Transformer).
- **`controller.py`:** Logik zur Steuerung der Klassifizierungs-Workflows.
- **`stopwords.py`:** Definition von Stoppwörtern für die Textverarbeitung.

## Dokumentationsübersicht

- [**Nutzung der Skripte**](usage.md) - Beispiele und Anleitungen für die CLI-Tools.
- [**Training & Evaluierung**](training.md) - Details zum Training neuer Modelle.
- [**XAI & Visualisierung**](analysis.md) - Erklärbarkeit und Datenanalyse.
- [**Architektur**](architecture.md) - Interner Aufbau und Transformer-Details.
