# Setting Up the Software

This page describes the necessary steps for the initial setup and installation of the MCP University System.

## Prerequisites

- Python 3.10 or higher  
- Ollama (for local LLM support)  
- Outlook (for working with .msg files and calendar integration under Windows)  

## Installation

1. Clone the repository.  
2. Create a virtual environment and install the dependencies:  

```bash
pip install -e .
```

Or use the provided `environment.yml` with Conda:

```bash
conda env create -f environment.yml
conda activate mcp-university
```

## Initial Setup (Setup Workflow)

To get the system up and running, perform the following steps:

1. **Prepare Configuration Files:**  
   Copy the `.example` configuration files in the `config/` directory:
   ```bash
   cp config/user.yaml.example config/user.yaml
   cp config/ontology.yaml.example config/ontology.yaml
   cp config/classifier_paths.yaml.example config/classifier_paths.yaml
   ```

2. **Customize User Data:**  
   Enter your name and your university email in `config/user.yaml`.

3. **Synchronize Student Data:**  
   If you have already created a `students.yaml` (e.g., via the Outlook macros), synchronize it with the SQLite database:
   ```bash
   mcp-uni db sync-students
   ```

A detailed description of all configuration options and the various `.yaml` files can be found on the **[Configuration](configuration.md)** page.
