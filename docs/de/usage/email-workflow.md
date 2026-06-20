# E-Mail Management Workflow

Dieser Workflow beschreibt den vollständigen Prozess von der Erfassung einer E-Mail in Microsoft Outlook bis hin zur automatisierten Analyse, Klassifizierung und der Erstellung von Antwort-Entwürfen oder Kalendereinträgen. Das System ist darauf ausgelegt, die Kommunikation mit Studierenden effizient zu gestalten und administrative Aufgaben (wie Terminbuchungen oder das Speichern von Abschlussarbeiten) zu automatisieren.

---

## 1. Phase: Daten-Export und Vorbereitung
Der Prozess beginnt direkt in Microsoft Outlook. Da das System lokal auf exportierten Daten arbeitet, müssen zunächst die relevanten Informationen bereitgestellt werden.

### Export aus Outlook
Verwenden Sie die im Projekt bereitgestellten VBA-Makros, um Daten in den `inbox`-Ordner zu exportieren. Eine detaillierte Beschreibung aller verfügbaren Makros und deren Installation finden Sie unter [Outlook VBA-Makros](outlook-macros.md).

- **E-Mails:** Exportiert E-Mails (meist von Studierenden) als `.msg` Dateien. Das System erkennt dabei automatisch Absender, Datum und Betreff.  
- **Kalenderdaten:** Exportiert freie Zeitfenster aus Ihrem Outlook-Kalender in eine Datei namens `free_slots.md`. Diese dient als Grundlage für automatisierte Terminvorschläge.  

---

## 2. Phase: Klassifizierung und Sortierung
Bevor eine inhaltliche Analyse stattfindet, werden die E-Mails nach Themen sortiert.

### Automatisches Einsortieren
Führen Sie das Sortier-Skript aus:
```bash
python -m mcp_university.classifier.sort_emails --source ./inbox --target ./sorted_mails
```

**Was passiert hier?**

1. **Themen-Erkennung:** Der [EmailClassifier](email-classification.md) nutzt ein Machine-Learning-Modell (Transformer-basiert), um den Inhalt der Mail einer Kategorie zuzuordnen (z.B. *Bachelor Thesis*, *Projekt*, *PO-Wechsel*).  
2. **Dateisystem-Struktur:** Die E-Mails werden in eine dreistufige Hierarchie verschoben: `Semester (z.B. 2023_24_WS) / Nachname / (Inbox oder SentItems)`.  
3. **Extraktion des Nachnamens:** Der Nachname wird automatisch aus der E-Mail-Adresse oder dem Anzeigenamen ermittelt.  
    - *Beispiel 1:* `max.mustermann@th-koeln.de` -> Ordner: `Mustermann`  
    - *Beispiel 2:* `mustermann@stud.th-koeln.de` -> Ordner: `Mustermann`  
    - *Beispiel 3:* `Mustermann-Schmidt, Erika <erika.mustermann@...>` -> Ordner: `Mustermann_Schmidt`  
4. **Normalisierung:** Namen werden normalisiert (Umlaute ersetzt, Sonderzeichen bereinigt), um Kompatibilität mit dem Dateisystem zu gewährleisten.  

---

## 3. Phase: KI-gestützte Analyse (Analyse & Kontext)
Nachdem die Mails sortiert sind, erfolgt die Analyse durch `process_sorted_emails.py`. In dieser Phase wird der notwendige Kontext für eine spätere Bearbeitung gesammelt.

**Inhalte dieser Phase:**

- **Gradio GUI Zusammenfassung:** In der [Gradio GUI](#gradio-gui) wird für jede Mail eine separate, kurze (2 Sätze) Zusammenfassung des aktuellen Inhalts angezeigt, um einen schnellen Überblick zu ermöglichen. Die vollständige Konversations-Zusammenfassung (`.emails_summary.md`) wird erst in **Phase 6** bei der Ausführung einer Antwort-Aktion erstellt, um Ressourcen zu sparen und den aktuellsten Stand zu garantieren.  
- **RAG-Kontext (Retrieval Augmented Generation):** Das System durchsucht eine Vektordatenbank nach thematisch passenden Informationen (z.B. Prüfungsordnungen), basierend auf dem Inhalt der aktuellen Mail. Dieser Kontext wird ausschließlich für die spätere Antwortgenerierung genutzt. Details zu diesem mehrstufigen Prozess finden Sie unter [RAG-Prozess](rag-process.md).
- **Ähnlichkeits-Suche:** Es wird nach den 3 neuesten, thematisch ähnlichsten E-Mails desselben Studenten im Archiv gesucht, um eine konsistente Historie zu gewährleisten.  
- **Aktions-Klassifizierung:** Das LLM entscheidet vorab, welche der 6 möglichen Aktionen am besten zur E-Mail passt.  

---

## 4. Phase: Aktions-Vorschlag
Basierend auf der Analyse schlägt das System eine von sechs Aktionen vor. Diese Auswahl wird in der GUI vorselektiert.

| Aktion | Beschreibung |
| :--- | :--- |
| **1) Antwort schreiben** | Standard-Antwort basierend auf dem Thema. |
| **2) Antwort mit Terminvorschlag** | Sucht freie Slots und schlägt diese vor. |
| **3) Termin direkt buchen** | Erkennt eine Terminbestätigung und trägt diese ein. |
| **4) Nur archivieren** | Einsortierung in den Archiv-Ordner; keine Antwort nötig. |
| **5) Aufgabe "Anhang lesen"** | Speziell für finale Abgaben (Korrektur-Erinnerung). |
| **6) Kolloquium-Termin** | Spezielle Buchung für Abschlussvorträge. |

---

## 5. Phase: Überprüfung (Gradio GUI) {#gradio-gui}
Der Prozess wird in einer interaktiven Web-Oberfläche kontrolliert (Human-in-the-loop).

**Funktionen der GUI:**

- **Korrektur der Klassifizierung:** Ändern der E-Mail-Klasse via Dropdown (physische Verschiebung beim Speichern).  
- **Aktions-Review:** Überprüfung und ggf. Änderung der vorgeschlagenen Aktion.  
- **Anhänge extrahieren:** Checkbox zum automatischen Speichern von Anhängen im Studentenordner.  
- **Quick-Links:** Direktes Öffnen des Windows-Ordners oder der E-Mail-Datei.  
- **Zusammenfassungen:** Für jede E-Mail wird eine kurze (2 Sätze) Zusammenfassung direkt in der GUI angezeigt, um das schnelle Scannen des Posteingangs zu erleichtern.  

---

## 6. Phase: Ausführung der Aktionen (Details)
Sobald Sie in der GUI auf "Speichern & Ausführen" klicken, wird die gewählte Aktion technisch umgesetzt. Hierbei werden nun auch die **Personen-Steckbriefe** (Student & Eigene Persona) sowie die **Skills** (Fachwissen-Dateien) einbezogen.

### Detail-Logik der Aktionen:

#### Vorbereitung: Konversations-Zusammenfassung
Bevor eine Antwort generiert wird, erstellt das System eine prägnante Zusammenfassung des bisherigen Konversationsverlaufs im Studentenordner (`.emails_summary.md`). Diese dient als wichtiger Kontext für das LLM, um über bisherige Absprachen informiert zu sein.  
- Ein Beispiel für die resultierende Struktur finden Sie unter [Beispiel E-Mail-Strukturen](indexing-details.md#beispiel-e-mail-strukturen).  
- Falls eine E-Mail in der GUI umklassifiziert wurde, bezieht die Zusammenfassung automatisch die neue Ordnerstruktur mit ein.  

#### 1) Antwort schreiben
Das LLM generiert einen Antworttext unter Berücksichtigung Ihres eigenen **Personen-Steckbriefs** (Tonalität, Rolle), des **Studenten-Steckbriefs** und der oben genannten **Konversations-Zusammenfassung**. Details zur Erstellung und Nutzung der Steckbriefe finden Sie unter [Personen-Profile](profiles.md). Es wird automatisch ein Entwurf in Outlook erstellt, der die Original-Mail als Anhang enthält.

#### 2) Antwort schreiben mit einem Terminvorschlag
Das System ruft das Tool `get_appointment_slots` auf, welches die `free_slots.md` ausliest. Die gefundenen Zeiten werden formatiert in den Antwortentwurf integriert.

#### 3) Termin im Kalender anlegen
Wird genutzt, wenn der Student einen Termin bestätigt hat. Das System extrahiert Datum und Uhrzeit und nutzt das Tool `manage_calendar_appointment`, um einen echten Eintrag in Ihrem Outlook-Kalender zu erstellen.

#### 4) E-Mail nur archivieren
Die E-Mail wird im entsprechenden studentischen Archiv-Ordner gespeichert. Es erfolgt keine weitere technische Aktion (wie z.B. ein Antwort-Entwurf).

#### 5) Aufgabe im Kalender anlegen (Finale Abgabe)
Diese Aktion kombiniert mehrere Schritte für Abschlussarbeiten:

1. Anhänge werden via `save_email_attachments` im Studentenordner gespeichert.  
2. Ein Kalendereintrag wird für in **7 Tagen** angelegt, um an die Korrektur zu erinnern.  
3. Ein Antwortentwurf zur Bestätigung des Empfangs wird erstellt.  

#### 6) Termin für Kolloquium
Ähnlich wie Aktion 3, jedoch wird hierbei die Dauer fest auf **60 Minuten** eingestellt und ein spezieller Betreff gewählt.

---

## Weiterführende Links  
- [Outlook VBA-Makros](outlook-macros.md): Details zu den Export-Skripten.  
- [Datenbank-Prozesse](database-processes.md): Erfahren Sie mehr über die Verwaltung der `profiles_tracking.db`.  
- [E-Mail Klassifizierung](email-classification.md): Details zu den Machine-Learning Modellen.  
- [Konfiguration](../configuration.md): So passen Sie Pfade und LLM-Einstellungen an.  
