import json
from pathlib import Path
from okf.config import OKFConfig

def load_spec(spec_file: Path) -> str:
    """Load the OKF specification from a file.

    Args:
        spec_file: Path to the OKF specification file.

    Returns:
        The content of the specification.
    """
    if not spec_file.exists():
        # Fallback if spec file doesn't exist to avoid crashing
        return "OKF Specification Version 0.2"
    return spec_file.read_text(encoding="utf-8")

def ask_llm(config: OKFConfig, system_prompt: str, user_prompt: str) -> dict:
    """Call LLM with system and user prompts and return the parsed JSON response.

    Args:
        config: OKFConfig instance.
        system_prompt: The system instruction.
        user_prompt: The user query/content.

    Returns:
        A dict parsed from LLM's JSON response.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    response = config.client.chat_completion(messages)
    return json.loads(response)

def extract_knowledge(markdown: str, filename: str, spec: str, config: OKFConfig) -> dict:
    """Analyze a source document and extract structured OKF knowledge artifacts.

    Args:
        markdown: Markdown content of the source document.
        filename: Name of the source file.
        spec: The OKF specification.
        config: OKFConfig instance.

    Returns:
        A dict containing concepts, entities, definitions, tables, and relations.
    """
    system_prompt = """
You are an expert Knowledge Engineer specialized in the Open Knowledge Format
(OKF) version 0.2.

Your task is to analyze source documents and extract structured knowledge
artifacts that can be stored in an OKF knowledge bundle.

You must:
- strictly follow the OKF specification
- preserve provenance
- extract only information explicitly supported by the source document
- never invent facts
- return only valid JSON
- do not include Markdown fences
"""

    user_prompt = f"""
Analyze the following source document and extract OKF knowledge artifacts.

The artifacts are:

1. Concepts
----------------
Concepts are abstract knowledge units or topics.

Examples:
- Examination procedure
- Machine Learning
- Transformer Architecture
- Competency-based education

A concept is NOT a concrete named object.

Extract:
- name
- description
- related concepts if obvious


2. Entities
----------------
Entities are concrete identifiable objects.

Examples:
- Person
- Organization
- University
- Software system
- Course
- Regulation
- Product

Extract:
- name
- entity type
- description


3. Definitions
----------------
Definitions are explicit explanations of terms.

Look for patterns like:
- "X is ..."
- "X bezeichnet ..."
- "Unter X versteht man ..."
- "X refers to ..."

Extract:
- term
- definition text
- source context


4. Tables
----------------
Extract meaningful tables.

A table should only be extracted if it contains structured information
that is useful independently from the document.

Examples:
- module overview
- comparison tables
- schedules
- parameter tables

Extract:
- title
- columns
- rows


--------------------
OKF SPECIFICATION
--------------------

{spec}


--------------------
SOURCE DOCUMENT
--------------------

Filename:

{filename}


Content:

{markdown}


Return ONLY this JSON structure:

{{
  "document": {{
    "title": "",
    "description": "",
    "source_file": "{filename}"
  }},

  "concepts": [
    {{
      "name": "",
      "description": "",
      "related_concepts": []
    }}
  ],

  "entities": [
    {{
      "name": "",
      "type": "",
      "description": ""
    }}
  ],

  "definitions": [
    {{
      "term": "",
      "definition": "",
      "context": ""
    }}
  ],

  "tables": [
    {{
      "title": "",
      "description": "",
      "columns": [],
      "rows": []
    }}
  ],

  "relations": [
    {{
      "source": "",
      "relation": "",
      "target": ""
    }}
  ]
}}


Additional rules:

- Keep names concise.
- Do not duplicate the same artifact.
- Prefer fewer high-quality artifacts over many weak artifacts.
- Every extracted artifact must be traceable to the source document.
- If no artifacts of a type exist, return an empty array.
"""
    return ask_llm(config, system_prompt, user_prompt)
