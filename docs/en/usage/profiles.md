# Person Profiles

The system enables the automatic creation and update of person profiles (Steckbriefe) based on email history and information from the Knowledge Graph.

## Overview

A profile summarizes key information about a person, such as:
- Role (Students, Faculty, etc.)
- Preferred salutation
- First contact date
- Relevant projects, theses, or tasks

These profiles are saved in Markdown format and serve as additional context for the LLM when responding to an email.

## How it Works

### Creation
If no profile exists for an email address, it is automatically created when attempting to reply to an email (or manually via CLI). All available emails for this person are analyzed.

### Automatic Updates
Profiles are dynamic. The system tracks which emails have already been used for profile generation in a separate database (`profiles_tracking.db`).

When new emails for a person are found in the system, the existing profile is automatically updated by the LLM, using the old profile as a base and integrating only the new information.

## CLI Commands

### Updating Profiles
You can update profiles manually via the CLI:

```bash
# Update all existing profiles
mcp-uni profiles update

# Update a specific profile
mcp-uni profiles update --email student@example.com
```

### Create Profile (Legacy/Direct)
```bash
mcp-uni index --profile student@example.com
```

## Troubleshooting: Encoding Issues (Umlauts)

The system features robust decoding for MIME headers (RFC 2047). This prevents errors when processing names with umlauts (e.g., `=?utf-8?Q?'Heike_Fr=C3=B6lin'?=`), which are common in Outlook. If you still encounter issues during folder creation, ensure that your filesystem supports UTF-8.

## File Paths
- **Profiles:** By default under `D:\Steckbriefe\` (configurable).
- **Tracking Database:** `data/profiles_tracking.db`.
