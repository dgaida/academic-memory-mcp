# Neuronale Netzarchitektur zur E-Mail-Klassifizierung

Diese Dokumentation beschreibt die im Package `email-classifier` integrierte und voll funktionsfähige Transformer-basierte Neuronale Netzarchitektur zur E-Mail-Klassifizierung. Sie dient als leistungsstarke Alternative zu den klassischen Klassifikationsmodellen (wie Random Forest oder XGBoost).

## 1. Architektur-Übersicht

Die Implementierung basiert auf einem **Transformer-basierten Modell** (Standard: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`). Im Gegensatz zu klassischen Bag-of-Words-Verfahren erfasst diese Architektur den semantischen Kontext und die Beziehungen zwischen den Wörtern im Satzgefüge (z. B. im E-Mail-Betreff und -Inhalt).

### Hauptkomponenten:  
1. **Encoder-Backbone**: Das vortrainierte multilinguale MPNet-Modell dient als Feature-Extractor.
2. **Input-Strukturierung**: Vorverarbeitung und Zusammenführung von Metadaten und E-Mail-Body in einen zusammenhängenden Eingabetext.  
3. **Classification Head**: Ein Fully Connected Layer (MLP) mit Dropout, das direkt auf das `[CLS]`-Token (den Repräsentationsvektor der gesamten Sequenz) angewendet wird, um die Wahrscheinlichkeiten für die Zielklassen zu berechnen.  

## 2. Datenaufbereitung & Input-Format

Um wichtige Metadaten explizit zu berücksichtigen und deren starke Signalwirkung (z. B. von Betreffzeilen oder Dateianhängen) zu nutzen, wird der Input vor der Tokenisierung wie folgt strukturiert:

**Format:**
```text
SUBJECT: <Betreff> | ATTACHMENTS: <Datei1.pdf, Datei2.docx> [SEP] <Inhalt der E-Mail (anonymisiert)>
```

- **Betreff (Subject)**: Besitzt die höchste Informationsdichte für die Zuordnung zu Kategorien wie z. B. Kolloquien oder Bachelorarbeiten.  
- **Anhänge (Attachments)**: Dateinamen wie "Antrag_BA.pdf" liefern extrem starke Merkmale für spezifische Klassen (z. B. `BachelorThesis`).  
- **Anonymisierung**: Personenbezogene Daten (PII) werden durch die `anonymize_th_koeln_names`-Logik vor der Weiterverarbeitung durch Platzhalter ersetzt.  

## 3. Vergleich der Ansätze

| Merkmal | Klassisch (TF-IDF + XGBoost/RF) | Transformer (NN) |
| :--- | :--- | :--- |
| **Status** | Implementiert (Standard offline) | Implementiert und einsatzbereit |
| **Kontext** | Ignoriert Wortreihenfolge (Bag-of-Words). | Erfasst komplexe semantische Zusammenhänge. |
| **Vokabular** | Begrenzt auf das im Training gesehene Vokabular. | Nutzt Subword-Tokenisierung (bessere Handhabung von OOV-Wörtern). |
| **Metadaten** | Müssen manuell als zusätzliche Features extrahiert werden. | Werden über das strukturierte Input-Format direkt im Textfluss gelernt. |
| **Transfer Learning** | Nicht möglich. | Nutzt vortrainiertes, tiefes Sprachwissen. |

## 4. Implementierungsdetails (`engine.py`)

Die tatsächliche PyTorch-Implementierung ist in `packages/email_classifier/src/email_classifier/engine.py` unter der Klasse `EmailTransformerClassifier` realisiert:

```python
class EmailTransformerClassifier(nn.Module):
    """Transformer-basiertes Modell zur E-Mail-Klassifizierung."""

    def __init__(self, model_name: str, num_classes: int, token: Optional[str] = None) -> None:
        """Initialisiert das Transformer-Modell.

        Args:
            model_name (str): Name des Modells.
            num_classes (int): Anzahl der Klassen.
            token (Optional[str]): HuggingFace Token.
        """
        super().__init__()
        self.transformer = AutoModel.from_pretrained(model_name, token=token)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.transformer.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask) -> torch.Tensor:
        """Führt den Forward-Pass des Modells aus.

        Args:
            input_ids (torch.Tensor): Input token IDs.
            attention_mask (torch.Tensor): Attention mask.

        Returns:
            torch.Tensor: Die Logits des Modells für die Klassen.
        """
        outputs = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
        # Nutze das [CLS] Token (erster Vektor der Sequenz) für die Klassifizierung
        cls_output = outputs.last_hidden_state[:, 0, :]
        cls_output = self.dropout(cls_output)
        return self.classifier(cls_output)
```

## 5. Trainings- & Validierungsstrategie

- **Fine-Tuning**: Die Gewichte des Transformer-Backbones sowie des Klassifikationskopfes werden mit einer niedrigen Learning Rate auf den TH-Köln-spezifischen E-Mail-Klassen trainiert.  
- **Klassen-Gewichtung (Weighted Cross-Entropy)**: Da einige Klassen deutlich seltener vorkommen (z. B. `SHK` vs. `Others`), wird ein gewichteter Cross-Entropy-Loss verwendet, um die Klassifizierung seltener Klassen zu verbessern.  
- **Maximale Sequenzlänge**: Auf 512 Token begrenzt, was für E-Mails einen optimalen Kompromiss aus Kontextgröße und Trainingsgeschwindigkeit darstellt.  

## 6. Zukünftige Verbesserungsmöglichkeiten

Obwohl das System bereits vollständig einsatzbereit ist, bieten sich für zukünftige Iterationen folgende Optimierungen an:

1. **Modell-Quantisierung (Quantization)**:  
   - Konvertierung des Modells in ein 8-Bit-Format (INT8) mittels PyTorch, um den Speicherbedarf auf Offline-Systemen (z. B. Laptops ohne dedizierte GPU) zu halbieren und die Inferenzgeschwindigkeit zu steigern.  
2. **LoRA Fine-Tuning für größere lokale Modelle**:  
   - Statt eines MPNet-Modells könnten größere multilinguale LLMs (z. B. Llama 3 oder Mistral) über Low-Rank Adaptation (LoRA) auf Klassifikation trainiert werden, sofern ausreichend Rechenressourcen vorhanden sind.
3. **Erweitertes Hyperparameter-Tuning**:  
   - Systematische Suche nach optimalen Learning Rates, Dropout-Raten und Batch-Sizes mittels Frameworks wie Optuna, um die Klassifikationsleistung (F1-Score) noch weiter zu maximieren.  
4. **Knowledge Distillation**:  
   - Destillieren eines sehr großen Modells in ein kleineres, hocheffizientes Transformer-Modell, das die hohe Vorhersagegenauigkeit beibehält, aber extrem schnell ausgeführt werden kann.  
