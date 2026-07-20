# E-Mail-Klassifikator (Package)

Dieses Package bietet eine umfassende Lösung zur automatisierten Klassifizierung und Sortierung von studentischen E-Mails. Es unterstützt verschiedene Machine-Learning-Modelle und bietet Werkzeuge zur Analyse und Visualisierung.

## Struktur des Packages

Das Package ist in funktionale Bereiche unterteilt:

### Benutzer-Skripte (`email_classifier.scripts`)
Diese Skripte sind für den direkten Aufruf durch den Benutzer gedacht:  
- **Training & Evaluierung:** `train.py`, `evaluate.py`  
- **Vorhersage & Sortierung:** `predict.py`, `sort_emails.py`, `classify_folder.py`, `sort_by_direction.py`  
- **Analyse & Visualisierung:** `xai_analysis.py`, `plot_data_distribution.py`, `top_words.py`  

### Interne Module & Kernmodule
Diese Module bilden den Kern des Systems und werden meist intern verwendet:  

#### `engine.py`
Enthält die Basisklassen für die Klassifizierung:
- **`EmailClassifier`**: Verwaltet das Laden von Modellen, Vorverarbeitung und Vorhersagen für klassische Modelle (RandomForest, XGBoost).
- **`EmailTransformerClassifier`**: Eine PyTorch-basierte Implementierung für Transformer-Modelle.
- **Vektorisierung**: Unterstützt TF-IDF, Embeddings (BGE-M3) und eine Kombination aus beiden.

#### `controller.py`
Der `EmailController` orchestriert den Prozess:
1. Laden der Konfiguration und des Modells.
2. Parsen eingehender E-Mails.
3. Aufruf der Klassifizierung.
4. Entscheidung über weitere Aktionen (Sortierung, Antwortgenerierung).

#### `stopwords.py`
Definition von Stoppwörtern für die Textverarbeitung.

## Dokumentationsübersicht

- [**Nutzung der Skripte**](usage.md) - Beispiele und Anleitungen für die CLI-Tools.  
- [**Training & Evaluierung**](training.md) - Details zum Training neuer Modelle.  
- [**XAI & Visualisierung**](analysis.md) - Erklärbarkeit und Datenanalyse.  
- [**Neuronale Netzarchitektur**](nn_architecture.md) - Details zur Transformer-basierten Klassifizierung.
