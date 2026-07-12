# Neural Network Architecture for Email Classification

This documentation describes the fully functional, integrated Transformer-based Neural Network architecture implemented in the `email-classifier` package. It serves as a powerful alternative to classical classification models (such as Random Forest or XGBoost).

## 1. Architecture Overview

The implementation is based on a **Transformer-based model** (default: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`). Unlike classical bag-of-words methods, this architecture captures the semantic context and relationships between words within sentences (e.g., in the email subject and body).

### Core Components:
1. **Encoder Backbone**: The pre-trained multilingual MiniLM model serves as the feature extractor.
2. **Input Structuring**: Preprocessing and merging of metadata and email body into a structured, unified input text.
3. **Classification Head**: A Fully Connected Layer (MLP) with dropout, applied directly to the `[CLS]` token (the representation vector of the entire sequence) to calculate the target class probabilities.

## 2. Data Preparation & Input Format

To explicitly integrate important metadata and leverage its strong signal effect (e.g., subject lines or attachments), the input is structured as follows before tokenization:

**Format:**
```text
SUBJECT: <Subject> | ATTACHMENTS: <file1.pdf, file2.docx> [SEP] <Email Body (anonymized)>
```

- **Subject**: Often holds the highest information density for classifying emails into categories such as colloquia or Bachelor's theses.
- **Attachments**: Filenames like "Antrag_BA.pdf" provide extremely strong indicators for specific classes (e.g., `BachelorThesis`).
- **Anonymization**: Personally identifiable information (PII) is replaced with placeholders using the `anonymize_th_koeln_names` logic before processing.

## 3. Comparison of Approaches

| Feature | Classical (TF-IDF + XGBoost/RF) | Transformer (NN) |
| :--- | :--- | :--- |
| **Status** | Implemented (Standard offline) | Implemented and ready to use |
| **Context** | Ignores word order (Bag-of-Words). | Captures complex semantic relationships. |
| **Vocabulary** | Limited to the vocabulary seen in training. | Uses subword tokenization (better handling of OOV words). |
| **Metadata** | Must be manually extracted as additional features. | Directly learned within the text stream via structured input. |
| **Transfer Learning**| Not possible. | Leverages pre-trained, deep language knowledge. |

## 4. Implementation Details (`engine.py`)

The actual PyTorch implementation resides in `packages/email_classifier/src/email_classifier/engine.py` under the `EmailTransformerClassifier` class:

```python
class EmailTransformerClassifier(nn.Module):
    """Transformer-based model for email classification."""

    def __init__(self, model_name: str, num_classes: int, token: Optional[str] = None) -> None:
        """Initializes the Transformer model.

        Args:
            model_name (str): Name of the model.
            num_classes (int): Number of classes.
            token (Optional[str]): HuggingFace Token.
        """
        super().__init__()
        self.transformer = AutoModel.from_pretrained(model_name, token=token)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.transformer.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask) -> torch.Tensor:
        """Performs the forward pass of the model.

        Args:
            input_ids (torch.Tensor): Input token IDs.
            attention_mask (torch.Tensor): Attention mask.

        Returns:
            torch.Tensor: The model logits for each class.
        """
        outputs = self.transformer(input_ids=input_ids, attention_mask=attention_mask)
        # Use the [CLS] token (first vector of the sequence) for classification
        cls_output = outputs.last_hidden_state[:, 0, :]
        cls_output = self.dropout(cls_output)
        return self.classifier(cls_output)
```

## 5. Training & Validation Strategy

- **Fine-Tuning**: The weights of both the Transformer backbone and the classification head are updated with a low learning rate on TH-Köln-specific email classes.
- **Class Weighting (Weighted Cross-Entropy)**: To handle class imbalance (e.g., many `Others` vs. few `SHK` emails), weighted cross-entropy loss is employed to improve performance on minority classes.
- **Max Sequence Length**: Capped at 512 tokens, which provides an optimal trade-off between context representation and training/inference speed.

## 6. Future Improvement Opportunities

While the system is fully operational, several optimization paths remain for future iterations:

1. **Model Quantization**:
   - Convert the model to an 8-bit integer format (INT8) using PyTorch to halve memory footprint on offline/client machines (e.g., laptops without dedicated GPUs) and increase inference speed.
2. **LoRA Fine-Tuning for Larger Local Models**:
   - Instead of a MiniLM model, larger multilingual LLMs (e.g., Llama 3 or Mistral) could be fine-tuned using Low-Rank Adaptation (LoRA) for classification, provided sufficient hardware resources are available.
3. **Advanced Hyperparameter Tuning**:
   - Systematic search for optimal learning rates, dropout rates, and batch sizes using frameworks like Optuna to further maximize classification performance (F1-score).
4. **Knowledge Distillation**:
   - Distill knowledge from a very large model into a smaller, highly efficient Transformer model that maintains high predictive accuracy but runs at extremely fast speeds.
