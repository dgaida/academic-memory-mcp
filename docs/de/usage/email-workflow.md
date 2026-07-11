# E-Mail Management Workflow

Dieser Workflow beschreibt den vollständigen Prozess von der Erfassung einer E-Mail in Microsoft Outlook bis hin zur automatisierten Analyse, Klassifizierung und der Erstellung von Antwort-Entwürfen oder Kalendereinträgen. Das System ist darauf ausgelegt, die Kommunikation mit Studierenden effizient zu gestalten und administrative Aufgaben (wie Terminbuchungen oder das Speichern von Abschlussarbeiten) zu automatisieren.

---

## 1. Phase: Daten-Export und Vorbereitung
Der Prozess beginnt direkt in Microsoft Outlook. Da das System lokal auf exportierten Daten arbeitet, müssen zunächst die relevanten Informationen bereitgestellt werden.

### Export aus Outlook
Verwenden Sie die im Projekt bereitgestellten VBA-Makros, um Daten in den `inbox`-Ordner zu exportieren. Eine detaillierte Beschreibung aller verfügbaren Makros und deren Installation finden Sie unter [Outlook VBA-Makros](outlook-macros.md).

- **E-Mails:** Exportiert E-Mails (meist von Studierenden) als `.msg` Dateien. Das System erkennt dabei automatisch Absender, Datum und Betreff.  
- **Kalenderdaten / Termine:** Exportiert freie Zeitfenster aus Ihrem Outlook-Kalender in eine Datei namens `free_slots.md`. Zudem werden auch bestehende Termine im Kalender exportiert, die für die Kalender-GUI zur Übersicht und Planung benötigt werden.  

---

## 2. Phase: Automatische Klassifizierung und Vorsortierung
Die manuelle Ausführung von Sortier-Skripten über die Kommandozeile ist **nicht mehr erforderlich**, da das Einlesen, die Klassifizierung und die Sortierung vollständig über die Gradio GUI (siehe 3. Phase) abgewickelt werden. Das System führt im Hintergrund die gesamte Themen-Erkennung und Namensauflösung durch, wenn Sie die GUI starten oder dort den Scan-Vorgang auslösen.

---

## 3. Phase: Interaktive Verwaltung (Gradio GUI) {#gradio-gui}
Der gesamte Prozess wird nun direkt über die Gradio GUI gesteuert (`scripts/process_sorted_emails.py`). Die GUI bietet zwei spezialisierte Tabs für unterschiedliche Arbeitsweisen.

### Tab 1: Schnell-Einsortierung
Dieser Tab ist für die massenweise Verarbeitung von E-Mails optimiert, bei denen die automatische Klassifizierung bereits ausreicht. Sie müssen keine CLI-Skripte mehr manuell aufrufen; alle Schritte geschehen per Knopfdruck in der GUI.

#### Wie die automatische Klassifizierung & Sortierung funktioniert:  
1. **Themen-Erkennung:** Der [EmailClassifier](../packages/email-classifier/index.md) nutzt ein hochentwickeltes Machine-Learning-Modell (Transformer-basiert), um den Inhalt der E-Mail einer Kategorie zuzuordnen (z.B. *Bachelor Thesis*, *Projekt*, *PO-Wechsel*).  
2. **Dateisystem-Struktur:** Nach der Freigabe in der GUI werden die E-Mails automatisch in eine dreistufige Archiv-Hierarchie verschoben: `Semester (z.B. 2023_24_WS) / Nachname / (Inbox oder SentItems)`.  
3. **Extraktion des Nachnamens:** Der Nachname wird automatisch aus der E-Mail-Adresse oder dem Anzeigenamen ermittelt (Greedy Name Matching / Dot-Separated Fallback).  
    - *Beispiel 1:* `max.mustermann@th-koeln.de` -> Ordner: `Mustermann`  
    - *Beispiel 2:* `mustermann@stud.th-koeln.de` -> Ordner: `Mustermann`  
    - *Beispiel 3:* `Mustermann-Schmidt, Erika <erika.mustermann@...>` -> Ordner: `Mustermann_Schmidt`  
4. **Normalisierung:** Namen werden normalisiert (Umlaute ersetzt, Sonderzeichen bereinigt), um Kompatibilität mit dem Dateisystem zu gewährleisten.  

- **Scan & Klassifizierung:** Liest alle E-Mails aus dem Quellordner ein und weist ihnen mittels Modell eine Klasse zu, ohne sie physisch zu verschieben.  
- **Listenansicht:** Getrennte Anzeige von `Inbox` und `SentItems`.  
- **Entfernen:** Mails, die eine genauere Betrachtung erfordern, können per Index-Auswahl in den zweiten Tab verschoben werden.  
- **Anhänge:** Für jede Mail kann bereits hier ausgewählt werden, ob Anhänge beim Archivieren gespeichert werden sollen.  
  - **Speicherort & Pfad der Anhänge:** Wenn die Option ausgewählt ist, werden die Anhänge automatisch direkt im studentischen Hauptordner (`Semester / Nachname /`) abgelegt (Elternordner des archivierten E-Mail-Ordners).  
  - *Beispiel:* Wenn eine Mail als `Bachelor Thesis` für den Studenten `Mustermann` im Semester `2023_24_WS` archiviert wird (E-Mail-Pfad: `2023_24_WS/Mustermann/Inbox/20231120_143000_Expose.msg`), wird der Anhang (z.B. `Expose_Max_Mustermann.pdf`) im folgenden Ordner gespeichert:  
    `2023_24_WS/Mustermann/Expose_Max_Mustermann.pdf`  
- **Archivieren:** Alle verbleibenden Mails in den Listen werden mit einem Klick direkt in ihre jeweiligen Archiv-Pfade verschoben.  

### Tab 2: Detail-Ansicht & Verarbeitung
Hier landen Mails, die aus Tab 1 entfernt wurden, oder die eine tiefergehende Analyse benötigen.

- **KI-Zusammenfassung:** Für jede Mail wird eine prägnante 2-Satz-Zusammenfassung generiert.  
- **Kontext & Ähnlichkeit:** Anzeige der ähnlichsten E-Mails aus dem Archiv (Similarity Search).  
- **Aktions-Auswahl:** Manuelle Auswahl der Aktion (Antworten, Termin buchen, etc.) und des Zielordners.  
- **Anhänge:** Option zum gezielten Speichern von Mail-Anhängen.  

---

## 4. Phase: KI-gestützte Analyse (Hintergrund & RAG)
Während der Arbeit in der GUI (insbesondere im Detail-Tab 2) führt das System im Hintergrund eine tiefgehende KI-Analyse der E-Mails durch. Ein zentrales Element ist hierbei der **RAG-Prozess (Retrieval Augmented Generation)**:

*   **Semantische Suche:** Auf Basis des E-Mail-Inhalts sucht das System in einer lokalen Vektordatenbank (Qdrant) nach hochrelevanten Dokumenten wie Prüfungsordnungen, Modulhandbüchern oder früheren E-Mail-Konversationen.  
*   **Wissens-Injektion:** Diese gefundenen Informationen werden als zusätzlicher Kontext in den Prompt für das LLM injiziert. Dadurch ist die KI in der Lage, hochgradig präzise und fachlich korrekte Antworten zu entwerfen, die genau auf den aktuellen Fall und die Regularien der TH Köln abgestimmt sind.  
*   **Erhöhte Antwortqualität:** Durch den RAG-Prozess werden Halluzinationen des LLMs minimiert und es können konkrete Paragraphen oder Fristen korrekt genannt werden.  
*   **Verlinkung zur Technik:** Eine detaillierte Erläuterung der mehrstufigen Filterung, Vektorsuche und des gesamten technischen Ablaufs finden Sie in der technischen Dokumentation unter [RAG Prozess](rag-process.md).  

---

## 5. Phase: Aktions-Vorschläge & GUI-Interaktion
Basierend auf der KI-gestützten Analyse schlägt das System eine von sechs Aktionen vor. Diese Auswahl wird in der GUI vorselektiert und kann vom Benutzer manuell überprüft, angepasst oder überschrieben werden.

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
**Dies ist die zentrale Aktion, bei der die Abgabe einer Abschlussarbeit automatisch verarbeitet und detektiert wird.** Wenn der E-Mail-Klassifizierer oder der Benutzer in der GUI eine E-Mail als finale Abgabe einstuft, wird diese Aktion ausgewählt. Sie kombiniert folgende automatisierte Schritte für Abschlussarbeiten:

1. **Anhänge speichern:** Alle E-Mail-Anhänge werden via `save_email_attachments` automatisch direkt im übergeordneten studentischen Ordner (`Semester / Nachname /`) abgelegt.  
2. **Kolloquium-Konfiguration (`config.json`):** Es wird automatisch eine `config.json` Datei im Hauptordner des Studenten mittels `create_colloquium_config` angelegt (bzw. aktualisiert mit dem Dateinamen der PDF-Arbeit aus dem Anhang). Diese Datei dient als Konfiguration für den *colloquium-protocol-creator*.  
3. **Kalender-Erinnerung:** Ein Kalendereintrag (Sprechstundentermin/Erinnerung) wird via `manage_calendar_appointment` für genau **7 Tage nach E-Mail-Eingang (um 08:00 Uhr)** angelegt, um an das Lesen und Bewerten der Arbeit zu erinnern.  
4. **Antwort-Entwurf:** Ein Outlook-Antwortentwurf zur Bestätigung des Empfangs der Abschlussarbeit wird automatisch erstellt.  

#### 6) Termin für Kolloquium (mit `config.json` Automatisierung)
Ähnlich wie Aktion 3, jedoch wird hierbei die Dauer fest auf **60 Minuten** eingestellt und ein spezieller Betreff gewählt. Zudem wurde diese Aktion erheblich weiterentwickelt, um den gesamten Kolloquiumsprozess zu automatisieren:

1. **Erstellung/Aktualisierung der `config.json`:**  
   Das System legt im Ordner des Studenten automatisch eine Konfigurationsdatei namens `config.json` an (oder aktualisiert eine bestehende). Diese enthält alle wichtigen Parameter für den Vortrag und optionale Folgeprozesse (wie z.B. eine automatisierte Folien-Bewertung mittels Gemini oder das Kompilieren von PDFs).

2. **Automatische Termin-Eintragung:**  
   Datum (Format: `DD.MM.YYYY`) und Uhrzeit (Format: `HH:MM`) des Kolloquiums werden automatisch aus der E-Mail extrahiert, im Outlook-Kalender verbucht (Dauer: 60 Minuten) und direkt in die `config.json` des Studenten eingetragen.

**Beispiel für die erzeugte/aktualisierte `config.json`:**
```json
{
  "task": "colloquium",
  "description": "Kolloquium auf dem Campus Gummersbach mit automatischer Gemini-Bewertung",
  "pdf": {
    "filename": "Bachelorarbeit.pdf"
  },
  "colloquium": {
    "date": "15.11.2026",
    "time": "14:00",
    "location_type": "campus",
    "room": "3.228"
  },
  "llm": {
    "api_choice": null,
    "model": null,
    "groq_free": true
  },
  "gemini_evaluation": {
    "enabled": false,
    "model": "gemini-2.0-flash-exp"
  },
  "output": {
    "folder": null,
    "compile_pdf": true,
    "fill_form_only": true
  }
}
```
Diese Datei dient nachgelagert auch zur automatisierten Bewertung von Präsentationsfolien oder dem Ausfüllen von Formularen.

---

## Weiterführende Links  
- [Outlook VBA-Makros](outlook-macros.md): Details zu den Export-Skripten.  
- [Datenbank-Prozesse](database-processes.md): Erfahren Sie mehr über die Verwaltung der `profiles_tracking.db`.  
- [E-Mail Klassifizierung](../packages/email-classifier/index.md): Details zu den Machine-Learning Modellen.  
- [Konfiguration](../configuration.md): So passen Sie Pfade und LLM-Einstellungen an.  


!!! info "Automatische Archivierung"
    Das System schlägt für bestimmte E-Mails automatisch die Aktion **"4) Nur archivieren"** vor:  
    - **Alte E-Mails:** E-Mails, die älter als der konfigurierte Schwellenwert (z.B. 6 Monate) sind.  
    - **SentItems:** E-Mails im Ordner `SentItems` benötigen nie eine Antwort-Aktion.  
    - **Bereits beantwortet:** E-Mails, für die das System erkennt, dass kein Handlungsbedarf besteht.  
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
