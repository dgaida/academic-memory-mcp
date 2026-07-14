# Action 3: Book Appointment

This action is executed when an email contains an appointment confirmation from a student. The system then enters the appointment directly into your Microsoft Outlook calendar.

## How it Works and Details

The system performs the following steps during this action:

1.  **Extract Date and Time:** The AI extracts the requested and confirmed date and time from the email.
2.  **Validity Check (Past):** It checks if the proposed appointment lies in the past.
    *   **If in the past:** No calendar entry is created. The email is archived directly (Status: `Archiviert (Termin in Vergangenheit)`).
3.  **Create Calendar Entry:** If the appointment is in the future, the system books the appointment in the user's Outlook calendar via the `manage_calendar_appointment` tool. The default duration is **30 minutes**, and the timezone is set to `Europe/Berlin`.
4.  **Archiving:** The email is filed in the corresponding student archive folder.

---

## Process Flow (Mermaid Diagram)

```mermaid
graph TD
    A[Email with appointment confirmation received] --> B[Extract date & time of the appointment]
    B --> C{Is appointment in the past?}
    C -- Yes --> D[No booking & archive email directly <br> Status: Archiviert (Termin in Vergangenheit)]
    C -- No --> E[Book appointment in Outlook calendar via manage_calendar_appointment]
    E --> F[Process completed]
```
