# E-Mail Klassifizierung

Das System enthält ein leistungsfähiges Subpackage zur automatisierten Klassifizierung von studentischen E-Mails (z.B. Bachelorarbeit, Praxisprojekt).

## Modell trainieren
Um den Klassifikator zu nutzen, muss er zuerst mit Beispieldaten trainiert werden. Erwartet wird eine Ordnerstruktur, in der jeder Unterordner eine Klasse repräsentiert und die E-Mails (.msg) enthält.

```bash
python3 email_classifier/train.py /pfad/zu/trainingsdaten --mode tfidf --method transformer
```

Dabei kann zwischen `randomforest`, `xgboost` und `transformer` (Standard) gewählt werden.

## E-Mail klassifizieren
Nach dem Training kann eine einzelne E-Mail-Datei klassifiziert werden:

```bash
python3 email_classifier/predict.py /pfad/zur/email.msg
```

Die Ausgabe enthält die wahrscheinlichste Klasse sowie die Konfidenz und eine detaillierte Wahrscheinlichkeitsverteilung.

## XAI Analyse (Interpretierbarkeit)
Um zu verstehen, welche Wörter für die Klassifizierung besonders wichtig waren, kann die XAI Analyse genutzt werden. Diese nutzt SHAP-Werte, um den Einfluss einzelner Wörter auf die Vorhersage zu berechnen.

```bash
python3 email_classifier/xai_analysis.py --model-path data/email_classifier_xgboost_tfidf.pkl --test-data-path /pfad/zu/testdaten
```

Das Skript analysiert bis zu 20 E-Mails pro Klasse und gibt die Top 5 Wörter zurück, die für die jeweilige Klasse am charakteristischsten sind.

## E-Mail Sortierung (Studenten-Ordner)
Das leistungsfähigste Skript sortiert E-Mails nicht nur nach Klasse, sondern auch nach Semester und Student (Nachname):

```bash
python3 email_classifier/sort_emails.py /quell/ordner --config config/class_paths.yaml --model data/email_classifier_xgboost_combined.pkl
```

Es erkennt automatisch:  
- **Semester:** Basierend auf dem E-Mail-Datum (SoSe/WS).  
- **Student:** Extrahiert den Nachnamen aus `smail.th-koeln.de` Adressen oder Anzeigenamen.  
- **Richtung:** Sortiert in `lastname/Inbox` oder `lastname/SentItems` Unterordner (einheitlich für alle Klassen).  
- **Bericht:** Erstellt eine `sorted_emails.md` mit einer Übersicht aller verschobenen Mails.  

### Maintenance Script
Mit `scripts/fix_email_folders.py` können bestehende E-Mail-Strukturen, die noch nicht dem `lastname/Folder` Schema entsprechen, automatisch migriert werden.

## Batch-Klassifizierung
Um einen ganzen Ordner mit E-Mails automatisch zu sortieren (nur Klassifizierung):
```bash
python3 email_classifier/classify_folder.py /quell/ordner --model data/email_classifier_xgboost_combined.pkl
```
Dies verschiebt die E-Mails in Unterordner, die nach den vorhergesagten Klassen benannt sind.

## Visualisierung der Datenverteilung
Um die Verteilung der E-Mails pro Klasse (aufgeteilt nach Inbox und SentItems) zu visualisieren, kann folgendes Skript genutzt werden:

```bash
python3 email_classifier/plot_data_distribution.py --train-dir D:\\TH_Koeln\\MailTrainingData --test-dir D:\\TH_Koeln\\MailTestData --output-dir data
```

Dies erzeugt zwei hochauflösende PNG-Dateien in `data/`:  
- `train_data_distribution.png`  
- `test_data_distribution.png`  

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
