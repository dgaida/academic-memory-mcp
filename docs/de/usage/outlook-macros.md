# Outlook VBA-Makros und Hilfsskripte

Dieses Projekt enthält eine hochentwickelte Sammlung von Outlook VBA-Makros und Python-Hilfsskripten, um den Export von E-Mails, Kalenderdaten und studentischen Profilen zu automatisieren. Diese Makros bilden die wesentliche Brücke zwischen Ihrem Outlook-Postfach und dem lokalen, agentischen KI-System (MCP University Memory System).

---

## Übersicht und Detail-Logik der Makros

### 1. Master-Export (RunAllExports)
*   **Datei:** `ExportStudentMails.bas`
*   **Wofür benötigt:** Dies ist das zentrale Makro für den täglichen Gebrauch. Es automatisiert die Ausführung der beiden wichtigsten täglichen Exporte hintereinander:
    1.  Ermittlung freier Kalender-Sprechstundenzeiten (ruft `ExportFreeSlots` auf).
    2.  Export aller neuen studentischen E-Mails (ruft `ExportStudentEmails` auf).
    *   *Interaktion:* Beim Start fragt das Makro interaktiv ab, wie viele Tage rückwärts (Standard: 7) nach neuen studentischen E-Mails gesucht werden soll.
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):**
    *   Die freien Zeitfenster werden in `D:\TH_Koeln\academic-memory-mcp\data\free_slots.md` abgelegt und vom LLM bei Antwort-Vorschlägen (Aktion 2) herangezogen.
    *   Die E-Mails werden im Inbox-Ordner gespeichert und stehen direkt für die Gradio GUI zur Klassifizierung, Zusammenfassung und Verarbeitung bereit.

---

### 2. E-Mail Export (ExportStudentEmails)
*   **Datei:** `ExportStudentMails.bas` / `ExportStudentMails_Outlook2007.bas`
*   **Wofür benötigt:** Sucht gezielt nach E-Mails von studentischen Domains (z.B. `@smail.th-koeln.de` oder `@smail.fh-koeln.de`) in Ihrem Posteingang und dem Ordner "Gesendete Elemente" (Sent Items).
    *   *Besonderheit:* Zur Gewährleistung eines sauberen Posteingangs und zur Vermeidung von Dubletten wird die E-Mail nach erfolgreichem Export auf der Festplatte automatisch in Outlook gelöscht.
*   **Speicherorte:**
    *   Posteingang-Mails: `D:\TH_Koeln\StudentMails\Inbox\`
    *   Gesendete Mails: `D:\TH_Koeln\StudentMails\SentItems\`
    *   *Format des Dateinamens:* `YYYYMMDD_HHMMSS - Betreff.msg`
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Dies sind die Rohdaten für den E-Mail-Verarbeitungsworkflow. Das Gradio GUI (`scripts/process_sorted_emails.py`) liest alle MSG-Dateien aus diesen Ordnern ein, klassifiziert sie mittels Machine Learning (Transformer) in Themengebiete, ermittelt den studentischen Nachnamen (Greedy Matching) und archiviert sie strukturiert im Zielpfad.

---

### 3. Kalender-Export / Freie Zeitfenster (ExportFreeSlots)
*   **Datei:** `FreeSlotExport.bas`
*   **Wofür benötigt:** Analysiert Ihre Outlook-Kalender ("Kalender" und "Kalender (Nur dieser Computer)") für die kommenden 14 Tage auf freie Sprechstundentermine.
    *   *Sprechstunden-Logik:* Sucht nach freien 30-Minuten-Zeitfenstern an Werktagen zwischen 13:30 und 16:00 Uhr.
    *   *Ausschlüsse:* Wochenenden, NRW-Feiertage sowie explizit konfigurierte Sperrwochentage (Standard: Mittwoch, Freitag) werden vollautomatisch übersprungen.
*   **Speicherort:** `D:\TH_Koeln\academic-memory-mcp\data\free_slots.md`
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Die generierte Markdown-Datei dient dem E-Mail-Controller als direkte Datenbasis. Wenn Sie in der GUI die **Aktion 2) Antwort schreiben mit Terminvorschlag** wählen, liest das System diese Datei ein. Das LLM extrahiert die freien Slots und baut diese formatiert und personalisiert in Ihren Antwortentwurf in Outlook ein.

---

### 4. Sprechstunden- & Termin-Export (AppointmentExport)
*   **Datei:** `AppointmentExport.bas`
*   **Wofür benötigt:** Exportiert alle bestehenden Kalendereinträge der kommenden 4 Wochen (Dauer, Ort, Thema, Teilnehmer, etc.) aus Ihren Outlook-Kalendern.
*   **Speicherort:** `D:\TH_Koeln\academic-memory-mcp\data\appointments.md`
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Dies ist die primäre Datenquelle für die Termin-GUI (**Appointment Manager**, gestartet via `python scripts/appointment_gui.py`). Der Appointment Manager liest diese Markdown-Tabelle ein und verknüpft jeden Kalendereintrag automatisch mit der lokalen Universitäts-Datenbank. Er zeigt Ihnen sofort den passenden Studentenordner, dessen KI-Konversationszusammenfassung (`.emails_summary.md`), den Steckbrief des Studierenden und ermöglicht den Schnellzugriff auf dessen eingereichte Dateien, sodass Sie perfekt vorbereitet in Besprechungen gehen.

---

### 5. Studierende sammeln (CollectStudentEmails)
*   **Datei:** `CollectStudentEmails.bas`
*   **Wofür benötigt:** Scannt Ihren Posteingang nach allen Absendern mit studentischer Domain, extrahiert deren Anzeigenamen sowie E-Mail-Adressen und legt diese geordnet an.
*   **Speicherort:** `D:\TH_Koeln\academic-memory-mcp\students.yaml`
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Bootstrapping und Pflege der zentralen studentischen Kontaktdatenbank. Wenn die Datei bereits existiert, werden nur neue Studierende hinzugefügt (bestehende Einträge werden geschützt). Die `students.yaml` wird anschließend über das CLI-Kommando `mcp-uni db sync-students` in die lokale SQLite-Metadatendatenbank übertragen, damit das System Namen und Aliase zuverlässig auflösen kann.

---

### 6. Keyword-basierter E-Mail Sorter (SortInboxByConfig)
*   **Datei:** `EmailSorter.bas`
*   **Wofür benötigt:** Ein robuster VBA-Sorter, der direkt in Outlook ausgeführt wird. Er ordnet E-Mails im Posteingang und in den Gesendeten Elementen auf Basis der in `students.yaml` definierten Schlüsselwörter (z.B. "Bachelorthesis", "Praxisprojekt") den jeweiligen Studierenden zu und speichert diese als MSG-Dateien direkt in den entsprechenden lokalen Dateiordnern auf Ihrer Festplatte ab.
*   **Speicherort:** Speichert die Dateien direkt in den individuellen Pfaden, die in `students.yaml` unter `folders` konfiguriert sind (z.B. `C:\Ablage\Mustermann\Bachelorthesis\`).
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Dient Anwendern, die eine physische Vorsortierung ihrer E-Mails direkt aus Outlook heraus bevorzugen, ohne den Gradio-Workflow zu verwenden. Die sortierten Mails werden bei nachfolgenden Indizierungsläufen durch den Crawler (`mcp-uni index`) erfasst und in den Wissensgraphen integriert.

---

### 7. Adress-Enrichment (EnrichStudentEmailsFromBody)
*   **Datei:** `EnrichStudentEmailsFromBody.bas`
*   **Wofür benötigt:** Durchsucht den Betreff und den gesamten Textkörper aller Outlook-Mails nach Vor- und Nachnamen bereits bekannter Studierender (aus der `students.yaml`).
*   **Speicherort:** Aktualisiert die Datei `D:\TH_Koeln\academic-memory-mcp\students.yaml`.
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Findet das Makro Übereinstimmungen, trägt es die zugehörige Absender- oder Empfänger-E-Mail-Adresse automatisch als alternative Adresse in der `students.yaml` ein. Dies löst das Problem, dass Studierende oft von privaten Adressen (z.B. Gmail, GMX) schreiben. Das System reichert das Profil an, sodass nachfolgende E-Mail-Zuordnungen und Suchen (im Index und der GUI) die private E-Mail-Adresse automatisch dem richtigen Studierenden zuordnen.

---

### 8. Langzeit-Archivierung (ArchiveOldStudentMails)
*   **Datei:** `ArchiveOldStudentMails.bas` / `ArchiveOldStudentMails_Outlook2007.bas`
*   **Wofür benötigt:** Zur langfristigen Ausmistung und Pflege des Outlook-Postfachs. Das Makro sucht nach studentischen E-Mails, die älter als ein Jahr (`ARCHIVE_AGE_YEARS = 1`) sind.
*   **Speicherort:** Exportiert die E-Mails strukturiert auf die Festplatte unter:
    `D:\TH_Koeln\StudentMails\<E-Mail-Adresse>\Inbox\` (bzw. `SentItems\`)
    *   *Outlook-Aktion:* Nach dem Export werden die Mails in Outlook in den Papierkorb verschoben, um das Postfach schlank und performant zu halten.
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Die archivierten MSG-Dateien verbleiben auf der Festplatte und werden vom Crawler (`mcp-uni index`) weiterhin erfasst, indiziert und stehen über die Vektorsuche (`mcp-uni search` oder RAG) für historische Suchen und Ähnlichkeitsvergleiche (Similarity-Anzeige in der GUI) voll zur Verfügung.

---

### 9. Betreff-basierter Export (ExportMailsBySubjectAndAge)
*   **Datei:** `ExportMailsBySubjectAndAge.bas`
*   **Wofür benötigt:** Ein Spezialexport-Makro, das gezielt nach alten Mails (> 1 Jahr) sucht, die ein bestimmtes Schlagwort im Betreff enthalten (z.B. "Nachteilsausgleich", "PO-Wechsel", "Härtefall").
*   **Speicherort:** Speichert die E-Mails als `.msg`-Dateien im dedizierten Verzeichnis:
    `D:\TH_Koeln\StudentMails\SubjectExport\`
    *   *Outlook-Aktion:* Löscht die Mails nach erfolgreichem Export aus Outlook.
*   **Was wird mit den Exports gemacht (Downstream-Nutzung):** Dient zur gezielten Sammlung historischer Fallbeispiele. Die exportierten E-Mails können als Trainingsdaten für den Machine-Learning-Klassifikator herangezogen werden oder als Wissensquelle für RAG-Modulordner indiziert werden, um dem LLM fundiertes Wissen über Sonderfall-Entscheidungen (z.B. genehmigte Härtefälle) bereitzustellen.

---

## Python Hilfsskripte im Makro-Kontext

### Ordner-Enrichment (`enrich_yaml_from_config.py`)
*   **Datei:** `outlook_macro/enrich_yaml_from_config.py`
*   **Wofür benötigt:** Wenn Sie bereits eine bestehende Ordnerstruktur für Studierende besitzen (z.B. aus dem EmailSorter-Format `email_config.md`), liest dieses Skript diese Struktur ein und trägt die Ordnerpfade sowie passende Keywords für jeden bekannten Studierenden automatisch in die `students.yaml` ein.
*   **Was passiert mit den Daten:** Die `students.yaml` wird mit den physischen Ordnerpfaden der Studierenden angereichert. Dies ermöglicht dem System bei der E-Mail-Archivierung (GUI), die E-Mails direkt in die echten Ordner der Studierenden auf der Festplatte einzusortieren (z.B. `Semester/Mustermann/Bachelorthesis`).

---

## Installation der Makros in Outlook

1.  Öffnen Sie Microsoft Outlook.
2.  Drücken Sie `ALT + F11`, um den integrierten VBA-Editor (Microsoft Visual Basic for Applications) zu öffnen.
3.  Klicken Sie im Menü auf `Einfügen -> Modul`, um ein neues leeres Modul zu erstellen.
4.  Kopieren Sie den Inhalt der gewünschten `.bas`-Dateien aus dem Ordner `outlook_macro/` dieses Projekts in das neue Modulfenster.
5.  **Wichtig:** Passen Sie die Pfadkonstanten (wie `ACCOUNT_NAME`, `YAML_FILE_PATH` oder `OUTPUT_PATH`) am Anfang der Module an Ihre lokale Ordnerstruktur an!
6.  Speichern Sie das VBA-Projekt (`STRG + S`).
7.  Sie können die Makros nun jederzeit direkt in Outlook über die Tastenkombination `ALT + F8` (Makro-Auswahlfenster) auswählen und starten.
