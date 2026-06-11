# Email Classification

The system includes a powerful subpackage for the automated classification of student emails (e.g., bachelor's thesis, internship project).

## Training the Model
To use the classifier, it must first be trained with example data. A folder structure is expected where each subfolder represents a class and contains the emails (.msg).

```bash
python3 mcp_university/classifier/train.py /path/to/training_data --mode tfidf --method transformer
```

You can choose between `randomforest`, `xgboost`, and `transformer` (default).

## Classifying an Email
After training, a single email file can be classified:

```bash
python3 mcp_university/classifier/predict.py /path/to/email.msg
```

The output contains the most likely class as well as the confidence and a detailed probability distribution.

## XAI Analysis (Interpretability)
To understand which words were particularly important for classification, XAI analysis can be used. This uses SHAP values to calculate the influence of individual words on the prediction.

```bash
python3 mcp_university/classifier/xai_analysis.py --model-path data/email_classifier_xgboost_tfidf.pkl --test-data-path /path/to/test_data
```

The script analyzes up to 20 emails per class and returns the top 5 words that are most characteristic for the respective class.

## Email Sorting (Student Folders)
The most powerful script sorts emails not only by class but also by semester and student (last name):

```bash
python3 mcp_university/classifier/sort_emails.py /source/folder --config config/class_paths.yaml --model data/email_classifier_xgboost_combined.pkl
```

It automatically recognizes:  
- **Semester:** Based on the email date (Summer/Winter semester).  
- **Student:** Extracts the last name from `smail.th-koeln.de` addresses or display names.  
- **Direction:** Sorts into `Inbox` or `SentItems` subfolders.  
- **Report:** Creates a `sorted_emails.md` with an overview of all moved emails.  

## Batch Classification
To automatically sort an entire folder of emails (classification only):
```bash
python3 mcp_university/classifier/classify_folder.py /source/folder --model data/email_classifier_xgboost_combined.pkl
```
This moves the emails into subfolders named after the predicted classes.

## Visualizing Data Distribution
To visualize the distribution of emails per class (split into Inbox and SentItems), the following script can be used:

```bash
python3 mcp_university/classifier/plot_data_distribution.py --train-dir /path/to/train_data --test-dir /path/to/test_data --output-dir data
```

This generates two high-resolution PNG files in `data/`:  
- `train_data_distribution.png`  
- `test_data_distribution.png`  

## Feature Modeling (Feature Extraction)

The `EmailClassifier` supports three different modes for feature extraction:

1.  **TF-IDF (`tfidf`)**:  
    - **Functionality:** Uses Term Frequency-Inverse Document Frequency. Word frequencies are counted and weighted.  
    - **Pros:** Fast, well-interpretable, effective for clearly defined technical terms.  
    - **Cons:** Ignores word order and semantics.  

2.  **Embeddings (`embedding`)**:  
    - **Functionality:** Uses `Sentence-Transformers` (`BAAI/bge-m3`) to project the text into a high-dimensional vector space.  
    - **Pros:** Captures semantic meaning and synonyms.  
    - **Cons:** More computationally intensive, harder to interpret.  

3.  **Combined (`combined`)**:  
    - **Functionality:** Concatenates TF-IDF vectors with embedding vectors.  
    - **Pros:** Combines precision of keywords with deep semantic understanding. Usually highest accuracy.  

### Model Naming
During training, the chosen method and mode are automatically appended to the filename (e.g., `email_classifier_transformer.pkl`) to avoid confusion between models.
