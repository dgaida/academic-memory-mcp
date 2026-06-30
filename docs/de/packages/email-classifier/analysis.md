# XAI & Visualisierung

Werkzeuge zur Analyse des Modells und der Datenverteilung.

## XAI Analyse (`xai_analysis.py`)

Nutzt SHAP (SHapley Additive exPlanations), um zu erklären, welche Wörter die Entscheidung des Modells am stärksten beeinflusst haben.

**Befehl:**
```bash
python -m email_classifier.scripts.xai_analysis --test-data-path /pfad/zu/testdaten
```

**Ergebnis:**
Das Skript gibt für jede Klasse die Top 5 Wörter aus, die für eine positive Vorhersage dieser Klasse verantwortlich waren. Dies hilft zu validieren, ob das Modell auf den richtigen Merkmalen lernt (z.B. "Bachelorarbeit" für die Klasse `BachelorThesis`).

---

## Datenverteilung plotten (`plot_data_distribution.py`)

Visualisiert die Anzahl der E-Mails pro Klasse in den Trainings- und Testdaten.

**Befehl:**
```bash
python -m email_classifier.scripts.plot_data_distribution --train-dir /pfad/zu/train --test-dir /pfad/zu/test --output-dir ./plots
```

---

## Top Wörter finden (`top_words.py`)

Ein schnelles Skript, um die häufigsten Wörter pro Klasse statistisch zu ermitteln (unabhängig vom Modell).

**Befehl:**
```bash
python -m email_classifier.scripts.top_words /pfad/zu/daten
```
