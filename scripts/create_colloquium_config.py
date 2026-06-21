"""Skript zum Erstellen von JSON-Konfigurationsdateien für den colloquium-protocol-creator."""
import json
from pathlib import Path
from typing import Optional, Literal
import typer
from pydantic import BaseModel, Field

class PDFConfig(BaseModel):
    """Konfiguration für die PDF-Datei."""
    filename: str

class ColloquiumDetails(BaseModel):
    """Details zum Kolloquiumstermin und -ort."""
    date: str
    time: str
    location_type: Literal["campus", "company", "online"]
    room: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    zoom_link: Optional[str] = None
    zcode: Optional[str] = None

class LLMConfig(BaseModel):
    """Konfiguration für das Large Language Model."""
    api_choice: Optional[str] = None
    model: Optional[str] = "openai/gpt-oss-120b"
    groq_free: bool = True

class GeminiEvaluation(BaseModel):
    """Konfiguration für die Gemini-Evaluierung."""
    enabled: bool = False
    model: str = "gemini-3-flash-preview"

class OutputConfig(BaseModel):
    """Konfiguration für die Ausgabe."""
    folder: Optional[str] = None
    compile_pdf: bool = True
    fill_form_only: bool = False

class ColloquiumTaskConfig(BaseModel):
    """Gesamtkonfiguration für den Kolloquium-Task."""
    task: str = "colloquium"
    description: str = "Kolloquium"
    pdf: PDFConfig
    colloquium: ColloquiumDetails
    llm: LLMConfig = Field(default_factory=LLMConfig)
    gemini_evaluation: GeminiEvaluation = Field(default_factory=GeminiEvaluation)
    output: OutputConfig = Field(default_factory=OutputConfig)

app = typer.Typer(help="Erstellt JSON-Konfigurationsdateien für den colloquium-protocol-creator.")

@app.command()
def create(
    filename: str = typer.Argument(..., help="Name der PDF-Datei (Bachelorarbeit.pdf)"),
    date: str = typer.Argument(..., help="Datum des Kolloquiums (DD.MM.YYYY)"),
    time: str = typer.Argument(..., help="Uhrzeit des Kolloquiums (HH:MM)"),
    location_type: str = typer.Argument(..., help="Ortstyp: campus, company oder online"),
    room: Optional[str] = typer.Option(None, "--room", help="Raumnummer (bei campus)"),
    company_name: Optional[str] = typer.Option(None, "--company-name", help="Name des Unternehmens (bei company)"),
    company_address: Optional[str] = typer.Option(None, "--company-address", help="Adresse des Unternehmens (bei company)"),
    zoom_link: Optional[str] = typer.Option(None, "--zoom-link", help="Zoom-Link (bei online)"),
    output_path: Path = typer.Option(Path("config.json"), "--output", "-o", help="Pfad zum Speichern der JSON-Datei")
) -> None:
    """
    Erstellt eine JSON-Konfigurationsdatei für ein Kolloquium.

    Args:
        filename (str): Name der PDF-Datei.
        date (str): Datum des Kolloquiums.
        time (str): Uhrzeit des Kolloquiums.
        location_type (str): Ortstyp (campus, company, online).
        room (Optional[str]): Raumnummer.
        company_name (Optional[str]): Name des Unternehmens.
        company_address (Optional[str]): Adresse des Unternehmens.
        zoom_link (Optional[str]): Zoom-Link.
        output_path (Path): Pfad zur Ausgabedatei.
    """
    if location_type not in ["campus", "company", "online"]:
        print(f"Fehler: Ungültiger Ortstyp '{location_type}'. Erlaubt sind: campus, company, online")
        raise typer.Exit(code=1)

    details = ColloquiumDetails(
        date=date,
        time=time,
        location_type=location_type,
        room=room,
        company_name=company_name,
        company_address=company_address,
        zoom_link=zoom_link
    )

    config = ColloquiumTaskConfig(
        pdf=PDFConfig(filename=filename),
        colloquium=details
    )

    # In der Ausgabe-JSON sollen nur gesetzte Felder im 'colloquium' Bereich erscheinen (außer date, time, location_type)
    data = config.model_dump()

    # Bereinigung der optionalen Felder in colloquium
    col_data = data["colloquium"]
    to_remove = []
    for key in ["room", "company_name", "company_address", "zoom_link", "zcode"]:
        if col_data.get(key) is None:
            to_remove.append(key)
    for key in to_remove:
        del col_data[key]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Konfiguration erfolgreich unter {output_path} gespeichert.")

if __name__ == "__main__":
    app()
