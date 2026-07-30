"""Kommandozeilen-Schnittstelle (CLI) für das MCP University System."""
import typer
import logging
from logging.handlers import RotatingFileHandler
from ..crawler.crawler import Crawler, run_index_or_profile
from ..config import get_config
from ..metadata.store import MetadataStore
from academic_parser.factory import ParserFactory
from ..summarizer.engine import Summarizer
from ..summarizer.profiler import PersonProfiler
from ..retrieval.index import SearchIndex, perform_search
from ..mcp_server.server import create_server
from ..knowledge_graph.engine import KnowledgeGraphEngine, build_knowledge_graph
from .db import db_app
from .memory import memory_app
import yaml  # noqa: F401

profiles_app = typer.Typer(help="Verwaltung von Personen-Steckbriefen")

@profiles_app.command("update")
def profiles_update(
    email: str = typer.Option(None, "--email", "-e", help="E-Mail-Adresse der zu aktualisierenden Person."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")
) -> None:
    """Aktualisiert Personen-Steckbriefe."""
    setup_logging(debug)
    profiler = PersonProfiler()
    if email:
        print(f"Aktualisiere Steckbrief für {email}...")
        profiler.update_profile(email)
    else:
        print("Aktualisiere alle Steckbriefe...")
        profiler.update_all_profiles()
    print("Fertig.")


logger = logging.getLogger(__name__)

graph_app = typer.Typer(help="Verwaltung des Wissensgraphen")


@graph_app.command("build")
def graph_build(debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")) -> None:
    """Baut den Wissensgraphen basierend auf den vorhandenen Zusammenfassungen auf."""
    setup_logging(debug)
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    graph_engine = KnowledgeGraphEngine(store, summarizer)

    build_knowledge_graph(cfg, store, summarizer, graph_engine)


@graph_app.command("visualize")
def graph_visualize(
    filter: str = typer.Option(None, "--filter", "-f", help="Filtert den Graphen nach einem Knotennamen."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")
) -> None:
    """Generiert eine interaktive HTML-Visualisierung des Wissensgraphen."""
    setup_logging(debug)
    from scripts.visualize_knowledge_graph import main as run_viz

    import sys
    original_argv = sys.argv
    sys.argv = ["visualize_knowledge_graph.py"]
    if filter:
        sys.argv.extend(["--filter", filter])

    try:
        run_viz()
    finally:
        sys.argv = original_argv


app = typer.Typer(help="MCP University Memory System CLI - Lokales Wissensmanagement für die Universität")
app.add_typer(graph_app, name="graph")
app.add_typer(db_app, name="db")
app.add_typer(profiles_app, name="profiles")
app.add_typer(memory_app, name="memory")

def setup_logging(debug: bool) -> None:
    """Konfiguriert das Logging für Konsole und Datei."""
    cfg = get_config()
    log_dir = cfg.log_path
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "mcp-university.log"

    # Basis-Konfiguration für das Root-Logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console Handler
    console_level = logging.DEBUG if debug else logging.INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # File Handler (immer DEBUG)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024, # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Vorhandene Handler entfernen, um Duplikate zu vermeiden
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

@app.command()
def index(
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren"),
    profile: str = typer.Option(None, "--profile", "-p", help="Erstellt einen Steckbrief für die angegebene E-Mail-Adresse anstatt zu indexieren.")
) -> None:
    """Startet den vollständigen Indexierungsprozess aller konfigurierten Ordner oder erstellt einen Personen-Steckbrief."""
    setup_logging(debug)
    cfg = get_config()

    run_index_or_profile(profile, cfg)

@app.command()
def search(
    query: str,
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")
) -> None:
    """Führt eine hybride Suche über die indexierten Dokumente aus und generiert eine Antwort.

    Args:
        query: Der Suchbegriff oder die Frage.
        debug: Wenn True, wird Debug-Logging aktiviert.
    """
    setup_logging(debug)
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)

    perform_search(query, cfg, store, idx)

@app.command()
def watch(debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")) -> None:
    """Startet den Watchdog zur Echtzeit-Überwachung von Ordnern."""
    setup_logging(debug)
    from ..crawler.watcher import Watcher
    cfg = get_config()
    store = MetadataStore(cfg.sqlite_path)
    academic_parser = ParserFactory(cfg.data_dir / "cache")
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)

    crawler = Crawler(cfg, store, academic_parser, summarizer, idx)
    watcher = Watcher(crawler)
    watcher.start()

@app.command()
def serve_mcp(debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")) -> None:
    """Startet den FastMCP-Server zur Integration in KI-Agenten."""
    setup_logging(debug)
    server = create_server()
    server.run()

if __name__ == "__main__":
    app()
