# Email Management Workflow

This workflow describes the process from receiving an email to creating a response draft in Outlook.

## 1. Outlook Export
The process begins in Outlook. Use the provided VBA macros to export relevant data:
- **Student Emails:** Exports emails from student domains as `.msg` files.
- **Free Slots:** Exports free time slots from your calendar to a YAML file (`free_slots.yaml`).

## 2. Classification and Sorting
Run the sorting script:
```bash
python -m mcp_university.classifier.sort_emails --source ./inbox --target ./sorted_mails
```
The system uses the `EmailClassifier` to categorize emails by topic (e.g., Bachelor Thesis, Project) and moves them into corresponding subfolders.

## 3. Analysis and Response Generation
After sorting, `process_sorted_emails.py` is executed. The script performs the following steps for each email:

1.  **Context Analysis:** The system analyzes other emails in the target folder (the previous history) to understand the context of the current request.
2.  **Appointment Check:** Checks if the student is requesting an appointment. If so, the `free_slots.yaml` is used to make a suggestion or book the appointment directly.
3.  **Necessity Check:** An LLM decides whether the email requires a response at all (or if it is just informational, for example).
4.  **Drafting:** If a response is needed, the agent generates a reply text considering the skill guidelines and the persona (Daniel Gaida).
5.  **Outlook Integration:** A draft is automatically created in the Outlook folder "Work in Progress". The original email is attached.

## 4. Verification (Gradio GUI)
At the end of the process, a Gradio web interface starts automatically. Here you can:
- Review the classifications made.
- Manually move emails to other categories if necessary.
- See the status of the processed emails.

## 5. Final Report
The script creates a file `processed_emails.md` containing a tabular overview of all processed emails and their status (e.g., "Draft created", "Appointment booked", "No reply needed").
