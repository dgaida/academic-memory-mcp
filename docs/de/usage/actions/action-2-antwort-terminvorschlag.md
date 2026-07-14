# Aktion 2: Antwort mit Terminvorschlag

Diese Aktion wird verwendet, wenn auf eine Anfrage geantwortet werden soll und gleichzeitig konkrete Terminvorschläge (z. B. für Sprechstunden oder Besprechungen) aus dem Kalender unterbreitet werden sollen.

## Funktionsweise und Details

Das System führt bei dieser Aktion folgende Schritte aus:

1.  **Auslesen der freien Zeiten:** Das System nutzt das Tool `get_appointment_slots`, welches die Datei `free_slots.md` einliest. Diese Datei wurde zuvor über Outlook-VBA-Makros mit Ihren aktuellen freien Zeiten gefüllt.
2.  **Formatierung und Filterung:** Die freien Zeitfenster werden ausgelesen und übersichtlich formatiert.
3.  **KI-Generierung:** Das lokale LLM entwirft das Antwortschreiben, bindet die gefundenen freien Slots ansprechend in die E-Mail ein und bittet den Empfänger um Bestätigung eines der Termine.
4.  **Anrede und Tonfall:** Auch hier werden die Steckbriefe und die ermittelte Anredeform (Du/Sie) berücksichtigt.
5.  **Entwurfserstellung:** Es wird ein Antwortentwurf in Outlook mit den integrierten Terminvorschlägen und der Original-Mail im Anhang angelegt.

---

## Prozessablauf (Mermaid Diagramm)

```mermaid
graph TD
    A[E-Mail empfangen & klassifiziert] --> B[Lese freie Slots aus free_slots.md via get_appointment_slots]
    B --> C[LLM generiert Antwortentwurf mit vorgeschlagenen Zeiten]
    C --> D[Anredeform Du/Sie & Steckbrief-Tonalität anwenden]
    D --> E[Outlook-Entwurf erstellen]
    E --> F[Vorgang abgeschlossen]
```
