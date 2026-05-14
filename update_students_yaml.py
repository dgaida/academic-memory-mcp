"""Skript zur Synchronisation von Studierendenordnern mit der students.yaml."""
import yaml
from pathlib import Path

def update_students(base_path: str, yaml_path: str):
    """Sucht nach Studierendenordnern und aktualisiert deren Pfade in der students.yaml.

    Args:
        base_path (str): Basisverzeichnis der Abschlussarbeiten.
        yaml_path (str): Pfad zur students.yaml Datei.
    """
    base_dir = Path(base_path)
    if not base_dir.exists():
        print(f"Directory {base_path} does not exist.")
        return

    with open(yaml_path, 'r', encoding='utf-8') as f:
        students_data = yaml.safe_load(f) or []

    changed = False
    student_folders = [d for d in base_dir.iterdir() if d.is_dir()]

    for folder in student_folders:
        lastname = folder.name
        found = False
        for student in students_data:
            if lastname in student.get('name', ''):
                found = True
                if not student.get('folders'):
                    student['folders'] = [
                        {
                            'keys': ["BachelorThesis", "Bachelorarbeit", "Kolloquium", "Abschlussarbeit"],
                            'path': str(folder.absolute())
                        }
                    ]
                    changed = True
                    print(f"Updated folders for student: {student['name']}")
                break

        if not found:
            print(f"No student found for folder: {lastname}")

    if changed:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(students_data, f, allow_unicode=True, sort_keys=False)
        print("Updated students.yaml successfully.")
    else:
        print("No changes made to students.yaml.")

if __name__ == "__main__":
    BASE_PATH = r"D:\TH_Koeln\BachelorMasterThesen\BachelorThesen\2025_26_WS"
    YAML_PATH = r"D:\TH_Koeln\academic-memory-mcp\students.yaml"

    # For local testing, we might want to override these
    import sys
    if len(sys.argv) > 2:
        update_students(sys.argv[1], sys.argv[2])
    else:
        update_students(BASE_PATH, YAML_PATH)
