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
python -m email_classifier.sort_emails --source ./inbox --target ./sorted_mails
```

**Was passiert hier?**

1. **Themen-Erkennung:** Der [EmailClassifier](../packages/email-classifier/index.md) nutzt ein Machine-Learning-Modell (Transformer-basiert), um den Inhalt der Mail einer Kategorie zuzuordnen (z.B. *Bachelor Thesis*, *Projekt*, *PO-Wechsel*).  
2. **Dateisystem-Struktur:** Die E-Mails werden in eine dreistufige Hierarchie verschoben: `Semester (z.B. 2023_24_WS) / Nachname / (Inbox oder SentItems)`.  
3. **Extraktion des Nachnamens:** Der Nachname wird automatisch aus der E-Mail-Adresse oder dem Anzeigenamen ermittelt.  
    - *Beispiel 1:* `max.mustermann@th-koeln.de` -> Ordner: `Mustermann`  
    - *Beispiel 2:* `mustermann@stud.th-koeln.de` -> Ordner: `Mustermann`  
    - *Beispiel 3:* `Mustermann-Schmidt, Erika <erika.mustermann@...>` -> Ordner: `Mustermann_Schmidt`  
4. **Normalisierung:** Namen werden normalisiert (Umlaute ersetzt, Sonderzeichen bereinigt), um Kompatibilität mit dem Dateisystem zu gewährleisten.  

---

## 3. Phase: Interaktive Verwaltung (Gradio GUI) {#gradio-gui}
Der gesamte Prozess wird nun direkt über die Gradio GUI gesteuert (`scripts/process_sorted_emails.py`). Die GUI bietet zwei spezialisierte Tabs für unterschiedliche Arbeitsweisen.

### Tab 1: Schnell-Einsortierung
Dieser Tab ist für die massenweise Verarbeitung von E-Mails optimiert, bei denen die automatische Klassifizierung bereits ausreicht.

- **Scan & Klassifizierung:** Liest alle E-Mails aus dem Quellordner ein und weist ihnen mittels Modell eine Klasse zu, ohne sie physisch zu verschieben.  
- **Listenansicht:** Getrennte Anzeige von `Inbox` und `SentItems`.  
- **Entfernen:** Mails, die eine genauere Betrachtung erfordern, können per Index-Auswahl in den zweiten Tab verschoben werden.  
- **Archivieren:** Alle verbleibenden Mails in den Listen werden mit einem Klick direkt in ihre jeweiligen Archiv-Pfade verschoben.  

### Tab 2: Detail-Ansicht & Verarbeitung
Hier landen Mails, die aus Tab 1 entfernt wurden, oder die eine tiefergehende Analyse benötigen.

- **KI-Zusammenfassung:** Für jede Mail wird eine prägnante 2-Satz-Zusammenfassung generiert.  
- **Kontext & Ähnlichkeit:** Anzeige der ähnlichsten E-Mails aus dem Archiv (Similarity Search).  
- **Aktions-Auswahl:** Manuelle Auswahl der Aktion (Antworten, Termin buchen, etc.) und des Zielordners.  
- **Anhänge:** Option zum gezielten Speichern von Mail-Anhängen.  

---

## 4. Phase: KI-gestützte Analyse (Hintergrund)
Während der Arbeit in der GUI (insbesondere in Tab 2) finden folgende Prozesse statt:

- **RAG-Kontext (Retrieval Augmented Generation):** Das System durchsucht eine Vektordatenbank nach thematisch passenden Informationen.  
- **Aktions-Vorschlag:** Das LLM schlägt basierend auf dem Inhalt eine der 6 Aktionen vor.  

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

!!! info "Termine in der Vergangenheit"
    Sollte ein Termin in der Vergangenheit liegen, wird dieser automatisch erkannt. In diesem Fall wird kein Kalendereintrag erstellt und die E-Mail wird direkt archiviert (Status: `Archiviert (Termin in Vergangenheit)`).

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
- [E-Mail Klassifizierung](../packages/email-classifier/index.md): Details zu den Machine-Learning Modellen.  
- [Konfiguration](../configuration.md): So passen Sie Pfade und LLM-Einstellungen an.  


!!! info "SentItems Archivierung"
    E-Mails im Ordner `SentItems` werden grundsätzlich nur archiviert. Sie benötigen nie eine Antwort-Aktion, unabhängig von ihrem Alter oder dem Status der Konversation.
---



### Diagnose und Logging
Das System protokolliert jeden Schritt der E-Mail-Verarbeitung detailliert in `process_emails.log`. Sollte die GUI keine E-Mails anzeigen, obwohl diese in `sorted_emails.md` gelistet sind, prüfen Sie die Log-Datei auf Warnungen bezüglich fehlender Modelldateien oder Zugriffsproblemen.



## Erstellte Berichte und Dateien

Während der Verarbeitung durch `scripts/process_sorted_emails.py` werden verschiedene Markdown-Dateien im Quellverzeichnis erstellt, um den Status und die Ergebnisse zu dokumentieren.

### 1. `sorted_emails.md`
Dieser Bericht wird direkt nach der initialen Sortierung erstellt und listet alle gefundenen E-Mails und ihre vorläufige Klassifizierung auf.

**Beispiel:**
```markdown
# Sortierte E-Mails

## Bachelor Thesis
- **Mustermann** | Max | Inbox: `D:\Mails\2023_24_WS\Mustermann\Inbox\Frage.msg`
```

### 2. `emails_to_process.md`
Diese Datei enthält eine Liste aller E-Mails, die für die Bearbeitung in der Gradio GUI vorgesehen sind, inklusive Metadaten wie Klasse und Semester.

**Beispiel:**
```markdown
# Zu beantwortende E-Mails

| Student | Klasse | Semester |
| :--- | :--- | :--- |
| Mustermann | Bachelor Thesis | 2023_24_WS |
```

### 3. `processed_emails.md`
Der Abschlussbericht, der nach der Verarbeitung (entweder automatisch oder via GUI) erstellt wird. Er dokumentiert, was mit jeder E-Mail geschehen ist.

**Beispiel:**
```markdown
# Verarbeitete E-Mails

| Student | Betreff | Status |
| :--- | :--- | :--- |
| Mustermann | Frage | Outlook Entwurf (Work in Progress) |
| Schmidt | Termin | Termin gebucht (2023-10-27 10:00) |
| Doe | Alte Mail | Automatisch archiviert (alt (> 6 Monate)) |
```

### 4. `.emails_summary.md` (im Studentenordner)
Eine KI-generierte Zusammenfassung des bisherigen Konversationsverlaufs mit dem Studenten. Diese Datei wird vor der Antwortgenerierung erstellt oder aktualisiert.

### 5. `*_reply.md` (im Studentenordner)
Falls kein Outlook-Entwurf erstellt werden konnte, wird die generierte Antwort als Markdown-Datei im Ordner des Studenten gespeichert.
