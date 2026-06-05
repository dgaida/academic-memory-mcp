# Vorschlag: Neuronale Netzarchitektur zur E-Mail-Klassifizierung

Dieser Vorschlag beschreibt eine Alternative zu den aktuellen Modellen (XGBoost/Random Forest), die direkt auf den (anonymisierten) Rohdaten der E-Mails arbeitet, anstatt auf statistischen Merkmalen wie TF-IDF.

## 1. Architektur-Übersicht

Als Architektur wird ein **Transformer-basiertes Modell** (z. B. DistilBERT oder ein multilinguales MiniLM) vorgeschlagen. Im Gegensatz zu klassischen Verfahren, die Wortfrequenzen zählen, erfassen Transformer den semantischen Kontext und die Beziehung zwischen Wörtern (wie z. B. in Betreffzeilen und Body).

### Hauptkomponenten:  
1.  **Encoder**: Ein vortrainiertes Modell wie `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.  
2.  **Input-Formatting**: Strukturierung der Rohdaten in ein für Transformer optimiertes Format.  
3.  **Classification Head**: Ein Fully Connected Layer (MLP) mit Softmax-Aktivierung über dem `[CLS]`-Token oder einem Mean-Pooling-Vektor.  

## 2. Datenaufbereitung & Input-Format

Anstatt den Text einfach flach zu übergeben, werden die Metadaten und der Inhalt strukturiert tokenisiert:

**Format:**
```text
[CLS] SUBJECT: <Betreff> | ATTACHMENTS: <Datei1.pdf, Datei2.docx> [SEP] <Inhalt der E-Mail (anonymisiert)> [SEP]
```

-   **Betreff**: Hat oft die höchste Informationsdichte für die Klassifizierung.  
-   **Anhänge**: Die Dateinamen (z. B. "Antrag_BA.pdf") geben starke Hinweise auf Klassen wie "BachelorThesis".  
-   **Anonymisierung**: Die bereits implementierte `anonymize_th_koeln_names`-Logik bleibt erhalten, um PII zu schützen, während die Struktur (z. B. Vorhandensein einer TH-Köln Adresse vs. Externe) durch Platzhalter wie `max.mustermann@student.th-koeln.de` erhalten bleibt.  

## 3. Warum diese Architektur?

| Merkmal | Klassisch (TF-IDF + XGBoost) | Transformer (NN) |
| :--- | :--- | :--- |
| **Kontext** | Ignoriert Wortreihenfolge (Bag-of-Words). | Erfasst semantische Zusammenhänge. |
| **Vokabular** | Begrenzt auf Trainingsvokabular. | Nutzt Subword-Tokenisierung (handhabt OOV Wörter besser). |
| **Metadaten** | Muss manuell als Features hinzugefügt werden. | Kann Metadaten (Anhänge) direkt im Textfluss lernen. |
| **Transfer Learning** | Nicht möglich. | Nutzt vortrainiertes Wissen über Sprache. |

## 4. Implementierungsskizze (PyTorch-Stil)

```python
import torch.nn as nn
from transformers import AutoModel

class EmailTransformerClassifier(nn.Module):
    def __init__(self, model_name, num_classes):
        super().__init__()
        self.transformer = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.transformer.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask):
        outputs = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
        # Nutze das [CLS] Token (index 0) für die Klassifizierung
        cls_output = outputs.last_hidden_state[:, 0, :]
        cls_output = self.dropout(cls_output)
        return self.classifier(cls_output)
```

## 5. Trainingsstrategie

1.  **Fine-Tuning**: Das gesamte Modell wird mit einer niedrigen Learning Rate auf den spezifischen E-Mail-Klassen der TH Köln trainiert.  
2.  **Weighted Cross-Entropy**: Um Klassenungleichgewichte (z. B. viele "Others", wenige "SHK") auszugleichen.  
3.  **Data Augmentation**: Leichtes Rauschen in den Text einfügen oder Synonym-Ersetzung, um die Robustheit zu erhöhen.  

## 6. Nächste Schritte

- Integration von `transformers` und `torch` in die `EmailClassifier`-Engine.  
- Anpassung von `train.py`, um das Fine-Tuning des Modells zu ermöglichen.  
- Vergleich der Precision/Recall-Werte gegen das aktuelle XGBoost-Modell.  
