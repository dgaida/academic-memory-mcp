"""Modul für die Konfiguration des MCP University Systems."""

from pathlib import Path
from typing import List, Dict, Any, Type, TypeVar
import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMConfig(BaseModel):
    """Konfiguration für das Large Language Model (Ollama)."""

    model: str = "gemma2:2b"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434"


class EmbeddingConfig(BaseModel):
    """Konfiguration für das Embedding-Modell."""

    model: str = "BAAI/bge-m3"


class RerankerConfig(BaseModel):
    """Konfiguration für das Reranker-Modell."""

    model: str = "BAAI/bge-reranker-v2-m3"


class CalendarConfig(BaseModel):
    """Konfiguration für den Kalender."""

    send_invitations_automatically: bool = False


class FolderConfig(BaseModel):
    """Konfiguration der zu überwachenden Ordner und Dateitypen."""

    folders: List[str] = []
    exclude_patterns: List[str] = [".git", "node_modules", "*.tmp", "*.bak"]
    supported_extensions: List[str] = [
        ".pdf",
        ".docx",
        ".md",
        ".txt",
        ".eml",
        ".msg",
        ".py",
        ".ipynb",
        ".json",
        ".html",
    ]
    summarize_emails_individually: bool = False


class Config:
    """Zentrale Konfigurationsklasse für das MCP University System.

    Lädt Einstellungen aus YAML-Dateien im 'config/'-Verzeichnis.
    """

    def __init__(self, config_dir: Path = None):
        """Initialisiert die Konfiguration.

        Args:
            config_dir (Path, optional): Pfad zum Konfigurationsverzeichnis. Defaults to None.
        """
        if config_dir is None:
            config_dir = Path(__file__).resolve().parent.parent / "config"

        self.config_dir = config_dir
        self.folders = self._load_yaml(config_dir / "folders.yaml", FolderConfig)

        models_data = self._load_raw_yaml(config_dir / "models.yaml")
        self.calendar = CalendarConfig(**models_data.get("calendar", {}))
        self.llm = LLMConfig(**models_data.get("llm", {}))
        self.embeddings = EmbeddingConfig(**models_data.get("embeddings", {}))
        self.reranker = RerankerConfig(**models_data.get("reranker", {}))

    def _load_yaml(self, path: Path, model_class: Type[T]) -> T:
        """Lädt eine YAML-Datei in ein Pydantic-Modell.

        Args:
            path (Path): Pfad zur YAML-Datei.
            model_class (Type[T]): Die Pydantic-Klasse.

        Returns:
            T: Instanz des Modells.
        """
        if not path.exists():
            return model_class()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return model_class(**data) if data else model_class()

    def _load_raw_yaml(self, path: Path) -> Dict[str, Any]:
        """Lädt eine YAML-Datei als Dictionary.

        Args:
            path (Path): Pfad zur Datei.

        Returns:
            Dict[str, Any]: Geladene Daten.
        """
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def data_dir(self) -> Path:
        """Gibt den Pfad zum Datenverzeichnis zurück.

        Returns:
            Path: Datenverzeichnis.
        """
        return self.config_dir.parent / "data"

    @property
    def log_path(self) -> Path:
        """Gibt den Pfad zum Log-Verzeichnis zurück.

        Returns:
            Path: Log-Pfad.
        """
        return self.data_dir / "logs"

    @property
    def sqlite_path(self) -> Path:
        """Gibt den Pfad zur SQLite-Datenbank zurück.

        Returns:
            Path: DB-Pfad.
        """
        return self.data_dir / "metadata" / "university.db"

    @property
    def qdrant_path(self) -> Path:
        """Gibt den Pfad zum Qdrant-Index zurück.

        Returns:
            Path: Index-Pfad.
        """
        return self.data_dir / "indexes" / "qdrant"


def get_config() -> Config:
    """Singleton-ähnlicher Zugriff auf die Systemkonfiguration.

    Returns:
        Config: Die aktuelle Konfiguration.
    """
    return Config()
