# Architektur & Interne Module

Dieser Abschnitt beschreibt den internen Aufbau des E-Mail-Klassifikators und die Funktionsweise der Kernmodule.

## Kernmodule

### `engine.py`
Enthält die Basisklassen für die Klassifizierung:
- **`EmailClassifier`**: Verwaltet das Laden von Modellen, Vorverarbeitung und Vorhersagen für klassische Modelle (RandomForest, XGBoost).
- **`EmailTransformerClassifier`**: Eine PyTorch-basierte Implementierung für Transformer-Modelle.
- **Vektorisierung**: Unterstützt TF-IDF, Embeddings (BGE-M3) und eine Kombination aus beiden.

### `controller.py`
Der `EmailController` orchestriert den Prozess:
1. Laden der Konfiguration und des Modells.
2. Parsen eingehender E-Mails.
3. Aufruf der Klassifizierung.
4. Entscheidung über weitere Aktionen (Sortierung, Antwortgenerierung).

## Transformer-Architektur

Für die Deep-Learning-Klassifizierung wird ein Transformer-Modell (Standard: `paraphrase-multilingual-MiniLM-L12-v2`) verwendet.

### Strukturierter Input
E-Mails werden vor der Verarbeitung strukturiert, um wichtige Metadaten zu erhalten:
```text
SUBJECT: <Betreff> | ATTACHMENTS: <Datei1.pdf, ...> [SEP] <E-Mail-Body (anonymisiert)>
```
Dies ermöglicht es dem Modell, die starke Signalwirkung von Betreffzeilen explizit zu lernen.

### Fine-Tuning
- Die Gewichte des Transformer-Backbones werden aktualisiert.
- Ein Klassifizierungskopf (Linear Layer) wird auf den `[CLS]`-Token angewendet.
- Maximale Sequenzlänge: 512 Token.

## Datenfluss
1. **Rohdaten**: .msg oder .eml Dateien.
2. **Parser**: Extraktion von Text, Betreff und Anhängen.
3. **Vorverarbeitung**: Anonymisierung (PII) und Strukturierung.
4. **Modell**: Berechnung der Klassenwahrscheinlichkeiten.
5. **Output**: Zuweisung einer Kategorie (z.B. `BachelorThesis`).
