# XAI & Visualization

Tools for analyzing the model and data distribution.

## XAI Analysis (`xai_analysis.py`)

Uses SHAP (SHapley Additive exPlanations) to explain which words influenced the model's decision the most.

**Important Note on Model Compatibility:**
- **ML Models (TF-IDF):** XAI analysis works **exclusively** for classical machine learning models running in **TF-IDF mode** (`--mode tfidf`), since the SHAP `TreeExplainer` relies directly on the TF-IDF vectorizer.
- **Transformer & Other Modes:** XAI analysis does **not** work for the Transformer model or for ML models trained in `embedding` or `combined` modes.

**Command:**
```bash
python -m email_classifier.scripts.xai_analysis --test-data-path /path/to/test_data
```

**Result:**
The script outputs the top 5 words for each class that were responsible for a positive prediction of that class. This helps to validate whether the model is learning on the correct features.

---

## Plot Data Distribution (`plot_data_distribution.py`)

Visualizes the number of emails per class in the training and test data.

**Command:**
```bash
python -m email_classifier.scripts.plot_data_distribution --train-dir /path/to/train --test-dir /path/to/test --output-dir ./plots
```

---

## Find Top Words (`top_words.py`)

A fast script to statistically determine the most frequent words per class.

**Important Note on Model Independence:**
- This script is **completely model-independent** and works directly on the raw text data using statistical TF-IDF calculations.
- It **does not require or load any trained model** (neither classical ML models nor the Transformer model). It is meant for pure data analysis before or after training.

**Command:**
```bash
python -m email_classifier.scripts.top_words /path/to/data
```
