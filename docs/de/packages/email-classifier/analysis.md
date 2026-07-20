# XAI & Visualisierung

Werkzeuge zur Analyse des Modells und der Datenverteilung.

## XAI Analyse (`xai_analysis.py`)

Nutzt SHAP (SHapley Additive exPlanations), um zu erklären, welche Wörter die Entscheidung des Modells am stärksten beeinflusst haben.

**Wichtiger Hinweis zur Modellkompatibilität:**  
- **ML-Modelle (TF-IDF):** Die XAI-Analyse funktioniert **ausschließlich** für die klassischen Machine-Learning-Modelle im **TF-IDF-Modus** (`--mode tfidf`), da hierfür der SHAP `TreeExplainer` auf dem Vektorizer aufbaut.  
- **Transformer & andere Modi:** Die XAI-Analyse funktioniert **nicht** für das Transformer-Modell oder für ML-Modelle, die im `embedding`- oder `combined`-Modus trainiert wurden.  

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

Ein schnelles Skript, um die häufigsten Wörter pro Klasse statistisch zu ermitteln.

**Wichtiger Hinweis zur Modellunabhängigkeit:**  
- Dieses Skript arbeitet **vollkommen modellunabhängig** direkt auf den Rohdaten mittels statistischer TF-IDF-Berechnung.  
- Es wird **kein trainiertes Modell** (weder klassische ML-Modelle noch das Transformer-Modell) benötigt oder geladen. Es dient zur reinen Datenanalyse vor oder nach dem Training.  

**Befehl:**
```bash
python -m email_classifier.scripts.top_words /pfad/zu/daten
```
