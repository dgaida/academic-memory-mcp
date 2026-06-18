# E-Mail Management Workflow

Dieser Workflow beschreibt den vollständigen Prozess von der Erfassung einer E-Mail in Microsoft Outlook bis hin zur automatisierten Analyse, Klassifizierung und der Erstellung von Antwort-Entwürfen oder Kalendereinträgen. Das System ist darauf ausgelegt, die Kommunikation mit Studierenden effizient zu gestalten und administrative Aufgaben (wie Terminbuchungen oder das Speichern von Abschlussarbeiten) zu automatisieren.

---

## 1. Phase: Daten-Export und Vorbereitung
Der Prozess beginnt direkt in Microsoft Outlook. Da das System lokal auf exportierten Daten arbeitet, müssen zunächst die relevanten Informationen bereitgestellt werden.

### Export aus Outlook
Verwenden Sie die im Projekt bereitgestellten VBA-Makros, um Daten in den `inbox`-Ordner zu exportieren:  
- **E-Mails:** Exportiert E-Mails (meist von Studierenden) als `.msg` Dateien. Das System erkennt dabei automatisch Absender, Datum und Betreff.  
- **Kalenderdaten:** Exportiert freie Zeitfenster aus Ihrem Outlook-Kalender in eine Datei namens `free_slots.yaml`. Diese dient als Grundlage für automatisierte Terminvorschläge.  

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
2. **Dateisystem-Struktur:** Die E-Mails werden in eine dreistufige Hierarchie verschoben: `Semester (z.B. 2023_24_WS) / Nachname_Vorname / (Inbox oder SentItems)`.  
3. **Normalisierung:** Namen werden normalisiert (Umlaute ersetzt, Sonderzeichen bereinigt), um Kompatibilität mit dem Dateisystem zu gewährleisten.  

---

## 3. Phase: KI-gestützte Analyse (LLM)
Nachdem die Mails sortiert sind, erfolgt die eigentliche Intelligenz-Arbeit durch `process_sorted_emails.py`. Das LLM (Large Language Model) analysiert jede E-Mail im Detail.

### Informationen, die dem LLM übergeben werden:
Um eine hochqualitative und kontextsensitive Antwort zu generieren, erhält das LLM eine Vielzahl an Informationen:  
- **Aktueller E-Mail-Inhalt:** Der Text der neuesten Nachricht in der Konversation.  
- **Konversationsverlauf:** Vorherige E-Mails im selben Ordner werden einbezogen, um den Kontext zu wahren.  
- **Personen-Steckbriefe:**  
    - **Studenten-Steckbrief:** Informationen über den Absender (Rolle, bisherige Themen). Details dazu finden Sie unter [Personen-Steckbriefe](profiles.md).  
    - **Eigener Steckbrief:** Ihre eigene Persona (Name, Rolle, Tonalität), definiert in der `config/user.yaml`.  
- **Skills (Fähigkeiten):** Für jede E-Mail-Klasse existiert eine Markdown-Datei (z.B. `SKILL_Bachelor_Thesis.md`), die spezifische Anweisungen und Fachwissen für dieses Thema enthält.  
- **RAG-Kontext (Retrieval Augmented Generation):** Das System durchsucht eine Vektordatenbank nach ähnlichen Fällen oder Dokumenten, die in [Memory-Pfaden](email-classification.md#memory-index) konfiguriert sind.  
- **Ähnlichkeits-Suche:** Das System sucht nach den 3 neuesten, thematisch ähnlichsten E-Mails desselben Studenten aus dem Archiv, um konsistente Antworten zu gewährleisten.  

---

## 4. Phase: Aktionen und Automatisierung
Basierend auf der Analyse schlägt das System eine von sechs Aktionen vor. In der [Gradio-Oberfläche](#5-phase-uberprufung-gradio-gui) können Sie diese Auswahl bestätigen oder ändern.

### Liste der Aktionen

| Aktion | Beschreibung | Technische Konsequenz |
| :--- | :--- | :--- |
| **1) Antwort schreiben** | Erstellt eine Standard-Antwort basierend auf dem Thema. | Generiert einen Textentwurf in Outlook. |
| **2) Antwort mit Terminvorschlag** | Sucht freie Slots in der `free_slots.yaml`. | Fügt konkrete Zeitvorschläge in den Antwortentwurf ein. |
| **3) Termin direkt buchen** | Erkennt eine Terminbestätigung des Studenten. | Ruft `manage_calendar_appointment` auf und erstellt einen echten Kalendereintrag in Outlook. |
| **4) Nur archivieren** | Keine Antwort nötig (z.B. reine Information). | Markiert die Mail als erledigt ohne weitere Aktion. |
| **5) Aufgabe "Anhang lesen"** | Speziell für finale Abgaben von Abschlussarbeiten. | Erstellt eine Outlook-Aufgabe/Termin für in 7 Tagen zur Korrektur und speichert Anhänge. |
| **6) Kolloquium-Termin** | Spezielle Buchung für Abschlussvorträge. | Erstellt einen 60-minütigen Kalendereintrag in Outlook. |

---

## 5. Phase: Überprüfung (Gradio GUI)
Der Prozess endet in einer interaktiven Web-Oberfläche. Hier behält der Mensch die volle Kontrolle (Human-in-the-loop).

**Funktionen der GUI:**  
- **Korrektur der Klassifizierung:** Falls eine Mail falsch einsortiert wurde, können Sie die Klasse via Dropdown ändern. Das System verschiebt die Dateien beim Speichern automatisch physisch auf der Festplatte.  
- **Aktions-Review:** Überprüfen Sie, welche Aktion das LLM vorschlägt und ändern Sie diese bei Bedarf.  
- **Anhänge extrahieren:** Über eine Checkbox können Sie entscheiden, ob Anhänge der Mail direkt im Studentenordner gespeichert werden sollen.  
- **Quick-Links:** Öffnen Sie den entsprechenden Windows-Ordner oder die E-Mail-Datei mit einem Klick direkt aus dem Browser.  
- **Zusammenfassungen:** Jede Mail wird kurz zusammengefasst, um das schnelle Scannen der Inbox zu ermöglichen.  

---

## Weiterführende Links  
- [Datenbank-Prozesse](database-processes.md): Erfahren Sie mehr über die Verwaltung der `profiles_tracking.db` und des Wissensgraphen.  
- [E-Mail Klassifizierung](email-classification.md): Details zu den Machine-Learning Modellen und Memory-Indizes.  
- [Konfiguration](../configuration.md): So passen Sie Pfade und LLM-Einstellungen an.  
