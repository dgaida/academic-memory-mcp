# Terminverwaltung (Appointment GUI)

Der Appointment Manager dient zur Vorbereitung von Terminen mit Studierenden. Er verknüpft die Termine aus Ihrem Kalender mit den im System vorhandenen Informationen über den jeweiligen Studierenden.

## Starten der GUI

Führen Sie das folgende Skript aus:

```bash
python scripts/appointment_gui.py
```

## Funktionen

*   **Wochenübersicht:** Zeigt alle Termine der aktuellen Woche an, die aus `data/appointments.md` eingelesen werden.  
*   **Studenten-Kontext:** Bei Auswahl eines Termins sucht das System automatisch nach dem passenden Studenten-Ordner.  
*   **Zusammenfassungen:** Zeigt die KI-generierte Konversationszusammenfassung (`.emails_summary.md`) des Studenten an.  
*   **Steckbriefe:** Zeigt den aktuellen Steckbrief des Studierenden (Interessen, bisherige Themen, etc.) an.  
*   **Datei-Explorer:** Ermöglicht den direkten Zugriff auf alle Dateien im Ordner des Studierenden (z.B. Exposés, Entwürfe).  

## Datenquelle

Die Termine werden üblicherweise über das Outlook-VBA-Makro `AppointmentExport.bas` exportiert. Das System liest diese exportierten Daten ein und reichert sie mit dem Wissen aus der lokalen Wissensbasis an.
