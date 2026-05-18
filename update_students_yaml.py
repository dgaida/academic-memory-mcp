"""Skript zur Synchronisation von Studierendenordnern mit der students.yaml."""
import yaml
from pathlib import Path
import re
from typing import List, Dict, Any


def get_keys_for_project_type(project_type: str) -> List[str]:
    """Gibt die passenden Keys für einen Projekttyp zurück.

    Args:
        project_type: Name des Projektordners (z.B. "BachelorThesen", "Praxisprojekte").

    Returns:
        Liste von Keys für diesen Projekttyp.
    """
    key_mapping = {
        "BachelorThesen": ["BachelorThesis", "Bachelorarbeit", "Kolloquium", "Abschlussarbeit"],
        "MasterThesen": ["MasterThesis", "Masterarbeit", "Kolloquium", "Abschlussarbeit"],
        "PraxisProjekte": ["Praxisprojekt", "Praxis Projekt"],
        "InformatikProjekte": ["Informatikprojekt", "Informatik Projekt", "WI Projekt"], 
        "WASP": ["WASP Projekt", "Wahlspezialisierung"]
    }
    return key_mapping.get(project_type, [])


def find_student_folders(base_path: str) -> List[Dict[str, Any]]:
    """Findet rekursiv alle Studierendenordner bis zum numerischen Level.

    Sucht rekursiv nach Ordnern, bis ein Ordner mit dem Muster ZZZZ_* gefunden wird
    (z.B. "2025_26_WS"). Darunter werden dann alle Unterordner als Studierendenordner
    betrachtet.

    Args:
        base_path: Basisverzeichnis für die Suche.

    Returns:
        Liste von Dictionaries mit 'path' (Studierendenordner), 'project_type' 
        (z.B. "BachelorThesen") und 'keys' (passende Keys für diesen Typ).
    """
    base_dir = Path(base_path)
    if not base_dir.exists():
        print(f"Directory {base_path} does not exist.")
        return []

    pattern = re.compile(r'^\d{4}_')
    student_folders = []

    def search_recursive(current_path: Path, project_type: str = None):
        """Rekursive Hilfsfunktion zur Ordnersuche."""
        try:
            for item in current_path.iterdir():
                if not item.is_dir():
                    continue

                # Prüfe, ob der Ordnername mit ZZZZ_ beginnt
                if pattern.match(item.name):
                    # Wir sind auf dem Stop-Level, die Unterordner sind Studierendenordner
                    keys = list(get_keys_for_project_type(project_type)) if project_type else []
                    for student_folder in item.iterdir():
                        if student_folder.is_dir():
                            student_folders.append({
                                'path': student_folder,
                                'project_type': project_type,
                                'keys': keys.copy()  # Kopie erstellen!
                            })
                else:
                    # Noch nicht am Stop-Level, weiter rekursiv suchen
                    # Wenn wir einen bekannten Projekttyp finden, merken wir ihn
                    new_project_type = project_type
                    if item.name in ["BachelorThesen", "MasterThesen", "PraxisProjekte", "InformatikProjekte", "WASP"]:
                        new_project_type = item.name
                    search_recursive(item, new_project_type)
        except PermissionError:
            print(f"Permission denied: {current_path}")

    search_recursive(base_dir)
    return student_folders


def update_students(base_path: str, yaml_path: str):
    """Sucht nach Studierendenordnern und aktualisiert deren Pfade in der students.yaml.

    Args:
        base_path: Basisverzeichnis der Abschlussarbeiten.
        yaml_path: Pfad zur students.yaml Datei.
    """
    base_dir = Path(base_path)
    if not base_dir.exists():
        print(f"Directory {base_path} does not exist.")
        return

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    if isinstance(data, dict) and 'students' in data:
        students_list = data['students']
    elif isinstance(data, list):
        students_list = data
    else:
        students_list = []

    changed = False
    student_folders = find_student_folders(base_path)

    for folder_info in student_folders:
        folder = folder_info['path']
        keys = folder_info['keys']
        lastname = folder.name
        
        found = False
        for student in students_list:
            if lastname.lower() in student.get('name', '').lower():
                found = True
                
                # Initialisiere folders Liste, falls nicht vorhanden
                if not student.get('folders'):
                    student['folders'] = []
                
                # Prüfe, ob bereits ein Eintrag mit diesen Keys existiert
                existing_folder = None
                for folder_entry in student['folders']:
                    if folder_entry.get('keys') == keys:
                        existing_folder = folder_entry
                        break
                
                # Aktualisiere bestehenden Eintrag oder füge neuen hinzu
                if existing_folder:
                    old_path = existing_folder.get('path')
                    new_path = str(folder.absolute())
                    if old_path != new_path:
                        existing_folder['path'] = new_path
                        changed = True
                        print(f"Updated path for student {student['name']}: {new_path}")
                else:
                    student['folders'].append({
                        'keys': keys,
                        'path': str(folder.absolute())
                    })
                    changed = True
                    print(f"Added folder for student {student['name']}: {folder.absolute()}")
                break

        if not found:
            print(f"No student found for folder: {lastname}")

    if changed:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print("Updated students.yaml successfully.")
    else:
        print("No changes made to students.yaml.")


if __name__ == "__main__":
    BASE_PATH = r"E:\TH_Koeln\BachelorMasterThesen"
    YAML_PATH = r"D:\TH_Koeln\academic-memory-mcp\students.yaml"

    # For local testing, we might want to override these
    import sys
    if len(sys.argv) > 2:
        update_students(sys.argv[1], sys.argv[2])
    else:
        update_students(BASE_PATH, YAML_PATH)
