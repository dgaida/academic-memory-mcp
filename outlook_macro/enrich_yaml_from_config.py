"""enrich_yaml_from_config.py

Liest die email_config.md (EmailSorter-Format) und traegt die darin
enthaltenen Ordnerpfade fuer jeden bekannten Studierenden in die
students.yaml ein.

Fuer jeden Studierenden koennen mehrere Ordner vorhanden sein, die
ueber Schluesselwoerter (Keywords) identifiziert werden:

    KEYWORD_RULES: list[tuple[list[str], str]]

Jede Regel besteht aus einer Liste von Alias-Keywords und einem
kanonischen Haupt-Key.  Ein Pfad wird einer Regel zugeordnet, wenn
eines der Pfad-Segmente (case-insensitiv) einem der Keywords entspricht.
Alle Keywords der Regel werden als Suchbegriffe in Mails gespeichert.

Beispiel:
    Pfad:  C:\\Studierende\\MusterMax\\Bachelorthesis
    Regel: (["bachelorthesis", "bachelorarbeit"], "Bachelorthesis")

Ausgabe-YAML-Struktur pro Studierenden (Ansatz A):

    folders:
      - keys: ["Bachelorthesis", "Bachelorarbeit", "BA-Thesis"]
        path: "C:\\\\Studierende\\\\MusterMax\\\\Bachelorthesis"
      - keys: ["Praxisprojekt", "PP"]
        path: "C:\\\\Studierende\\\\MusterMax\\\\Praxisprojekt"

Usage:
    python enrich_yaml_from_config.py
    python enrich_yaml_from_config.py --config email_config.md --yaml students.yaml
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Konfiguration: Keyword-Regeln
# ---------------------------------------------------------------------------
# Jeder Eintrag: (keywords, canonical_key)
# keywords:       Alle Alias-Keywords fuer diese Regel (case-insensitiv).
#                 Sie werden 1:1 als keys-Liste in der YAML gespeichert und
#                 spaeter beim Keyword-Matching in Mails verwendet.
# canonical_key:  Erster Eintrag der keys-Liste (Haupt-Bezeichner).
#
# Reihenfolge ist wichtig: der erste Treffer gewinnt (fuer denselben Pfad).
# ---------------------------------------------------------------------------
KEYWORD_RULES: list[tuple[list[str], str]] = [
    (
        ["bachelorthesis", "bachelorarbeit", "ba-thesis", "bachelor_thesis"],
        "Bachelorthesis",
    ),
    (["masterthesis", "masterarbeit", "ma-thesis", "master_thesis"], "Masterthesis"),
    (["praxisprojekt", "praxis_projekt", "pp"], "Praxisprojekt"),
    (["anerkennung", "anerkennungen"], "Anerkennung"),
    (["seminar"], "Seminar"),
    (["pruefung", "pruefungen", "exam"], "Pruefung"),
    (["kolloquium"], "Kolloquium"),
    (["beratung", "beratungen"], "Beratung"),
    (["allgemein", "sonstiges", "misc"], "Allgemein"),
]


# ---------------------------------------------------------------------------
# Pfade
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = Path("D:/TH_Koeln/academic-memory-mcp/email_config.md")
DEFAULT_YAML_PATH = Path("D:/TH_Koeln/academic-memory-mcp/students.yaml")


# ---------------------------------------------------------------------------
# email_config.md einlesen
# ---------------------------------------------------------------------------


def read_email_config(config_path: Path) -> dict[str, str]:
    """Liest die email_config.md und gibt ein Dict {email_lower: folder_path} zurueck.

    Args:
        config_path: Pfad zur Markdown-Konfigurationsdatei.

    Returns:
        Dictionary mit E-Mail-Adressen (Lowercase) als Keys und
        Dateisystem-Ordnerpfaden als Values.

    Raises:
        FileNotFoundError: Wenn die Konfigurationsdatei nicht gefunden wird.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")

    email_map: dict[str, str] = {}

    for raw_line in config_path.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        line = raw_line.strip()

        # Leerzeilen und Kommentare ueberspringen
        if not line or line.startswith("#"):
            continue

        # Trenner: Tab oder mind. 2 Leerzeichen
        if "\t" in line:
            parts = line.split("\t", 1)
        else:
            match = re.split(r" {2,}", line, maxsplit=1)
            parts = match if len(match) == 2 else []  # type: ignore[assignment]

        if len(parts) != 2:
            continue

        email_addr = parts[0].strip().lower()
        folder_path = parts[1].strip()

        # Markdown-Escapes aufloesen
        folder_path = folder_path.replace(r"\_", "_").replace("\\\\", "\\")

        if email_addr and folder_path:
            email_map[email_addr] = folder_path

    return email_map


# ---------------------------------------------------------------------------
# Keyword-Matching
# ---------------------------------------------------------------------------


def classify_path(
    folder_path: str,
    rules: list[tuple[list[str], str]],
) -> tuple[list[str], str] | None:
    """Ordnet einen Ordnerpfad anhand der Keyword-Regeln einer Regel zu.

    Jedes Pfad-Segment wird case-insensitiv gegen die Keywords jeder Regel
    geprueft.  Die erste passende Regel gewinnt.

    Args:
        folder_path: Ordnerpfad als String (Windows- oder POSIX-Trennzeichen).
        rules: Geordnete Liste von (keywords, canonical_key)-Tupeln.

    Returns:
        Das Tupel (keywords, canonical_key) der ersten passenden Regel,
        oder None wenn keine Regel passt.
    """
    segments = [s.lower() for s in re.split(r"[/\\]", folder_path) if s]

    for keywords, canonical_key in rules:
        for kw in keywords:
            if any(kw.lower() in seg for seg in segments):
                return keywords, canonical_key

    return None


@dataclass
class FolderEntry:
    """Ein Ordner-Eintrag mit Alias-Keywords und Pfad.

    Attributes:
        keys: Liste von Suchbegriffen (z.B. ["Bachelorthesis", "Bachelorarbeit"]).
              Der erste Eintrag gilt als kanonischer Bezeichner.
        path: Absoluter Ordnerpfad auf dem Dateisystem.
    """

    keys: list[str]
    path: str


# ---------------------------------------------------------------------------
# YAML einlesen (zustandsorientierter Mini-Parser)
# ---------------------------------------------------------------------------


class Student:
    """Repraesentiert einen Studierenden mit allen YAML-Feldern.

    Attributes:
        name:    Vollstaendiger Anzeigename.
        smail:   Primaere smail-Adresse (Lowercase).
        emails:  Liste weiterer bekannter E-Mail-Adressen.
        folders: Liste von FolderEntry-Objekten (keys + path).
        raw_extra_lines: Zeilen aus dem YAML-Block, die nicht geparst wurden,
                         damit sie beim Schreiben erhalten bleiben.
    """

    def __init__(self) -> None:
        self.name: str = ""
        self.smail: str = ""
        self.emails: list[str] = []
        self.folders: list[FolderEntry] = []
        self.raw_extra_lines: list[str] = []


def load_students_yaml(yaml_path: Path) -> list[Student]:
    """Liest students.yaml und gibt eine Liste von Student-Objekten zurueck.

    Unterstuetztes Format (Einrueckung 0 fuer Studierenden-Eintraege)::

        students:
        - name: Max Mustermann
          smail: m.mustermann@smail.th-koeln.de
          emails: []
          folders:
          - keys:
            - Bachelorthesis
            - Bachelorarbeit
            path: C:\\Ablage\\Mustermann\\Bachelorthesis

    Args:
        yaml_path: Pfad zur YAML-Datei.

    Returns:
        Liste von Student-Objekten; leer wenn die Datei nicht existiert.
    """
    if not yaml_path.exists():
        return []

    lines = yaml_path.read_text(encoding="utf-8", errors="replace").splitlines()

    students: list[Student] = []
    current: Student | None = None
    # Zustaende: root | in_student | in_emails | in_folders | in_folder_entry | in_keys
    state: str = "root"
    current_entry: FolderEntry | None = None

    def _commit_entry() -> None:
        """Schliesst den aktuellen FolderEntry ab und haengt ihn an current.folders."""
        nonlocal current_entry
        if current_entry is not None and current_entry.path and current_entry.keys:
            assert current is not None
            current.folders.append(current_entry)
        current_entry = None

    for raw in lines:
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))

        # Studierenden-Block: "- " auf Indent 0
        if stripped.startswith("- ") and indent == 0:
            _commit_entry()
            if current is not None:
                students.append(current)
            current = Student()
            state = "in_student"
            after_dash = stripped[2:].strip()
            if after_dash.startswith("name:"):
                current.name = _extract_yaml_value(after_dash, "name")
            continue

        if current is None:
            continue

        if stripped.startswith("name:"):
            _commit_entry()
            current.name = _extract_yaml_value(stripped, "name")
            state = "in_student"

        elif stripped.startswith("smail:"):
            _commit_entry()
            current.smail = _extract_yaml_value(stripped, "smail").lower()
            state = "in_student"

        elif stripped.startswith("emails:"):
            _commit_entry()
            rest = stripped[7:].strip()
            if rest.startswith("["):
                current.emails = _parse_inline_list(rest, lowercase=True)
                state = "in_student"
            else:
                state = "in_emails"

        elif state == "in_emails" and stripped.startswith("- "):
            addr = stripped[2:].strip().strip('"').strip("'").lower()
            if addr:
                current.emails.append(addr)

        elif stripped.startswith("folders:"):
            _commit_entry()
            rest = stripped[8:].strip()
            state = "in_student" if rest in ("", "[]") else "in_folders"

        # Neuer folder-Eintrag: "- keys:" oder "- path:" auf Indent 2
        elif (
            state in ("in_folders", "in_folder_entry")
            and stripped.startswith("- ")
            and indent == 2
        ):
            _commit_entry()
            current_entry = FolderEntry(keys=[], path="")
            state = "in_folder_entry"
            after_dash = stripped[2:].strip()
            if after_dash.startswith("keys:"):
                rest = after_dash[5:].strip()
                if rest.startswith("["):
                    # Inline: - keys: ["A", "B"]
                    current_entry.keys = _parse_inline_list(rest, lowercase=False)
                else:
                    # Block: naechste Zeilen "- Keyword" auf Indent 4
                    state = "in_keys"
            elif after_dash.startswith("path:"):
                current_entry.path = _extract_yaml_value(after_dash, "path")

        # Block-keys: "- Keyword" auf Indent 4
        elif state == "in_keys" and stripped.startswith("- ") and indent == 4:
            kw = stripped[2:].strip().strip('"').strip("'")
            if kw and current_entry is not None:
                current_entry.keys.append(kw)

        elif state in ("in_folder_entry", "in_keys") and current_entry is not None:
            if stripped.startswith("keys:"):
                rest = stripped[5:].strip()
                if rest.startswith("["):
                    current_entry.keys = _parse_inline_list(rest, lowercase=False)
                    state = "in_folder_entry"
                else:
                    state = "in_keys"
            elif stripped.startswith("path:"):
                current_entry.path = _extract_yaml_value(stripped, "path")
                state = "in_folder_entry"
            elif (
                stripped
                and not stripped.startswith("#")
                and indent <= 2
                and not stripped.startswith("- ")
            ):
                _commit_entry()
                state = "in_student"

        elif state == "in_student":
            if stripped and not stripped.startswith("#"):
                current.raw_extra_lines.append(raw)

    _commit_entry()
    if current is not None:
        students.append(current)

    return students


def _extract_yaml_value(line: str, key: str) -> str:
    """Extrahiert den Wert aus einer YAML-Zeile der Form ``key: "value"``.

    Args:
        line: Die (bereits getrimmte) YAML-Zeile.
        key:  Der Schlusselname ohne Doppelpunkt.

    Returns:
        Den Wert ohne Anfuehrungszeichen, oder leerer String.
    """
    prefix = f"{key}:"
    if not line.startswith(prefix):
        return ""
    return line[len(prefix) :].strip().strip('"').strip("'")


def _parse_inline_list(raw: str, *, lowercase: bool = False) -> list[str]:
    """Parst eine YAML-Inline-Liste  ``["a", "b"]``  in eine Python-Liste.

    Args:
        raw:       Der rohe String (mit oder ohne eckige Klammern).
        lowercase: Wenn True, werden alle Eintraege in Kleinbuchstaben
                   umgewandelt (z.B. fuer E-Mail-Adressen).

    Returns:
        Liste der enthaltenen String-Werte.
    """
    raw = raw.strip("[]")
    if not raw.strip():
        return []
    items = [item.strip().strip('"').strip("'") for item in raw.split(",")]
    if lowercase:
        items = [i.lower() for i in items]
    return [i for i in items if i]


# ---------------------------------------------------------------------------
# Ordnerpfade zuordnen
# ---------------------------------------------------------------------------


def enrich_students(
    students: list[Student],
    email_map: dict[str, str],
    rules: list[tuple[list[str], str]],
) -> tuple[int, int]:
    """Ordnet Ordnerpfade aus email_map den passenden Studierenden zu.

    Ein Ordnerpfad wird einem Studierenden zugeordnet, wenn eine seiner
    bekannten Adressen (smail oder emails) in email_map vorkommt.

    Der Pfad wird als neuer FolderEntry mit den Keywords der passenden Regel
    in student.folders eingetragen.  Existiert bereits ein Eintrag mit
    demselben kanonischen Key (erster Eintrag von keys), wird der Pfad nur
    aktualisiert wenn er sich geaendert hat.

    Args:
        students:  Liste von Student-Objekten (werden in-place veraendert).
        email_map: Dict {email_lower: folder_path} aus read_email_config.
        rules:     Keyword-Regeln fuer classify_path.

    Returns:
        Tupel (neue_eintraege, geaenderte_eintraege).
    """
    new_count = 0
    changed_count = 0

    for student in students:
        known_addresses = {student.smail} | set(student.emails)

        for addr in known_addresses:
            if addr not in email_map:
                continue

            folder_path = email_map[addr]
            match = classify_path(folder_path, rules)

            if match is None:
                # Kein Keyword-Match -> Pfad-Basename als einziges Keyword
                fallback_key = Path(folder_path).name or addr
                keywords = [fallback_key]
            else:
                keywords, _ = match

            canonical = keywords[0]

            # Bestehenden Eintrag mit gleichem kanonischen Key suchen
            existing = next(
                (e for e in student.folders if e.keys and e.keys[0] == canonical),
                None,
            )
            if existing is None:
                student.folders.append(FolderEntry(keys=keywords, path=folder_path))
                new_count += 1
            elif existing.path != folder_path:
                existing.path = folder_path
                changed_count += 1

    return new_count, changed_count


# ---------------------------------------------------------------------------
# YAML schreiben
# ---------------------------------------------------------------------------


def write_students_yaml(yaml_path: Path, students: list[Student]) -> None:
    """Schreibt die Studierenden-Liste in die YAML-Datei.

    Format ohne Anfuehrungszeichen, Studierenden-Eintraege auf Einrueckung 0,
    keys als Block-Liste::

        students:
        - name: Max Mustermann
          smail: m.mustermann@smail.th-koeln.de
          emails: []
          folders:
          - keys:
            - Bachelorthesis
            - Bachelorarbeit
            path: C:\\Ablage\\Mustermann\\Bachelorthesis

    Args:
        yaml_path: Zielpfad der YAML-Datei.
        students:  Liste von Student-Objekten.
    """
    lines: list[str] = ["students:"]

    for student in students:
        lines.append(f"- name: {student.name}")
        lines.append(f"  smail: {student.smail}")

        # emails
        if not student.emails:
            lines.append("  emails: []")
        else:
            lines.append("  emails:")
            for addr in student.emails:
                lines.append(f"  - {addr}")

        # folders (Block-keys-Liste)
        if not student.folders:
            lines.append("  folders: []")
        else:
            lines.append("  folders:")
            for entry in student.folders:
                lines.append("  - keys:")
                for k in entry.keys:
                    lines.append(f"    - {k}")
                lines.append(f"    path: {entry.path}")

        for extra in student.raw_extra_lines:
            lines.append(extra)

        lines.append("")

    yaml_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------


def main() -> None:
    """Hauptfunktion: parst Argumente und fuehrt die Anreicherung durch."""
    parser = argparse.ArgumentParser(
        description="Reichert students.yaml mit Ordnerpfaden aus email_config.md an."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Pfad zur email_config.md (Standard: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--yaml",
        type=Path,
        default=DEFAULT_YAML_PATH,
        help=f"Pfad zur students.yaml (Standard: {DEFAULT_YAML_PATH})",
    )
    args = parser.parse_args()

    config_path: Path = args.config
    yaml_path: Path = args.yaml

    print(f"Lese Konfiguration: {config_path}")
    try:
        email_map = read_email_config(config_path)
    except FileNotFoundError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"  {len(email_map)} E-Mail-Eintraege gefunden.")

    print(f"Lese YAML: {yaml_path}")
    students = load_students_yaml(yaml_path)
    print(f"  {len(students)} Studierende geladen.")

    if not students:
        print(
            "Keine Studierenden in der YAML-Datei. Bitte zuerst CollectStudentEmails ausfuehren."
        )
        sys.exit(0)

    new_count, changed_count = enrich_students(students, email_map, KEYWORD_RULES)

    print(f"Schreibe YAML: {yaml_path}")
    write_students_yaml(yaml_path, students)

    print(
        f"Fertig!  {new_count} neue Ordner-Eintraege,  "
        f"{changed_count} aktualisierte Ordner-Eintraege."
    )


if __name__ == "__main__":
    main()
