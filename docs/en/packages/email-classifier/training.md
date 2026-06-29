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
