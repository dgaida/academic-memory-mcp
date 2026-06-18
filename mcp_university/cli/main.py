"""Kommandozeilen-Schnittstelle (CLI) für das MCP University System."""
from pathlib import Path
import typer
import logging
import sys
from logging.handlers import RotatingFileHandler
from ..crawler.crawler import Crawler
from ..config import get_config
from ..metadata.store import MetadataStore
from ..parser.factory import ParserFactory
from ..summarizer.engine import Summarizer
from ..summarizer.profiler import PersonProfiler
from ..retrieval.index import SearchIndex
from ..mcp_server.server import create_server
from ..knowledge_graph.engine import KnowledgeGraphEngine
import yaml
from .db import db_app

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
    """Baut den studentischen Wissensgraphen (Verbindungen zum User)."""
    setup_logging(debug)
    cfg = get_config()
    store = MetadataStore(cfg.metadata_db_path)
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    graph_engine = KnowledgeGraphEngine(store, summarizer)

    user_node_id, _ = store.upsert_node(cfg.user.name, "Person", {"email": cfg.user.email, "role": ["User"]})
    print(f"Benutzer-Knoten initialisiert: {cfg.user.name}")

    paths_file = cfg.config_dir / "classifier_paths.yaml"
    if not paths_file.exists():
        paths_file = cfg.config_dir / "classifier_paths.yaml.example"
    if not paths_file.exists():
        print("Fehler: classifier_paths.yaml nicht gefunden.")
        return

    with open(paths_file, "r", encoding="utf-8") as f:
        paths_data = yaml.safe_load(f)
    class_paths = paths_data.get("class_paths", {})

    for class_name, base_path_str in class_paths.items():
        base_path = Path(base_path_str)
        if not base_path.exists():
            continue
        print(f"Verarbeite Klasse: {class_name}")
        for summary_file in base_path.rglob(".emails_summary.md"):
            content = summary_file.read_text(encoding='utf-8')
            changes = graph_engine.process_summary(content, user_node_id)
            if any(changes.values()):
                print(f"    Änderungen aus {summary_file.name}: {changes}")
    print("Studentischer Wissensgraph erfolgreich aktualisiert.")

@graph_app.command("visualize")
def graph_visualize(
    filter: str = typer.Option(None, "--filter", "-f", help="Filtert den Graphen."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")
) -> None:
    """Generiert eine HTML-Visualisierung."""
    setup_logging(debug)
    from scripts.visualize_knowledge_graph import main as run_viz
    original_argv = sys.argv
    sys.argv = ["visualize_knowledge_graph.py"]
    if filter:
        sys.argv.extend(["--filter", filter])
    try:
        run_viz()
    finally:
        sys.argv = original_argv

app = typer.Typer(help="MCP University CLI")
app.add_typer(graph_app, name="graph")
app.add_typer(db_app, name="db")
app.add_typer(profiles_app, name="profiles")

def setup_logging(debug: bool) -> None:
    """Konfiguriert das Logging."""
    cfg = get_config()
    cfg.log_path.mkdir(parents=True, exist_ok=True)
    log_file = cfg.log_path / "mcp-university.log"
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

@app.command()
def index(
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren"),
    profile: str = typer.Option(None, "--profile", "-p", help="Erstellt einen Steckbrief.")
) -> None:
    """Startet Indexierung oder erstellt Steckbrief."""
    setup_logging(debug)
    cfg = get_config()
    if profile:
        profiler = PersonProfiler()
        if profiler.generate_profile(profile):
            print(f"Steckbrief für {profile} erstellt.")
        return
    store = MetadataStore(cfg.metadata_db_path)
    parser = ParserFactory(cfg.data_dir / "cache")
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)
    crawler = Crawler(cfg, store, parser, summarizer, idx)
    crawler.crawl()

@app.command()
def search(query: str, debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")) -> None:
    """Führt hybride Suche aus."""
    setup_logging(debug)
    cfg = get_config()
    store = MetadataStore(cfg.metadata_db_path)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)
    results = idx.search(query)
    for res in results:
        print(f"[{res['score']:.2f}] {res['filename']}")
    if results:
        summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)
        context = "\n\n".join([r['content'] for r in results])
        print(summarizer.answer_question(query, context))

@app.command()
def watch(debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")) -> None:
    """Startet Watchdog."""
    setup_logging(debug)
    from ..crawler.watcher import Watcher
    cfg = get_config()
    store = MetadataStore(cfg.metadata_db_path)
    idx = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model, store=store)
    crawler = Crawler(cfg, store, ParserFactory(cfg.data_dir / "cache"), Summarizer(cfg.llm.model, cfg.llm.base_url), idx)
    Watcher(crawler).start()

@app.command()
def serve_mcp(debug: bool = typer.Option(False, "--debug", "-d", help="Debug-Logging aktivieren")) -> None:
    """Startet MCP-Server."""
    setup_logging(debug)
    create_server().run()

if __name__ == "__main__":
    app()
