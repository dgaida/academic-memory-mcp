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

Before a reply is generated, the system creates a concise summary of the previous conversation history in the student folder (`.emails_summary.md`). This serves as crucial context for the LLM to stay informed about prior agreements. Details on how each action works and is executed can be found directly in their respective descriptions:

*   **[Action 1: Write Reply](actions/action-1-antwort-schreiben.md)**  
*   **[Action 2: Reply with Appointment Suggestion](actions/action-2-antwort-terminvorschlag.md)**  
*   **[Action 3: Book Appointment](actions/action-3-termin-buchen.md)**  
*   **[Action 4: Archive Only](actions/action-4-nur-archivieren.md)**  
*   **[Action 5: Create Task in Calendar (Final Submission)](actions/action-5-aufgabe-kalender.md)**  
*   **[Action 6: Colloquium Appointment](actions/action-6-kolloquium-termin.md)**  

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
