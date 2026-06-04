# E-Mail Management Workflow

Dieser Workflow beschreibt den Prozess vom Erhalt einer E-Mail bis zur Erstellung eines Antwort-Entwurfs in Outlook.

## 1. Export aus Outlook
Der Prozess beginnt in Outlook. Verwenden Sie die bereitgestellten VBA-Makros, um relevante Daten zu exportieren:
- **Studenten-E-Mails:** Exportiert E-Mails von Studenten-Domains als `.msg` Dateien.
- **Freie Termine:** Exportiert freie Zeitfenster aus Ihrem Kalender in eine YAML-Datei (`free_slots.yaml`).

## 2. Klassifizierung und Sortierung
Führen Sie das Sortier-Skript aus:
```bash
python -m mcp_university.classifier.sort_emails --source ./inbox --target ./sorted_mails
```
Das System nutzt den `EmailClassifier`, um die Mails nach Themen (z.B. Bachelor Thesis, Projekt) zu kategorisieren und in entsprechende Unterordner zu verschieben.

## 3. Analyse und Antwort-Generierung
Nach der Sortierung wird `process_sorted_emails.py` ausgeführt. Das Skript führt folgende Schritte für jede E-Mail durch:

1.  **Kontext-Analyse:** Das System analysiert andere E-Mails im Zielordner (den bisherigen Verlauf), um den Kontext der aktuellen Anfrage zu verstehen.
2.  **Termin-Check:** Prüft, ob der Student um einen Termin bittet. Falls ja, werden die `free_slots.yaml` genutzt, um einen Vorschlag zu machen oder den Termin direkt zu buchen.
3.  **Notwendigkeits-Check (Necessity Check):** Ein LLM entscheidet, ob die E-Mail überhaupt eine Antwort erfordert (oder ob es sich z.B. nur um eine Information handelt).
4.  **Entwurf schreiben:** Falls eine Antwort nötig ist, generiert der Agent unter Berücksichtigung der Skill-Vorgaben und der Persona (Daniel Gaida) einen Antworttext.
5.  **Outlook Integration:** Es wird automatisch ein Entwurf ("Draft") im Outlook-Ordner "Work in Progress" erstellt. Die Original-Mail wird als Anhang beigefügt.

## 4. Überprüfung (Gradio GUI)
Am Ende des Prozesses startet automatisch eine Gradio-Weboberfläche. Hier können Sie:
- Die getroffenen Klassifizierungen überprüfen.
- Mails bei Bedarf manuell in andere Kategorien verschieben.
- Den Status der verarbeiteten Mails einsehen.

## 5. Abschlussbericht
Das Skript erstellt eine Datei `processed_emails.md`, die eine tabellarische Übersicht über alle verarbeiteten Mails und deren Status (z.B. "Entwurf erstellt", "Termin gebucht", "Keine Antwort nötig") enthält.
