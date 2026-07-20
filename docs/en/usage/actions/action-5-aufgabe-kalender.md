# Action 4: Create Task in Calendar (Final Submission)

This action serves as the central control for the final submission of academic theses (Bachelor's and Master's theses). When the system detects a final submission email, this action coordinates a series of automated steps to assist with the evaluation process.

## How it Works and Details

Once executed, the system automatically performs the following steps:

1.  **Save Attachments:** All email attachments (such as the final thesis PDF) are automatically saved via `save_email_attachments` directly in the student's main folder (`Semester / Lastname /`). Existing files are not overwritten; if necessary, the suffix `_final` is added.  
2.  **Colloquium Configuration (`config.json`):** A `config.json` file is automatically created or updated in the student's main folder via `create_colloquium_config`. This file contains the exact filename of the PDF document from the attachment and serves as the configuration interface for the [colloquium-protocol-creator](https://dgaida.github.io/colloquium-protocol-creator/).  
3.  **Calendar Reminder in 7 Days:** A calendar entry (reminder) is created in your Outlook calendar via the `manage_calendar_appointment` tool for **exactly 7 days after the email is received, at 08:00 AM**. This reminds you in a timely manner to read and evaluate the submitted thesis.  
4.  **Draft Receipt Confirmation:** An email draft is automatically created in Outlook to confirm the official receipt of the thesis to the student.  

---

## Process Flow (Mermaid Diagram)

```mermaid
graph TD
    A[Email classified as 'Final Submission'] --> B[Save email attachments in student's main folder]
    B --> C[Create or update config.json for the colloquium]
    C --> D[Create calendar reminder for 7 days later at 08:00 AM]
    D --> E[Create Outlook draft for receipt confirmation]
    E --> F[Process completed]
```

---

## Integration with the Colloquium Protocol Creator

The generated `config.json` already contains the name of the PDF thesis. As soon as a colloquium date is agreed upon and confirmed with the student, the system automatically enters the date and time into this configuration file.

This allows for a seamless transition to protocol creation and evaluation of the colloquium.

## Configuration File Example

The created file has the following format:

```json
{
  "task": "colloquium",
  "description": "Colloquium on Campus Gummersbach with automatic Gemini evaluation",
  "pdf": {
    "filename": "Bachelor_Thesis_Mustermann.pdf"
  },
  "colloquium": {
    "date": "DD.MM.YYYY",
    "time": "hh:mm",
    "location_type": "campus",
    "room": "3.228"
  },
  ...
}
```