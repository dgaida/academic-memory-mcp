# Email Parsing and Name Extraction

This page describes in detail how the system extracts names from email addresses and display names. This logic is crucial for correctly sorting emails into student folders.

## Basic Logic (Hierarchical)

The system follows a strict hierarchy to determine the surname of a sender or recipient:

1.  **"im Auftrag von" Recognition**: If an email was sent on behalf of someone else, the actual sender is focused.
2.  **Greedy Name Matching (Primary)**:
    *   The display name (e.g., "Mustermann Max") is split into its individual parts.
    *   These parts are matched against the "local part" of the email address (the part before the @).
    *   If a part of the display name is found within the local part, it is identified as the surname.
    *   *Example*: `Mustermann Max <mustermann@example.com>` -> "Mustermann" is found in the local part and is therefore the surname.
3.  **Dot-Separated Local Part (Fallback 1)**:
    *   If no match with the display name is possible, the local part is split at dots (`.`).
    *   The system checks the segments from back to front and ignores generic terms (such as "info", "studium").
    *   *Example*: `max.mustermann@smail.th-koeln.de` -> "Mustermann".
4.  **Generic Fallbacks (Fallback 2)**:
    *   Commas in the display name (`Surname, Firstname`).
    *   Last word in the display name.
    *   Local part formatting (uppercase recognition).

## Examples

| Input (Sender/Recipient) | Extracted Surname | Reason |
| :--- | :--- | :--- |
| `Mustermann, Max` | **Mustermann** | Comma separation |
| `Mustermann Max <mustermann@example.com>` | **Mustermann** | Greedy Match (Mustermann in local part) |
| `max.mustermann@th-koeln.de` | **Mustermann** | Dot-separated local part |
| `'Hans Müller' <mueller@th-koeln.de>` | **Müller** | Greedy Match (mueller in local part, umlaut normalization) |
| `info@th-koeln.de` | **Unknown** | Generic local part |

## Implementation

The logic is implemented in `mcp_university/classifier/sort_emails.py` in the function `extract_lastname`.

```python
def extract_lastname(sender_raw: str) -> str:
    # Hierarchical Logic:
    # 1. on behalf of
    # 2. Greedy Match (Display Name vs Local Part)
    # 3. Dot-Separated Local Part
    # 4. Generic Fallbacks
    ...
```

## Important Rules for Developers

*   **No deletion of comments**: The explanatory comments in `extract_lastname` are essential for understanding edge cases.
*   **Google-Style Docstrings**: Every change must be documented.
*   **Umlaut Handling**: The system normalizes names for comparison (`Müller` vs `mueller`) but returns the original name (Title Case).
