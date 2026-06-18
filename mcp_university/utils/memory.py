from pathlib import Path
from typing import Dict

def resolve_memory_index_names(class_paths: Dict[str, str]) -> Dict[str, str]:
    """
    Maps each class name to its corresponding vector database folder name.

    If multiple classes share the same path, the folder name is derived from
    the prefix of the class name (before the first '_').
    Otherwise, the class name itself is used as the folder name.
    """
    path_to_classes = {}
    for class_name, path_str in class_paths.items():
        # Normalize path to handle different separators/formats
        try:
            path = str(Path(path_str).absolute())
        except Exception:
            path = path_str
        path_to_classes.setdefault(path, []).append(class_name)

    class_to_index_name = {}
    for path, classes in path_to_classes.items():
        if len(classes) > 1:
            # Multiple classes share the path.
            # Per requirement: Use the prefix before '_' from the first class.
            # Assuming classes follow the naming convention if they share a path.
            first_class = classes[0]
            if "_" in first_class:
                index_name = first_class.split("_")[0]
            else:
                index_name = first_class
        else:
            # Single class for this path
            index_name = classes[0]

        for c in classes:
            class_to_index_name[c] = index_name

    return class_to_index_name
