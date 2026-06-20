import os
import re
import subprocess
import platform
import pandas as pd
import gradio as gr
from pathlib import Path
from datetime import datetime, timedelta
import yaml

from mcp_university.config import get_config
from mcp_university.classifier.sort_emails import find_student_folder, extract_lastname
from mcp_university.utils.semester import normalize_name

def open_file(filepath):
    if not filepath or not Path(filepath).exists():
        return f"Datei nicht gefunden: {filepath}"

    filepath = str(Path(filepath).absolute())
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])
        return f"Geöffnet: {filepath}"
    except Exception as e:
        return f"Fehler beim Öffnen: {e}"

def parse_appointments():
    config = get_config()
    file_path = config.data_dir / "appointments.md"
    if not file_path.exists():
        return pd.DataFrame(columns=["Start", "Betreff", "Teilnehmer"])

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    data = []
    for line in lines:
        if "|" in line and "---" not in line and "Start | Betreff" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                data.append(parts[:3])

    df = pd.DataFrame(data, columns=["Start", "Betreff", "Teilnehmer"])

    # Filter for this week
    try:
        df["dt"] = pd.to_datetime(df["Start"], errors='coerce')
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)

        #df_week = df[(df["dt"] >= start_of_week) & (df["dt"] < end_of_week)].copy()
        #if df_week.empty:
        #    return df.drop(columns=["dt"])
        #return df_week.drop(columns=["dt"])

        # For the purpose of the task, let's keep all if we want to see something,
        # but the request said "dieser Woche". I'll implement the filter but fallback if empty for demo?
        # No, let's be strict.
        df = df[(df["dt"] >= start_of_week) & (df["dt"] < end_of_week)]
    except Exception as e:
        print(f"Error parsing dates: {e}")

    if "dt" in df.columns:
        df = df.drop(columns=["dt"])
    return df

def get_class_paths():
    config = get_config()
    cp_path = config.config_dir / "classifier_paths.yaml"
    if not cp_path.exists():
        cp_path = config.config_dir / "classifier_paths.yaml.example"

    with open(cp_path, "r", encoding="utf-8") as f:
        cp_data = yaml.safe_load(f)
    return cp_data.get("class_paths", {})

def get_class_from_title(title, class_paths):
    for class_name in class_paths.keys():
        if class_name.lower() in title.lower():
            return class_name
    return "Other"

def extract_email(text):
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0) if match else None

def load_student_details(evt: gr.SelectData, df):
    row_idx = evt.index[0]
    title = df.iloc[row_idx]["Betreff"]
    participant_info = df.iloc[row_idx]["Teilnehmer"]

    class_paths = get_class_paths()
    cls = get_class_from_title(title, class_paths)
    lastname = extract_lastname(participant_info)
    email = extract_email(participant_info)

    student_dir = None
    if cls in class_paths:
        base_path = Path(class_paths[cls])
        student_dir = find_student_folder(base_path, lastname)

    if not student_dir:
        for bp_str in class_paths.values():
            student_dir = find_student_folder(Path(bp_str), lastname)
            if student_dir:
                break

    summary = "### Ordner-Zusammenfassung\n\nKeine Zusammenfassung gefunden."
    if student_dir:
        summary_path = student_dir / ".emails_summary.md"
        if summary_path.exists():
            summary = f"### Ordner-Zusammenfassung\n\n{summary_path.read_text(encoding='utf-8')}"

    profile = "### Steckbrief\n\nKein Steckbrief gefunden."
    if email:
        profile_path = Path("Steckbriefe") / f"{email}.md"
        if not profile_path.exists():
             profile_path = Path(r"D:\Steckbriefe") / f"{email}.md"

        if profile_path.exists():
            profile = f"### Steckbrief\n\n{profile_path.read_text(encoding='utf-8')}"

    explorer_root = str(student_dir) if student_dir and student_dir.exists() else None

    return summary, profile, explorer_root, str(student_dir) if student_dir else ""

def on_file_select(evt: gr.SelectData):
    # evt.value is the path or name
    # FileExplorer select event gives the full path if root is set?
    # Actually it gives the relative path from root.
    return evt.value

with gr.Blocks(title="Appointment Manager") as demo:
    gr.Markdown("# Wochen-Terminplaner & Student-Info")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Termine dieser Woche")
            appointments_df = gr.State(parse_appointments())
            table = gr.DataFrame(value=parse_appointments(), interactive=False)
            refresh_btn = gr.Button("Aktualisieren")

        with gr.Column(scale=2):
            summary_md = gr.Markdown("### Ordner-Zusammenfassung\n\nWähle einen Termin aus.")
            profile_md = gr.Markdown("### Steckbrief\n\nWähle einen Termin aus.")

        with gr.Column(scale=1):
            gr.Markdown("### Dateisystem")
            student_path_display = gr.Textbox(label="Studenten-Pfad", interactive=False)
            explorer = gr.FileExplorer(label="Dateien (Klick zum Öffnen)", file_count="single")
            open_status = gr.Textbox(label="Status", interactive=False)

    def update_table():
        new_df = parse_appointments()
        return new_df, new_df

    refresh_btn.click(update_table, outputs=[table, appointments_df])

    # We need a hidden state or something to store the student_dir for FileExplorer
    # But FileExplorer.root can be updated dynamically?
    # In recent Gradio, FileExplorer doesn't easily update root dynamically via return.
    # We might need to use a different approach if it doesn't work.
    # Actually, we can return a new gr.FileExplorer update.

    def handle_selection(evt: gr.SelectData, df):
        summary, profile, folder_root, folder_str = load_student_details(evt, df)
        if folder_root:
            return summary, profile, gr.update(root=folder_root, visible=True), folder_str
        else:
            return summary, profile, gr.update(visible=False), ""

    table.select(handle_selection, inputs=[appointments_df], outputs=[summary_md, profile_md, explorer, student_path_display])

    def open_selected_file(evt: gr.SelectData, student_dir):
        if not student_dir:
            return "Kein Studenten-Ordner ausgewählt."
        # evt.value is the relative path
        full_path = Path(student_dir) / evt.value[0] if isinstance(evt.value, list) else Path(student_dir) / evt.value
        return open_file(full_path)

    explorer.select(open_selected_file, inputs=[student_path_display], outputs=[open_status])

if __name__ == "__main__":
    demo.launch()
