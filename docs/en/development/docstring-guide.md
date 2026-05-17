# Docstring Guide

In this project, complete documentation of the source code is mandatory. We use the **Google-style** for docstrings.

## Format Example

```python
def example_function(param1: int, param2: str = "default") -> bool:
    """Short one-line description of the function.

    Longer description explaining the function's behavior in detail.
    Multiple paragraphs can be used here.

    Args:
        param1 (int): Description of the first parameter.
        param2 (str): Description of the second parameter.
            Defaults to "default".

    Returns:
        bool: Description of the return value.

    Raises:
        ValueError: If param1 is negative.

    Example:
        >>> example_function(42)
        True
    """
    if param1 < 0:
        raise ValueError("param1 must be positive")
    return True
```

## Real Example from Code (`mcp_university/cli/db.py`)

```python
def get_store_and_index():
    """Initializes and returns the MetadataStore and SearchIndex.

    Uses the global configuration to determine the paths for the SQLite database
    and the Qdrant index.

    Returns:
        Tuple[MetadataStore, SearchIndex]: A tuple consisting of the initialized
            store and the search index.
    """
```

## Rules

1.  **Completeness:** Every public and private method/class requires a docstring.  
2.  **Type Hints:** Parameters and return values must be typed in the function signature.  
3.  **Language:** Docstrings are written in **German**. In this project, we prefer German for technical descriptions in the university context.  

## Verification

Compliance is enforced using `interrogate`. The CI build will fail if coverage falls below **95%**.

```bash
interrogate mcp_university/ --fail-under 95
```
