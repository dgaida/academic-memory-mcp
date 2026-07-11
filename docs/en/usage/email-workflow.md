# Email Management Workflow

This workflow describes the complete process from capturing an email in Microsoft Outlook to automated analysis, classification, and the creation of reply drafts or calendar entries. The system is designed to streamline communication with students and automate administrative tasks (such as appointment bookings or saving final theses).

---

## Phase 1: Data Export and Preparation
The process begins directly in Microsoft Outlook. Since the system works locally on exported data, the relevant information must first be provided.

### Export from Outlook
Use the VBA macros provided in the project to export data into the `inbox` folder:

- **Emails:** Exports emails (mostly from students) as `.msg` files. The system automatically detects the sender, date, and subject.  
- **Calendar Data / Appointments:** Exports free time slots from your Outlook calendar into a file named `free_slots.yaml`. Additionally, existing calendar appointments are also exported, which are required for the calendar GUI to provide an overview and assist in scheduling.  

---

## Phase 2: Automatic Classification and Pre-sorting
Running sorting scripts manually via the command line is **no longer required**, as reading, classification, and sorting are now handled entirely through the Gradio GUI (see Phase 3). The system performs all topic recognition and name resolution in the background when you start the GUI or trigger the scanning process there.

---

## Phase 3: AI-Powered Analysis (LLM)
After the emails are sorted, the actual intelligence work is performed by `scripts/process_sorted_emails.py`. The LLM (Large Language Model) analyzes each email in detail.

### Information Passed to the LLM:
To generate a high-quality and context-sensitive response, the LLM receives a variety of information:

- **Current Email Content:** The text of the latest message in the conversation.  
- **Conversation History:** Previous emails in the same folder are included to maintain context.  
- **Person Profiles:**  
    - **Student Profile:** Information about the sender (role, previous topics). Details can be found under [Person Profiles](profiles.md).  
    - **User Profile:** Your own persona (name, role, tone), defined in `config/user.yaml`.  
- **Skills:** For each email class, there is a Markdown file (e.g., `SKILL_Bachelor_Thesis.md`) containing specific instructions and expertise for that topic.  
- **Summary:** The system creates a concise summary of the previous conversation history in the student folder (`.emails_summary.md`). This primarily serves as context for the LLM during reply generation. In the [Gradio GUI](#gradio-gui), however, a separate, short (2-sentence) summary of the current content is displayed for each email to provide a quick overview.  
    - An example of the resulting structure can be found under [Example Email Structures](indexing-details.md#example-email-structures).  
    - If an email is reclassified in the GUI, the `.emails_summary.md` is automatically moved to the new target folder.  
- **RAG Context (Retrieval Augmented Generation):** The system performs a deep AI analysis of emails in the background using a RAG process.  
    - **Semantic Search:** Based on the email content, the system searches a local vector database (Qdrant) for highly relevant documents such as examination regulations, module handbooks, or past email conversations.  
    - **Knowledge Injection:** These retrieved documents are injected as additional context into the prompt for the LLM. This enables the AI to draft highly accurate and context-sensitive replies tailored to the rules and regulations of TH Köln.  
    - **Enhanced Response Quality:** The RAG process minimizes hallucinations and ensures that specific deadlines or examination rules are mentioned correctly.  
    - **Technical Details Link:** For a detailed explanation of multi-stage filtering, vector search, and the technical workflow, see the technical documentation under [RAG Process](rag-process.md).  
- **Similarity Search:** The system searches for the 3 most recent, thematically similar emails from the same student in the archive to ensure consistent responses.  

---

## Phase 4: Actions and Automation
Based on the analysis, the system suggests one of six actions. In the [Gradio Interface](#gradio-gui), you can confirm or change this selection.

### List of Actions

| Action | Description | Technical Consequence |
| :--- | :--- | :--- |
| **1) Write Reply** | Creates a standard response based on the topic. | Generates a text draft in Outlook. |
| **2) Reply with Appointment Proposal** | Searches for free slots in `free_slots.yaml`. | Inserts concrete time suggestions into the reply draft. |
| **3) Book Appointment Directly** | Recognizes an appointment confirmation from the student. | Calls `manage_calendar_appointment` and creates an actual calendar entry in Outlook. |
| **4) Archive Only** | No reply needed (e.g., purely informational). | Marks the email as handled without further action. |
| **5) Task "Read Attachment"** | Specifically for final submissions of theses. | Creates an Outlook task/appointment for 7 days later for grading and saves attachments. |
| **6) Colloquium Appointment (with `config.json` Automation)** | Special booking for final presentations with `config.json` automation. | Creates a 60-minute calendar entry in Outlook, creates/updates `config.json` in the student folder, and saves PDF filenames and presentation date/time. |

---

## Phase 5: Interactive Management (Gradio GUI) {#gradio-gui}
The entire process is controlled directly via the Gradio GUI (`scripts/process_sorted_emails.py`). The GUI offers two specialized tabs for different workflows.

### Tab 1: Quick Sorting
This tab is optimized for bulk processing of emails where the automatic classification is already sufficient. You no longer need to run CLI scripts manually; all steps are executed at the click of a button in the GUI.

#### How Automatic Classification & Sorting Works:  
1. **Topic Recognition:** The [Email Classification](../packages/email-classifier/index.md) system uses an advanced machine learning model (transformer-based) to assign the content of the email to a category (e.g., *Bachelor Thesis*, *Project*, *PO-Change*).  
2. **File System Structure:** Once approved in the GUI, the emails are automatically moved into a three-level archive hierarchy: `Semester (e.g., 2023_24_WS) / Lastname / (Inbox or SentItems)`.  
3. **Lastname Extraction:** The lastname is automatically extracted from the email address or display name (using Greedy Name Matching / Dot-Separated Fallback).  
    - *Example 1:* `max.mustermann@th-koeln.de` -> Folder: `Mustermann`  
    - *Example 2:* `mustermann@stud.th-koeln.de` -> Folder: `Mustermann`  
    - *Example 3:* `Mustermann-Schmidt, Erika <erika.mustermann@...>` -> Folder: `Mustermann_Schmidt`  
4. **Normalization:** Names are normalized (umlauts replaced, special characters cleaned) to ensure compatibility with the file system.  

- **Scan & Classification:** Reads all emails from the source folder and assigns them a class using the model without physically moving them.  
- **List View:** Separate display of `Inbox` and `SentItems`.  
- **Remove:** Emails that require closer inspection can be moved to the second tab by selecting their index.  
- **Attachments:** For each email, you can already select here whether attachments should be saved during archiving.  
  - **Storage Location & Path of Attachments:** If the option is selected, attachments are automatically saved directly in the student's main directory (`Semester / Lastname /`) (which is the parent directory of the archived email folder).  
  - *Example:* If an email is archived as `Bachelor Thesis` for the student `Mustermann` in the semester `2023_24_WS` (email path: `2023_24_WS/Mustermann/Inbox/20231120_143000_Expose.msg`), the attachment (e.g., `Expose_Max_Mustermann.pdf`) will be saved in the following folder:  
    `2023_24_WS/Mustermann/Expose_Max_Mustermann.pdf`  
- **Archive:** All remaining emails in the lists are moved directly to their respective archive paths with one click.  

### Tab 2: Detail View & Processing
This is where emails go that were removed from Tab 1 or that require a deeper analysis.

- **AI Summary:** A concise 2-sentence summary is generated for each email.  
- **Context & Similarity:** Displays the most similar emails from the archive (Similarity Search).  
- **Action Selection:** Manual selection of the action (Reply, book appointment, etc.) and target folder.  
- **Attachments:** Option to selectively save email attachments.  

---

## Phase 6: Execution of Actions (Details)
As soon as you click "Save & Execute" in the GUI, the selected action is technically implemented. This is where the **Person Profiles** (Student & User Persona) and **Skills** (expertise Markdown files) are integrated.

### Detailed Logic of Actions:

#### Preparation: Conversation Summary
Before a reply is generated, the system creates a concise summary of the previous conversation history in the student folder (`.emails_summary.md`). This serves as crucial context for the LLM to stay informed about prior agreements.  
- An example of the resulting structure can be found under [Example Email Structures](indexing-details.md#example-email-structures).  
- If an email is reclassified in the GUI, the summary automatically adapts to the new folder structure.  

#### 1) Write Reply
The LLM generates a reply taking into account your own **Person Profile** (tone, role), the **Student Profile**, and the aforementioned **Conversation Summary**. Details can be found under [Person Profiles](profiles.md). A draft is automatically created in Outlook with the original email attached.

#### 2) Write Reply with Appointment Proposal
The system calls the `get_appointment_slots` tool, which reads `free_slots.yaml`. The retrieved free slots are formatted and integrated into the reply draft.

#### 3) Book Appointment Directly
Used when a student has confirmed an appointment. The system extracts the date and time and uses the `manage_calendar_appointment` tool to create a real entry in your Outlook calendar.

!!! info "Appointments in the Past"
    If an appointment lies in the past, it is automatically detected. In this case, no calendar entry is created and the email is archived directly (Status: `Archived (Appointment in Past)`).

#### 4) Archive Only
The email is saved in the student's archive folder. No further technical actions (such as a reply draft) are taken.

#### 5) Create Task in Calendar (Final Submission)
**This is the central action where the final submission of a thesis is automatically detected and processed.** When the email classifier or the user in the GUI classifies an email as a final submission, this action is selected. It combines several automated steps for final theses:

1. **Save Attachments:** All email attachments are automatically saved in the student's parent directory (`Semester / Lastname /`) via `save_email_attachments`.  
2. **Colloquium Configuration (`config.json`):** A `config.json` configuration file is automatically created in the student's main directory via `create_colloquium_config` (or updated with the filename of the PDF thesis from the attachment). This file is used for the *colloquium-protocol-creator*.  
3. **Calendar Reminder:** A calendar entry is created via `manage_calendar_appointment` exactly **7 days after the email is received (at 08:00 AM)** to remind you to read and grade the thesis.  
4. **Reply Draft:** A reply draft confirming receipt of the thesis is automatically generated.  

#### 6) Colloquium Appointment (with `config.json` Automation)
Similar to action 3, but the duration is fixed at **60 minutes** and a special subject is chosen. In addition, this action has been significantly enhanced to automate the entire colloquium process:

1. **Creation/Update of `config.json`:**  
   The system automatically creates a configuration file named `config.json` in the student's folder (or updates an existing one). This file contains all crucial parameters for the presentation and optional downstream processes (such as automated slide evaluation using Gemini or compiling PDFs).

2. **Automated Appointment Entry:**  
   The date (format: `DD.MM.YYYY`) and time (format: `HH:MM`) of the colloquium are automatically extracted from the email, booked in the Outlook calendar (duration: 60 minutes), and written directly into the student's `config.json`.

**Example of the generated/updated `config.json`:**
```json
{
  "task": "colloquium",
  "description": "Kolloquium auf dem Campus Gummersbach mit automatischer Gemini-Bewertung",
  "pdf": {
    "filename": "Bachelorarbeit.pdf"
  },
  "colloquium": {
    "date": "15.11.2026",
    "time": "14:00",
    "location_type": "campus",
    "room": "3.228"
  },
  "llm": {
    "api_choice": null,
    "model": null,
    "groq_free": true
  },
  "gemini_evaluation": {
    "enabled": false,
    "model": "gemini-2.0-flash-exp"
  },
  "output": {
    "folder": null,
    "compile_pdf": true,
    "fill_form_only": true
  }
}
```
This file is used downstream for automated evaluation of presentation slides or automatically filling out grading forms.

---

## Further Links  
- [Database Processes](database-processes.md): Learn more about managing `profiles_tracking.db` and the Knowledge Graph.  
- [Email Classification](../packages/email-classifier/index.md): Details on the machine learning models and memory indices.  
- [Configuration](../configuration.md): How to customize paths and LLM settings.  


!!! info "Automatic Archiving"
    The system automatically suggests the action **"4) Archive Only"** for specific emails:  
    - **Old Emails:** Emails older than the configured threshold (e.g., 6 months).  
    - **SentItems:** Emails in the `SentItems` folder never require a reply action.  
    - **Already Answered:** Emails where the system detects no need for further action.  

### Diagnosis and Logging
The system logs every step of email processing in detail in `process_emails.log`. If the GUI does not display any emails even though they are listed in `sorted_emails.md`, check the log file for warnings regarding missing model files or access issues.
