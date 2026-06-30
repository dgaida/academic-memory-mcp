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

## Feature-Modellierung (Merkmalsextraktion)

Der `EmailClassifier` unterstützt drei verschiedene Modi für die Merkmalsextraktion:

1.  **TF-IDF (`tfidf`)**:
    - **Funktionsweise:** Verwendet die Term Frequency-Inverse Document Frequency. Es werden Worthäufigkeiten gezählt und gewichtet.
    - **Vorteile:** Schnell, gut interpretierbar, effektiv bei klar definierten Fachbegriffen.
    - **Nachteile:** Ignoriert Wortreihenfolge und Semantik.

2.  **Embeddings (`embedding`)**:
    - **Funktionsweise:** Verwendet `Sentence-Transformers` (`BAAI/bge-m3`), um den Text in einen hochdimensionalen Vektorraum zu projizieren.
    - **Vorteile:** Erfasst die semantische Bedeutung und Synonyme.
    - **Nachteile:** Rechenintensiver, schwerer interpretierbar.

3.  **Kombiniert (`combined`)**:
    - **Funktionsweise:** Konkateniert die TF-IDF-Vektoren mit den Embedding-Vektoren.
    - **Vorteile:** Kombiniert Präzision von Schlüsselwörtern mit tiefem semantischen Verständnis. Meist höchste Genauigkeit.

### Modell-Benennung
Beim Training wird die gewählte Methode und der Modus automatisch an den Dateinamen angehängt (z.B. `email_classifier_transformer.pkl`), um eine Verwechslung der Modelle zu vermeiden.
