# Email Management Workflow

This workflow describes the process from receiving an email to creating a reply draft in Outlook.

## 1. Export from Outlook
The process begins in Outlook. Use the provided VBA macros to export relevant data:  
- **Student Emails:** Exports emails from student domains as `.msg` files.  
- **Free Slots:** Exports free time slots from your calendar to a YAML file (`free_slots.yaml`).  

## 2. Classification and Sorting
Run the sorting script:
```bash
python -m mcp_university.classifier.sort_emails --source ./inbox --target ./sorted_mails
```
The system uses the `EmailClassifier` to categorize emails by topic (e.g., Bachelor Thesis, Project) and move them into appropriate subfolders.

## 3. Analysis and Response Generation
After sorting, `process_sorted_emails.py` is executed. The script performs the following steps for each email:

1.  **Context Analysis:** The system analyzes other emails in the target folder (previous history) to understand the context of the current request.  
2.  **Cutoff Date Policy (`--cutoff-date`):** The `--cutoff-date YYYY-MM-DD` parameter can be used to exclude older emails from LLM processing (reply generation, appointment booking). They will only be sorted.  
3.  **Appointment Check:** Checks if the student is asking for an appointment. If so, `free_slots.yaml` is used to make a suggestion or book the appointment directly.  
4.  **Check for Final Submission:** Automatically detects when a student finally submits their thesis (Bachelor/Master/Project). In this case:  
    - A **reminder appointment** is automatically created in the Outlook calendar for 7 days later (08:00 AM).  
    - **Attachments are extracted** and saved securely in the corresponding student folder.  
    - A confirmation email is prepared as a draft.  
5.  **Person Context:** Includes existing person profiles (created by the indexer or `create_person_profiles.py`) in the reply generation.  
6.  **Necessity Check:** An LLM decides whether the email requires a response at all (or if it is just information, for example).  
7.  **Write Draft:** If a response is necessary, the agent generates a reply text considering the skill specifications and the persona (Daniel Gaida).  
8.  **Outlook Integration:** A draft is automatically created in the Outlook folder "Work in Progress". The original email is attached.  

## 4. Verification (Gradio GUI)
At the end of the process, a Gradio web interface starts automatically. Here you can:  
- Verify the classifications made.  
- Manually move emails to other categories if necessary. The system automatically moves the corresponding `.emails_summary.md` as well.  
- View the status of processed emails.  

## 5. Final Report
The script creates a `processed_emails.md` file containing a tabular overview of all processed emails and their status (e.g., "Draft created", "Appointment booked", "No response needed").
