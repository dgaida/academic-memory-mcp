# Architecture & Internal Modules

This section describes the internal structure of the email classifier and the functioning of the core modules.

## Core Modules

### `engine.py`
Contains the base classes for classification:  
- **`EmailClassifier`**: Manages model loading, preprocessing, and predictions for classical models (RandomForest, XGBoost).  
- **`EmailTransformerClassifier`**: A PyTorch-based implementation for Transformer models.  
- **Vectorization**: Supports TF-IDF, embeddings (BGE-M3), and a combination of both.  

### `controller.py`
The `EmailController` orchestrates the process:  
1. Loading configuration and model.  
2. Parsing incoming emails.  
3. Invoking classification.  
4. Deciding on further actions (sorting, reply generation).  

## Transformer Architecture

For deep learning classification, a Transformer model (Default: `paraphrase-multilingual-MiniLM-L12-v2`) is used.

### Structured Input
Emails are structured before processing to preserve important metadata:
```text
SUBJECT: <Subject> | ATTACHMENTS: <file1.pdf, ...> [SEP] <Email Body (anonymized)>
```
This allows the model to explicitly learn the strong signal effect of subject lines.

### Fine-Tuning  
- The weights of the Transformer backbone are updated.  
- A classification head (linear layer) is applied to the `[CLS]` token.  
- Maximum sequence length: 512 tokens.  
