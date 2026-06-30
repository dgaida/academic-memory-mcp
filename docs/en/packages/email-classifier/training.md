# Training & Evaluation

This section describes how models are trained, validated, and tested.

## Train Model (`train.py`)

Training expects a folder structure where subfolders represent classes. Within these class folders, there should be `Inbox` and `SentItems`.

**Command:**
```bash
python -m email_classifier.scripts.train /path/to/train_data --mode combined --method xgboost
```

### Parameters:
- `--mode`: `tfidf`, `embedding`, or `combined` (Default: `combined`).
- `--method`: `xgboost`, `randomforest`, or `transformer`.
- `--model-path`: Optional path to save the model.

Training automatically creates diagrams for the confusion matrix and training progress (for Transformer).

---

## Evaluate Model (`evaluate.py`)

Calculates detailed metrics (accuracy, precision, recall, f1) for an existing model on a test dataset.

**Command:**
```bash
python -m email_classifier.scripts.evaluate /path/to/test_data --mode combined
```

**Result:**
- Console output of the `classification_report`.
- Generation of a heatmap of the confusion matrix as PNG.
- Storage of metrics in `metrics.json`.

## Feature Modeling (Feature Extraction)

The `EmailClassifier` supports three different modes for feature extraction:

1.  **TF-IDF (`tfidf`)**:
    - **Mechanism:** Uses Term Frequency-Inverse Document Frequency. Word frequencies are counted and weighted.
    - **Advantages:** Fast, well-interpretable, effective with clearly defined technical terms.
    - **Disadvantages:** Ignores word order and semantics.

2.  **Embeddings (`embedding`)**:
    - **Mechanism:** Uses `Sentence-Transformers` (`BAAI/bge-m3`) to project the text into a high-dimensional vector space.
    - **Advantages:** Captures semantic meaning and synonyms.
    - **Disadvantages:** More computationally intensive, harder to interpret.

3.  **Combined (`combined`)**:
    - **Mechanism:** Concatenates TF-IDF vectors with embedding vectors.
    - **Advantages:** Combines the precision of keywords with deep semantic understanding. Usually highest accuracy.

### Model Naming
During training, the chosen method and mode are automatically appended to the file name (e.g., `email_classifier_transformer.pkl`) to avoid confusing models.
