# Final Submission of Theses

The system automatically detects the final submission of Bachelor, Master, and project theses. When such an email is received, several automated steps are initiated to support the correction and examination process.

## Automated Steps

1.  **Calendar Reminder:** A reminder is automatically created in your Outlook calendar exactly 7 days after the email is received (at 08:00 AM) to remind you to read the thesis.  
2.  **Save Attachments:** All email attachments are automatically saved in the corresponding student folder. Existing files are not overwritten; if necessary, the suffix `_final` is added.  
3.  **Colloquium Configuration:** A `config.json` file is created in the student's main folder. This file serves as a configuration for the [colloquium-protocol-creator](https://dgaida.github.io/colloquium-protocol-creator/).  

## Integration with the Colloquium Protocol Creator

The generated `config.json` already contains the name of the PDF thesis. As soon as a colloquium date is agreed upon and confirmed with the student, the system automatically enters the date and time into this configuration file.

This allows for a seamless transition to protocol creation and evaluation of the colloquium.

## Configuration File Example

The created file has the following format:

\`\`\`json
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
\`\`\`
