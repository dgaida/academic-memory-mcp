# Setting Up the Software

This page describes the necessary steps for the initial setup of the MCP University System after installation.

For actual installation instructions and system prerequisites, please refer to the **[Installation](installation.md)** page.

## Initial Setup (Setup Workflow)

To get the system up and running, you need to prepare and adapt the configuration files. There are three files that you **must** configure. Configuration files that do not absolutely need to be modified (such as `models.yaml` or `ontology.yaml`) can be left as they are.

### 1. Prepare Configuration Files

First, copy the `.example` templates in the `config/` directory:

```bash
cp config/user.yaml.example config/user.yaml
cp config/ontology.yaml.example config/ontology.yaml
cp config/classifier_paths.yaml.example config/classifier_paths.yaml
```

### 2. Mandatory Customizations

You must explicitly customize the following configuration files for the system to be functional:

1. **`config/user.yaml` (Personal User Data):**
   Open this file and adjust the following entries:
   - **`name`**: Your full name (used, among other things, for automatic generation of email signatures).
   - **`email`**: Your **primary university email address**. This is essential as the Outlook macro and backend scripts use this address to locate your Outlook mailbox on the system and export emails from it.
   - **`emails`**: A list of all your email addresses and aliases (e.g., if you have multiple university addresses). The system uses this list to identify your own sent emails.

   *Explanations & Options:* See **[user.yaml in Configuration](configuration.md#1-useryaml)**.

2. **`config/folders.yaml` (Directories to Monitor):**
   This file does not exist as a template by default, but must be created by you if you want to use the indexing function (`mcp-uni memory update` or `python scripts/index_memory.py`). Create the file `config/folders.yaml` and enter the desired paths:
   ```yaml
   folders:
     - "/path/to/teaching/modules"
     - "/path/to/student/files"
   ```
   - **`folders`**: A list of absolute paths on your hard drive to be monitored by the crawler and indexed into the vector database.

   *Explanations & Options:* See **[folders.yaml in Configuration](configuration.md#2-foldersyaml)**.

3. **`config/classifier_paths.yaml` (Archiving Paths):**
   Open this file and configure the physical target folders on your hard drive for the respective email classes (e.g., `BachelorThesis`, `MasterThesis`, `Other`):
   ```yaml
   class_paths:
     BachelorThesis: "/path/to/student/bachelor-thesis"
     MasterThesis: "/path/to/student/master-thesis"
     Other: "/path/to/student/other-mails"
   ```
   This is where the email classifier physically files emails.

   *Explanations & Options:* See **[classifier_paths.yaml in Configuration](configuration.md#4-classifier_pathsyaml)**.

### 3. Synchronize Student Data

If you have already created a `students.yaml` (e.g., via the Outlook macros), synchronize it with the SQLite database:

```bash
mcp-uni db sync-students
```

A detailed description of all configuration options and the various `.yaml` files can be found on the **[Configuration](configuration.md)** page.
