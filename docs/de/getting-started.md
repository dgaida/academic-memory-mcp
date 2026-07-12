# Erste Schritte & Anwendungsfälle (Use Cases)

Herzlich willkommen beim **MCP University Memory System**! Dieses System dient als Ihr intelligentes, lokales Gedächtnis und unterstützt Sie umfassend bei Ihren alltäglichen Aufgaben in der universitären Lehre und Verwaltung.

Die Getting Started Seite gibt Ihnen einen schnellen Überblick über die zentralen Anwendungsfälle (Use Cases), die das System abdeckt, und verlinkt auf die jeweiligen Detailanleitungen des Handbuchs.

---

## Übersicht der Anwendungsfälle (Use Cases)

Das System ist um sechs Hauptanwendungsfälle herum aufgebaut, die Ihren universitären Alltag erleichtern:

### 1. [E-Mail Schnellsuche](usage/email-search.md)
*   **Worum geht es?** Durchsuchen Sie tausende archivierte E-Mails blitzschnell mit einer dedizierten, grafischen Benutzeroberfläche (Gradio GUI).
*   **Key Features:** Autovervollständigung, Volltextsuche, direkter Absprung zu E-Mails in Outlook oder dem Datei-Explorer.
*   **Mehr erfahren:** [Anleitung zur E-Mail Suche](usage/email-search.md).

### 2. [Terminverwaltung](usage/appointment-management.md)
*   **Worum geht es?** Effiziente Vorbereitung auf Ihre wöchentlichen Termine und Sprechstunden.
*   **Key Features:** Das System bündelt alle relevanten Kontextinformationen (Dokumente, Abschlussarbeiten, E-Mail-Verläufe der Teilnehmer) übersichtlich auf einen Blick.
*   **Mehr erfahren:** [Anleitung zur Terminverwaltung](usage/appointment-management.md).

### 3. [Automatisiertes Beantworten von E-Mails (E-Mail Workflow)](usage/email-workflow.md)
*   **Worum geht es?** Beschleunigen Sie Ihre tägliche Korrespondenz. Das System klassifiziert eingehende E-Mails automatisch und schlägt passende Aktionen vor.
*   **Key Features:** Automatische Generierung von präzisen, kontextbezogenen Antwortentwürfen im korrekten Tonfall (Du/Sie), basierend auf dem E-Mail-Verlauf und dem Wissensgraphen.
*   **Mehr erfahren:** [Anleitung zum E-Mail Workflow](usage/email-workflow.md).

### 4. [Personaldatenbank & Personen-Steckbriefe](usage/profiles.md)
*   **Worum geht es?** Verwalten Sie alle Hochschulmitarbeiter, Kontakte und Zuständigkeiten sowie individuelle Steckbriefe Ihrer Studierenden.
*   **Key Features:** Automatische Bestimmung der bevorzugten Anrede (Du/Sie). Import von Modulverantwortlichkeiten und Prüfern über die offizielle MOCOGI-API und den Personen-Crawler der TH Köln.
*   **Mehr erfahren:** [Anleitung zu Steckbriefen & Personaldatenbank](usage/profiles.md).

### 5. [Finale Abgabe von Abschlussarbeiten](usage/final-submission.md)
*   **Worum geht es?** Begleiten Sie den Prozess der finalen Abgabe von Bachelor- und Masterthesen lückenlos und automatisiert.
*   **Key Features:** JIT-Archivierung von Abgabedokumenten, vollautomatische Terminplanung für Kolloquien inklusive Raumbuchung und automatischer Erinnerungsfunktion in Ihrem Kalender.
*   **Mehr erfahren:** [Anleitung zur Finalen Abgabe](usage/final-submission.md).

### 6. [Outlook Makros](usage/outlook-macros.md)
*   **Worum geht es?** Nahtlose Integration in Ihren gewohnten Windows-Arbeitsplatz.
*   **Key Features:** Exportieren Sie E-Mails, Termindaten und freie Zeitfenster direkt aus Outlook in das System, um sie der lokalen KI zur Verfügung zu stellen.
*   **Mehr erfahren:** [Anleitung zu Outlook Makros](usage/outlook-macros.md).

---

## Erste Schritte zur Einrichtung

Um das System in Betrieb zu nehmen, folgen Sie bitte unserer strukturierten Anleitung:

1. **[Installation](installation.md):** Erfahren Sie, wie Sie das Python-System, Conda oder systemweite Komponenten wie `qmd` installieren.
2. **[Einrichtung](setup.md):** Kopieren und konfigurieren Sie die Beispieldateien, um das System auf Ihre Umgebung anzupassen.
3. **[Konfiguration](configuration.md):** Erfahren Sie alles über die Konfigurationsoptionen für Ordner, ML-Klassifikationspfade und lokale LLMs (Ollama).
4. **[Fehlerbehandlung](troubleshooting.md):** Schnelle Hilfe bei bekannten Problemen oder Codierungsfehlern.
