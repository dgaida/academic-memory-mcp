# Script Usage

This section explains the use of user-focused scripts with concrete examples.

## Email Sorting (`sort_emails.py`)

This script sorts emails based on their classification, semester, and student name into a structured folder hierarchy.

**Command:**
```bash
python -m email_classifier.scripts.sort_emails /path/to/source --config config/class_paths.yaml
```

### Before/After Example

**Before:**
```text
/source/
├── 20240115_103000 - Question about project.msg
├── 20240220_141500 - Registration bachelor thesis.msg
└── 20231210_090000 - Homework.msg
```

**After:**
```text
/destination/
├── WS_2023_24/
│   └── Mueller/
│       └── Inbox/
│           └── 20231210_090000 - Homework.msg
├── SoSe_2024/
│   ├── Schmidt/
│   │   └── Inbox/
│   │       └── 20240115_103000 - Question about project.msg
│   └── Weber/
│       └── Inbox/
│           └── 20240220_141500 - Registration bachelor thesis.msg
└── sorted_emails.md  # Summary report
```

---

## Single Prediction (`predict.py`)

Classifies a single email and outputs the probability distribution.

**Command:**
```bash
python -m email_classifier.scripts.predict /path/to/email.msg
```

**Example Output:**
```text
Classification for: 'Question about project.msg'
Result: InformatikProjekt (Confidence: 0.92)

Probabilities:
- InformatikProjekt: 0.92
- BachelorThesis: 0.05
- Other: 0.03
```

---

## Batch Classification (`classify_folder.py`)

Moves all emails in a folder into subfolders named after the predicted classes (without semester/student logic).

**Command:**
```bash
python -m email_classifier.scripts.classify_folder /path/to/source
```

**Result Structure:**
```text
/source/
├── BachelorThesis/
│   └── mail1.msg
├── InformatikProjekt/
│   └── mail2.msg
└── Other/
    └── mail3.msg
```
