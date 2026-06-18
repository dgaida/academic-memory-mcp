# Outlook VBA-Makros

Dieses Projekt enthält eine Sammlung von Outlook VBA-Makros, um den Export von E-Mails und Kalenderdaten zu automatisieren. Diese Makros bilden die Brücke zwischen Ihrem Outlook-Postfach und dem lokalen KI-System.

---

## Übersicht der Makros

### 1. Master-Export (RunAllExports)
**Datei:** `ExportStudentMails.bas`
Dies ist das zentrale Makro für den täglichen Gebrauch. Es führt nacheinander zwei Aktionen aus:
1. Exportiert freie Kalender-Slots (ruft `ExportFreeSlots` auf).
2. Exportiert studentische E-Mails aus Posteingang und Gesendeten Elementen (ruft `ExportStudentEmails` auf).
Sie werden beim Start gefragt, wie viele Tage rückwärts (Standard: 7) nach neuen E-Mails gesucht werden soll.

### 2. E-Mail Export (ExportStudentEmails)
**Datei:** `ExportStudentMails.bas`
Sucht in Ihrem Postfach nach E-Mails von studentischen Domains (z.B. `@smail.th-koeln.de`).
- **Speicherort:** `D:\TH_Koeln\StudentMails\Inbox` bzw. `SentItems`.
- **Dateiname:** `YYYYMMDD_HHMMSS - Betreff.msg`.
- **Besonderheit:** Nach dem erfolgreichen Export wird die E-Mail in Outlook gelöscht, um den Posteingang sauber zu halten.

### 3. Kalender-Export (ExportFreeSlots)
**Datei:** `FreeSlotExport.bas`
Analysiert Ihre Kalender ("Kalender" und "Kalender (Nur dieser Computer)") für die nächsten 14 Tage.
- **Logik:** Sucht nach freien 30-Minuten-Fenstern zwischen 13:30 und 16:00 Uhr (konfigurierbar).
- **Ausschlüsse:** Wochenenden, NRW-Feiertage und explizit konfigurierte Wochentage (Standard: Mi, Fr) werden ignoriert.
- **Ausgabe:** Erstellt eine Markdown-Datei `data/free_slots.md`, die vom LLM für Terminvorschläge genutzt wird.

### 4. Studierende sammeln (CollectStudentEmails)
**Datei:** `CollectStudentEmails.bas`
Scannt den Posteingang nach allen Absendern mit studentischer Domain und trägt diese in eine zentrale `students.yaml` ein. Dies ist nützlich, um eine erste Liste aller Studierenden für den `EmailSorter` zu erstellen.

### 5. E-Mail Sorter (SortInboxByConfig)
**Datei:** `EmailSorter.bas`
Ein fortgeschrittener Sorter, der auf der `students.yaml` basiert. Er durchsucht Betreff und Inhalt nach Keywords (z.B. "Bachelorthesis") und verschiebt die E-Mails direkt in die entsprechenden Projektordner auf Ihrer Festplatte.

### 6. Adress-Enrichment (EnrichStudentEmailsFromBody)
**Datei:** `EnrichStudentEmailsFromBody.bas`
Sucht im Textkörper von E-Mails nach Namen bekannter Studierender. Wenn ein Name gefunden wird, wird die E-Mail-Adresse dieser Nachricht als alternative Adresse des Studierenden in der `students.yaml` gespeichert.

### 7. Archivierung (ArchiveOldStudentMails)
**Datei:** `ArchiveOldStudentMails.bas`
Exportiert studentische E-Mails, die älter als ein Jahr sind, als `.msg`-Dateien ins Archiv und verschiebt sie in Outlook in den Papierkorb. Dies dient der langfristigen Ordnung des Postfachs.

### 8. Betreff-basierter Export (ExportMailsBySubjectAndAge)
**Datei:** `ExportMailsBySubjectAndAge.bas`
Ein Spezial-Makro, das gezielt nach Mails mit einem bestimmten Schlagwort (z.B. "Nachteilsausgleich") sucht, die älter als ein Jahr sind, und diese exportiert.

---

## Installation der Makros in Outlook

1. Öffnen Sie Outlook.
2. Drücken Sie `ALT + F11`, um den VBA-Editor zu öffnen.
3. Klicken Sie im Menü auf `Einfügen -> Modul`.
4. Kopieren Sie den Inhalt der gewünschten `.bas`-Dateien aus dem Ordner `outlook_macro/` in das neue Modul.
5. Passen Sie ggf. die Pfade (Konstanten am Anfang der Dateien) an Ihre lokale Struktur an.
6. Speichern Sie das Projekt (`STRG + S`).
7. Sie können die Makros nun über `ALT + F8` in Outlook starten.
