# E-Mail-Klassifizierung mit Neuronalen Netzen (Transformer)

Dieses Modul bietet eine Alternative zu klassischen Modellen (XGBoost/Random Forest), indem es direkt auf den (anonymisierten) Rohdaten der E-Mails arbeitet.

## Architektur

Die Architektur basiert auf einem **Transformer-Modell** (Standard: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`), das für die Sequenzklassifizierung feinjustiert wird.

### Datenaufbereitung

Anstatt den Text einfach als flachen String zu übergeben, werden die E-Mail-Komponenten strukturiert:

```text
SUBJECT: <Betreff> | ATTACHMENTS: <Datei1.pdf, ...> [SEP] <E-Mail-Body (anonymisiert)>
```

Dies ermöglicht es dem Modell, die starke Signalwirkung von Betreffzeilen und Dateinamen explizit zu lernen.

## Training

Das Modell wird mittels Fine-Tuning trainiert. Dabei werden:  
1.  Die Gewichte des Transformer-Backbones aktualisiert.  
2.  Ein Klassifizierungskopf (Linear Layer) auf den `[CLS]`-Token angewendet.  
3.  Die E-Mails mit einer maximalen Sequenzlänge von 512 Token verarbeitet.  

## Nutzung

Um den Transformer-Modus zu nutzen, muss beim Training der Parameter `--method transformer` übergeben werden:

```bash
python -m mcp_university.classifier.train <data_dir> --method transformer
```

Der Vorteil gegenüber TF-IDF liegt in der Erfassung semantischer Ähnlichkeiten, was besonders bei variierenden Formulierungen in Studenten-E-Mails von Vorteil ist.
