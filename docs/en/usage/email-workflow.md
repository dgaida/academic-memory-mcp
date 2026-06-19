# Email Management Workflow

This workflow describes the complete process from capturing an email in Microsoft Outlook to automated analysis, classification, and the creation of reply drafts or calendar entries. The system is designed to streamline communication with students and automate administrative tasks (such as appointment bookings or saving final theses).

---

## Phase 1: Data Export and Preparation
The process begins directly in Microsoft Outlook. Since the system works locally on exported data, the relevant information must first be provided.

### Export from Outlook
Use the VBA macros provided in the project to export data into the `inbox` folder:  
- **Emails:** Exports emails (mostly from students) as `.msg` files. The system automatically detects the sender, date, and subject.  
- **Calendar Data:** Exports free time slots from your Outlook calendar into a file named `free_slots.yaml`. This serves as the basis for automated appointment suggestions.  

---

## Phase 2: Classification and Sorting
Before a content analysis takes place, the emails are sorted by topic.

### Automatic Sorting
Run the sorting script:
```bash
python -m mcp_university.classifier.sort_emails --source ./inbox --target ./sorted_mails
```

**What happens here?**  
1. **Topic Recognition:** The [Email Classification](email-classification.md) system uses a machine learning model (transformer-based) to assign the content of the email to a category (e.g., *Bachelor Thesis*, *Project*, *PO-Change*).  
2. **File System Structure:** The emails are moved into a three-level hierarchy: `Semester (e.g., 2023_24_WS) / Lastname / (Inbox or SentItems)`.
3. **Lastname Extraction:** The lastname is automatically extracted from the email address or display name.
    - *Example 1:* `max.mustermann@th-koeln.de` -> Folder: `Mustermann`
    - *Example 2:* `mustermann@stud.th-koeln.de` -> Folder: `Mustermann`
    - *Example 3:* `Mustermann-Schmidt, Erika <erika.mustermann@...>` -> Folder: `Mustermann_Schmidt`
4. **Normalization:** Names are normalized (umlauts replaced, special characters cleaned) to ensure compatibility with the file system.

---

## Phase 3: AI-Powered Analysis (LLM)
After the emails are sorted, the actual intelligence work is performed by `process_sorted_emails.py`. The LLM (Large Language Model) analyzes each email in detail.

### Information Passed to the LLM:
To generate a high-quality and context-sensitive response, the LLM receives a variety of information:  
- **Current Email Content:** The text of the latest message in the conversation.  
- **Conversation History:** Previous emails in the same folder are included to maintain context.  
- **Person Profiles:**  
    - **Student Profile:** Information about the sender (role, previous topics). Details can be found under [Person Profiles](profiles.md).  
    - **User Profile:** Your own persona (name, role, tone), defined in `config/user.yaml`.  
- **Skills:** For each email class, there is a Markdown file (e.g., `SKILL_Bachelor_Thesis.md`) containing specific instructions and expertise for that topic.  
- **Summary:** The system creates a concise summary of the previous conversation history in the student folder (`.emails_summary.md`). This serves to provide the user with a quick overview in the [Gradio GUI](#gradio-gui).
    - An example of the resulting structure can be found under [Example Email Structures](indexing-details.md#example-email-structures).
    - If an email is reclassified in the GUI, the `.emails_summary.md` is automatically moved to the new target folder.
- **RAG Context (Retrieval Augmented Generation):** The system searches a vector database for thematically matching information (e.g., examination regulations) based on the content of the current mail. Details on this multi-stage process can be found under [RAG Process](rag-process.md).
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
| **6) Colloquium Appointment** | Special booking for final presentations. | Creates a 60-minute calendar entry in Outlook. |

---

## Phase 5: Verification (Gradio GUI) {#gradio-gui}
The process ends in an interactive web interface. Here, the human remains in full control (Human-in-the-loop).

**GUI Functions:**  
- **Correction of Classification:** If an email was incorrectly sorted, you can change the class via a dropdown. The system automatically moves the files physically on the disk when saving.  
- **Action Review:** Check which action the LLM suggests and change it if necessary.  
- **Extract Attachments:** Via a checkbox, you can decide whether attachments of the email should be saved directly in the student folder.  
- **Quick Links:** Open the corresponding Windows folder or the email file with one click directly from the browser.  
- **Summaries:** Each email is briefly summarized to allow for quick scanning of the inbox.  

---

## Further Links  
- [Database Processes](database-processes.md): Learn more about managing `profiles_tracking.db` and the Knowledge Graph.  
- [Email Classification](email-classification.md): Details on the machine learning models and memory indices.  
- [Configuration](../configuration.md): How to customize paths and LLM settings.  
