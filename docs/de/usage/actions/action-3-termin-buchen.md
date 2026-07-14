# Aktion 3: Termin direkt buchen

Diese Aktion wird ausgeführt, wenn eine E-Mail eine Terminbestätigung eines Studierenden enthält. Das System trägt den Termin daraufhin direkt in Ihren Microsoft Outlook-Kalender ein.

## Funktionsweise und Details

Das System führt bei dieser Aktion folgende Schritte aus:

1.  **Datum- und Uhrzeitextraktion:** Die KI extrahiert das gewünschte und bestätigte Datum sowie die Uhrzeit aus der E-Mail.
2.  **Prüfung auf Gültigkeit (Vergangenheit):** Es wird überprüft, ob der vorgeschlagene Termin in der Vergangenheit liegt.
    *   **Falls in der Vergangenheit:** Es wird kein Kalendereintrag erstellt. Die E-Mail wird direkt archiviert (Status: `Archiviert (Termin in Vergangenheit)`).
3.  **Kalendereintrag erstellen:** Liegt der Termin in der Zukunft, bucht das System den Termin über das Tool `manage_calendar_appointment` direkt im Outlook-Kalender des Benutzers. Die Standarddauer beträgt **30 Minuten**, und die Zeitzone ist auf `Europe/Berlin` eingestellt.
4.  **Archivierung:** Die E-Mail wird im entsprechenden studentischen Archiv-Ordner abgelegt.

---

## Prozessablauf (Mermaid Diagramm)

```mermaid
graph TD
    A[E-Mail mit Terminbestätigung empfangen] --> B[Extrahiere Datum & Uhrzeit des Termins]
    B --> C{Liegt Termin in der Vergangenheit?}
    C -- Ja --> D[Keine Buchung & Mail direkt archivieren <br> Status: Archiviert (Termin in Vergangenheit)]
    C -- Nein --> E[Buche Termin im Outlook-Kalender via manage_calendar_appointment]
    E --> F[Vorgang abgeschlossen]
```
