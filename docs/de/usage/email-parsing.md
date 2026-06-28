# E-Mail Parsing und Namensextraktion

Diese Seite beschreibt detailliert, wie das System Namen aus E-Mail-Adressen und Display-Namen extrahiert. Diese Logik ist entscheidend für die korrekte Einsortierung von E-Mails in die Studentenordner.

## Grundlogik (Hierarchisch)

Das System folgt einer strengen Hierarchie, um den Nachnamen eines Absenders oder Empfängers zu bestimmen:

1.  **"im Auftrag von" Erkennung**: Falls eine E-Mail im Auftrag gesendet wurde, wird der eigentliche Absender fokussiert.
2.  **Greedy Name Matching (Primär)**:
    *   Der Display-Name (z.B. "Mustermann Max") wird in seine Einzelteile zerlegt.
    *   Diese Teile werden mit dem "Local-Part" der E-Mail-Adresse (der Teil vor dem @) abgeglichen.
    *   Wenn ein Teil des Display-Namens im Local-Part vorkommt, wird dieser als Nachname identifiziert.
    *   *Beispiel*: `Mustermann Max <mustermann@example.com>` -> "Mustermann" wird im Local-Part gefunden und ist somit der Nachname.
3.  **Dot-Separated Local Part (Fallback 1)**:
    *   Falls kein Abgleich mit dem Display-Namen möglich ist, wird der Local-Part an Punkten (`.`) aufgeteilt.
    *   Das System prüft die Segmente von hinten nach vorne und ignoriert generische Begriffe (wie "info", "studium").
    *   *Beispiel*: `max.mustermann@smail.th-koeln.de` -> "Mustermann".
4.  **Generische Fallbacks (Fallback 2)**:
    *   Kommata im Display-Namen (`Nachname, Vorname`).
    *   Letztes Wort im Display-Namen.
    *   Local-Part Formatierung (Großbuchstaben-Erkennung).

## Beispiele

| Eingabe (Sender/Empfänger) | Extrahierter Nachname | Grund |
| :--- | :--- | :--- |
| `Mustermann, Max` | **Mustermann** | Komma-Separation |
| `Mustermann Max <mustermann@example.com>` | **Mustermann** | Greedy Match (Mustermann in Local-Part) |
| `max.mustermann@th-koeln.de` | **Mustermann** | Dot-Separated Local Part |
| `'Hans Müller' <mueller@th-koeln.de>` | **Müller** | Greedy Match (mueller in Local-Part, Umlaut-Normalisierung) |
| `info@th-koeln.de` | **Unknown** | Generischer Local-Part |

## Implementierung

Die Logik ist in `mcp_university/classifier/sort_emails.py` in der Funktion `extract_lastname` implementiert.

```python
def extract_lastname(sender_raw: str) -> str:
    # Hierarchische Logik:
    # 1. im Auftrag von
    # 2. Greedy Match (Display Name vs Local Part)
    # 3. Dot-Separated Local Part
    # 4. Generische Fallbacks
    ...
```

## Wichtige Regeln für Entwickler

*   **Keine Löschung von Kommentaren**: Die erklärenden Kommentare in `extract_lastname` sind essenziell für das Verständnis der Randfälle.
*   **Google-Style Docstrings**: Jede Änderung muss dokumentiert werden.
*   **Umlaut-Handling**: Das System normalisiert Namen für den Vergleich (`Müller` vs `mueller`), gibt aber den Originalnamen (Title Case) zurück.
