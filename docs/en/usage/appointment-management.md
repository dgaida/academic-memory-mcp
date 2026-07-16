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
    *   **How does it find the folder?**  
        The system first extracts the participant's name (or lastname) and email address from the appointment's participant information. Then, it searches for the folder based on the email class and the extracted lastname:  
        1. **Name Extraction:** The lastname is filtered from the participant string using regular expressions and text patterns (e.g., "Mustermann" from `max.mustermann@th-koeln.de` or "Mustermann" from `Mustermann Max <... >`).  
        2. **Class Path Mapping:** Each email class (e.g., *Bachelor Thesis*, *Project*) has a defined base path in the `classifier_paths.yaml` configuration. The system determines the class of the appointment (see below) and first checks the corresponding base path for a folder containing the student's lastname.  
        3. **Fallback Search:** If no folder is found in the specific class path (e.g., because the class of the appointment does not match or the folder is located elsewhere), the system searches all other configured base paths for a matching folder containing that lastname.  
    *   **How does the tool know the theme of the appointment / determine the email class?**  
        The determination is based on the subject (title) of the calendar appointment:  
        *   The system reads the configured email classes and their paths from `classifier_paths.yaml`.  
        *   It matches the subject of the appointment with the class names (case-insensitive). If the name of a class (e.g., "Bachelor Thesis" or "Project") appears in the subject, that email class is assigned to the appointment.  
        *   If no match is found in the subject, the subject is passed to the EmailClassifier model, which determines the class. If no emails from the appointment participant are found in the predicted class folder, the system falls back to the default class `"Other"`.  
*   **Summaries:** Displays the AI-generated conversation summary (`.emails_summary.md`) of the found main student directory.  
    *   **Does the GUI create the summary if it doesn't exist yet?**  
        Yes! If no summary exists yet for the found student folder or if the existing one is outdated (i.e., if the file date of `.emails_summary.md` is older than the newest email file `.msg` / `.eml` in the folder), the GUI automatically generates or updates the summary in the background. To do this, it reads the entire email history of the student and uses the local LLM to generate an up-to-date, structured summary, which is then saved as `.emails_summary.md` in the student's folder.  
*   **Student Profiles (Steckbriefe):** Displays the student's current profile (interests, previous topics, preferred salutation, etc.).  
    *   **Is this also created by the GUI if it doesn't exist yet?**  
        Yes! When an appointment is selected and the participant's email address is known, the system calls the `PersonProfiler`. This checks whether a profile already exists under `D:\Steckbriefe\<email>.md` (or alternatively in the local folder `Steckbriefe/`). If no profile exists yet, the profiler searches for all emails from this person (up to 100 of the newest emails from all archive paths), incorporates information from the Knowledge Graph (e.g., roles, affiliations), determines the preferred salutation ("Du" or "Sie") through LLM analysis of recent direct emails, and automatically generates a new, detailed profile in Markdown. If a profile already exists, it is also automatically updated when new emails are found.  
*   **File Explorer:** Allows direct access to all files in the student's folder (e.g., exposés, drafts).  

## Data Source

The appointments are usually exported via the Outlook VBA macro `AppointmentExport.bas`. The system reads this exported data and enriches it with knowledge from the local knowledge base.
