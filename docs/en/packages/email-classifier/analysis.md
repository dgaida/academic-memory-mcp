# XAI & Visualization

Tools for analyzing the model and data distribution.

## XAI Analysis (`xai_analysis.py`)

Uses SHAP (SHapley Additive exPlanations) to explain which words influenced the model's decision the most.

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
