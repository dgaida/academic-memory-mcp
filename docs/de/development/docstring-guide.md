# Docstring Guide

In diesem Projekt ist eine vollständige Dokumentation des Quellcodes obligatorisch. Wir verwenden den **Google-Style** für Docstrings.

## Format-Beispiel

```python
def example_function(param1: int, param2: str = "default") -> bool:
    """Kurze Einzeilen-Beschreibung der Funktion.

    Längere Beschreibung, die das Verhalten der Funktion im Detail
    erläutert. Hier können mehrere Absätze stehen.

    Args:
        param1 (int): Beschreibung des ersten Parameters.
        param2 (str): Beschreibung des zweiten Parameters.
            Defaults to "default".

    Returns:
        bool: Beschreibung des Rückgabewerts.

    Raises:
        ValueError: Wenn param1 negativ ist.

    Example:
        >>> example_function(42)
        True
    """
    if param1 < 0:
        raise ValueError("param1 muss positiv sein")
    return True
```

## Reales Beispiel aus dem Code (`mcp_university/cli/db.py`)

```python
def get_store_and_index():
    """Initialisiert und gibt den MetadataStore und SearchIndex zurück.

    Nutzt die globale Konfiguration, um die Pfade für die SQLite-Datenbank
    und den Qdrant-Index zu bestimmen.

    Returns:
        Tuple[MetadataStore, SearchIndex]: Ein Tupel bestehend aus dem initialisierten
            Store und dem Suchindex.
    """
```

## Regeln

1.  **Vollständigkeit:** Jede öffentliche und private Methode/Klasse benötigt einen Docstring.
2.  **Type Hints:** Parameter und Rückgabewerte müssen in der Funktionssignatur typisiert sein.
3.  **Sprache:** Docstrings werden in **Deutsch** verfasst. In diesem Projekt bevorzugen wir Deutsch für die fachliche Beschreibung im universitären Kontext.

## Überprüfung

Die Einhaltung wird mittels `interrogate` erzwungen. Der CI-Build schlägt fehl, wenn die Abdeckung unter **95%** fällt.

```bash
interrogate mcp_university/ --fail-under 95
```
