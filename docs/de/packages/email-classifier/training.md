# Training & Evaluierung

Dieser Abschnitt beschreibt, wie Modelle trainiert, validiert und getestet werden.

## Modell trainieren (`train.py`)

Das Training erwartet eine Ordnerstruktur, in der Unterordner die Klassen repräsentieren. Innerhalb dieser Klassenordner sollten `Inbox` und `SentItems` liegen.

**Befehl:**
```bash
python -m email_classifier.scripts.train /pfad/zu/trainingsdaten --mode combined --method xgboost
```

### Parameter:
- `--mode`: `tfidf`, `embedding` oder `combined` (Standard: `combined`).
- `--method`: `xgboost`, `randomforest` oder `transformer`.
- `--model-path`: Optionaler Pfad zum Speichern des Modells.

Das Training erstellt automatisch Diagramme zur Confusion Matrix und zum Trainingsverlauf (bei Transformer).

---

## Modell evaluieren (`evaluate.py`)

Berechnet detaillierte Metriken (Accuracy, Precision, Recall, F1) für ein existierendes Modell auf einem Testdatensatz.

**Befehl:**
```bash
python -m email_classifier.scripts.evaluate /pfad/zu/testdaten --mode combined
```

**Ergebnis:**
- Konsolenausgabe des `classification_report`.
- Generierung einer Heatmap der Confusion Matrix als PNG.
- Speicherung der Metriken in `metrics.json`.
