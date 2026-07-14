# Outlook VBA Macros and Helper Scripts

This project contains a sophisticated collection of Outlook VBA macros and Python helper scripts to automate the export of emails, calendar data, and student profiles. These macros form the essential bridge between your Outlook mailbox and the local, agentic AI system (MCP University Memory System).

---

## Overview and Detailed Logic of the Macros

### 1. Master Export (RunAllExports)  
*   **File:** `ExportStudentMails.bas`  
*   **Purpose:** This is the central macro for daily use. It automates the execution of the two most important daily exports in sequence:  
    1.  Determining free calendar consultation times (calls `ExportFreeSlots`).  
    2.  Exporting all new student emails (calls `ExportStudentEmails`).  
    *   *Interaction:* Upon start, the macro interactively asks how many days backward (default: 7) to search for new student emails.  
*   **Downstream Usage of Exports:**  
    *   The free time slots are saved in `D:\TH_Koelncademic-memory-mcp\dataree_slots.md` and are used by the LLM for draft reply suggestions (Action 2).  
    *   The emails are saved in the Inbox folder and are directly available to the Gradio GUI for classification, summarization, and processing.  

---

### 2. Email Export (ExportStudentEmails)  
*   **File:** `ExportStudentMails.bas` / `ExportStudentMails_Outlook2007.bas`  
*   **Purpose:** Specifically searches for emails from student domains (e.g., `@smail.th-koeln.de` or `@smail.fh-koeln.de`) in your inbox and the "Sent Items" folder.  
    *   *Special Feature:* To ensure a clean inbox and avoid duplicates, the email is automatically deleted in Outlook after a successful export to the hard drive.  
*   **Storage Locations:**  
    *   Inbox emails: `D:\TH_Koeln\StudentMails\Inbox\`  
    *   Sent emails: `D:\TH_Koeln\StudentMails\SentItems\`  
    *   *Filename format:* `YYYYMMDD_HHMMSS - Subject.msg`  
*   **Downstream Usage of Exports:** These are the raw data for the email processing workflow. The Gradio GUI (`scripts/process_sorted_emails.py`) reads all MSG files from these folders, classifies them into topics using Machine Learning (Transformer), determines the student's last name (Greedy Matching), and archives them in a structured way in the target path.  

---

### 3. Calendar Export / Free Time Slots (ExportFreeSlots)  
*   **File:** `FreeSlotExport.bas`  
*   **Purpose:** Analyzes your Outlook calendars ("Calendar" and "Calendar (Only this computer)") for the next 14 days for free consultation hours.  
    *   *Consultation Logic:* Searches for free 30-minute time slots on weekdays between 1:30 PM and 4:00 PM.  
    *   *Exclusions:* Weekends, public holidays in NRW, and explicitly configured blocked weekdays (default: Wednesday, Friday) are automatically skipped.  
*   **Storage Location:** `D:\TH_Koelncademic-memory-mcp\dataree_slots.md`  
*   **Downstream Usage of Exports:** The generated Markdown file serves as a direct data basis for the email controller. When you select **Action 2) Write reply with appointment suggestion** in the GUI, the system reads this file. The LLM extracts the free slots and integrates them in a formatted and personalized way into your draft reply in Outlook.  

---

### 4. Appointment & Consultation Export (AppointmentExport)  
*   **File:** `AppointmentExport.bas`  
*   **Purpose:** Exports all existing calendar entries of the next 4 weeks (duration, location, subject, participants, etc.) from your Outlook calendars.  
*   **Storage Location:** `D:\TH_Koelncademic-memory-mcp\datappointments.md`  
*   **Downstream Usage of Exports:** This is the primary data source for the appointment GUI (**Appointment Manager**, started via `python scripts/appointment_gui.py`). The Appointment Manager reads this Markdown table and automatically links each calendar entry with the local university database. It immediately shows you the matching student folder, their AI conversation summary (`.emails_summary.md`), the student's profile (Steckbrief), and allows quick access to their submitted files, so you are perfectly prepared for meetings.  

---

### 5. Collect Students (CollectStudentEmails)  
*   **File:** `CollectStudentEmails.bas`  
*   **Purpose:** Scans your inbox for all senders with a student domain, extracts their display names and email addresses, and organizes them.  
*   **Storage Location:** `D:\TH_Koelncademic-memory-mcp\students.yaml`  
*   **Downstream Usage of Exports:** Bootstrapping and maintaining the central student contact database. If the file already exists, only new students are added (existing entries are protected). The `students.yaml` is then transferred to the local SQLite metadata database via the CLI command `mcp-uni db sync-students` so that the system can reliably resolve names and aliases.  

---

### 6. Keyword-Based Email Sorter (SortInboxByConfig)  
*   **File:** `EmailSorter.bas`  
*   **Purpose:** A robust VBA sorter executed directly in Outlook. It sorts emails in the inbox and in Sent Items based on the keywords defined in `students.yaml` (e.g., "Bachelor Thesis", "Practical Project") to the respective students and saves them as MSG files directly in the corresponding local folders on your hard drive.  
*   **Storage Location:** Saves files directly in the individual paths configured in `students.yaml` under `folders` (e.g., `C:\Ablage\Mustermann\Bachelorthesis\`).  
*   **Downstream Usage of Exports:** Serves users who prefer to physically pre-sort their emails directly from Outlook without using the Gradio workflow. The sorted emails are captured and integrated into the knowledge graph during subsequent indexing runs by the crawler (`mcp-uni index`).  

---

### 7. Address Enrichment (EnrichStudentEmailsFromBody)  
*   **File:** `EnrichStudentEmailsFromBody.bas`  
*   **Purpose:** Searches the subject and the entire body of all Outlook emails for first and last names of already known students (from `students.yaml`).  
*   **Storage Location:** Updates the file `D:\TH_Koelncademic-memory-mcp\students.yaml`.  
*   **Downstream Usage of Exports:** If the macro finds matches, it automatically enters the corresponding sender or recipient email address as an alternative address in `students.yaml`. This solves the problem of students often writing from private addresses (e.g., Gmail, GMX). The system enriches the profile so that subsequent email assignments and searches (in the index and the GUI) automatically map the private email address to the correct student.  

---

### 8. Long-Term Archiving (ArchiveOldStudentMails)  
*   **File:** `ArchiveOldStudentMails.bas` / `ArchiveOldStudentMails_Outlook2007.bas`  
*   **Purpose:** For long-term clean-up and maintenance of the Outlook mailbox. The macro searches for student emails older than one year (`ARCHIVE_AGE_YEARS = 1`).  
*   **Storage Location:** Exports emails in a structured way to the hard drive under:  
    `D:\TH_Koeln\StudentMails\<Email-Address>\Inbox\` (or `SentItems\`)  
    *   *Outlook Action:* After the export, the emails are moved to the Trash in Outlook to keep the mailbox slim and performant.  
*   **Downstream Usage of Exports:** The archived MSG files remain on the hard drive and continue to be captured and indexed by the crawler (`mcp-uni index`). They are fully available via vector search (`mcp-uni search` or RAG) for historical searches and similarity comparisons (similarity display in the GUI).  

---

### 9. Subject-Based Export (ExportMailsBySubjectAndAge)  
*   **File:** `ExportMailsBySubjectAndAge.bas`  
*   **Purpose:** A specialized export macro that targetedly searches for old emails (> 1 year) containing a specific keyword in the subject (e.g., "compensation for disadvantages", "PO change", "hardship case").  
*   **Storage Location:** Saves emails as `.msg` files in the dedicated directory:  
    `D:\TH_Koeln\StudentMails\SubjectExport\`  
    *   *Outlook Action:* Deletes emails from Outlook after successful export.  
*   **Downstream Usage of Exports:** Used for targeted collection of historical case studies. The exported emails can be used as training data for the machine learning classifier or indexed as a knowledge source for RAG module folders to provide the LLM with sound knowledge on special-case decisions (e.g., approved hardship cases).  

---

## Python Helper Scripts in Macro Context

### Folder Enrichment (`enrich_yaml_from_config.py`)  
*   **File:** `outlook_macro/enrich_yaml_from_config.py`  
*   **Purpose:** If you already have an existing folder structure for students (e.g., from the EmailSorter format `email_config.md`), this script reads this structure and automatically enters the folder paths and matching keywords for each known student into `students.yaml`.  
*   **What happens to the data:** The `students.yaml` is enriched with the physical folder paths of the students. This allows the system during email archiving (GUI) to sort the emails directly into the real folders of the students on the hard drive (e.g., `Semester/Mustermann/Bachelorthesis`).  

---

## Installing the Macros in Outlook

1.  Open Microsoft Outlook.  
2.  Press `ALT + F11` to open the integrated VBA editor (Microsoft Visual Basic for Applications).  
3.  In the menu, click `Insert -> Module` to create a new empty module.  
4.  Copy the content of the desired `.bas` files from the `outlook_macro/` folder of this project into the new module window.  
5.  **Important:** Adjust the path constants (such as `ACCOUNT_NAME`, `YAML_FILE_PATH`, or `OUTPUT_PATH`) at the beginning of the modules to match your local folder structure!  
6.  Save the VBA project (`CTRL + S`).  
7.  You can now select and start the macros at any time directly in Outlook via the keyboard shortcut `ALT + F8` (macro selection window).  
