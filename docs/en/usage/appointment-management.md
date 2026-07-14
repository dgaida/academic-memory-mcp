# Appointment Management (Appointment GUI)

The Appointment Manager is used to prepare for appointments with students. It links the appointments from your calendar with the information available in the system about the respective student.

## Starting the GUI

Run the following script:

```bash
python scripts/appointment_gui.py
```

## Features

*   **Weekly Overview:** Displays all appointments for the current week, read from `data/appointments.md`.  
*   **Student Context:** Selecting an appointment automatically searches for the matching student folder.  
*   **Summaries:** Displays the AI-generated conversation summary (`.emails_summary.md`) of the student.  
*   **Student Profiles (Steckbriefe):** Displays the student's current profile (interests, previous topics, etc.).  
*   **File Explorer:** Allows direct access to all files in the student's folder (e.g., exposés, drafts).  

## Data Source

The appointments are usually exported via the Outlook VBA macro `AppointmentExport.bas`. The system reads this exported data and enriches it with knowledge from the local knowledge base.
