"""Modul für die Konfiguration des MCP University Systems."""
import os

# Configure Hugging Face Hub settings to prevent hangs and timeouts
if "HF_HUB_DISABLE_XET" not in os.environ:
    os.environ["HF_HUB_DISABLE_XET"] = "1"
if "HF_HUB_DOWNLOAD_TIMEOUT" not in os.environ:
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "30"

from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any, Type, TypeVar, Union
import yaml
from pydantic import BaseModel, model_validator

T = TypeVar("T", bound=BaseModel)

class LLMConfig(BaseModel):
    """Konfiguration für das Large Language Model (Ollama)."""
    model: str = "gemma2:2b"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434"
    num_ctx: int = 8192
    num_predict: int = 2048

class EmbeddingConfig(BaseModel):
    """Konfiguration für das Embedding-Modell."""
    model: str = "BAAI/bge-m3"

class RerankerConfig(BaseModel):
    """Konfiguration für das Reranker-Modell."""
    model: str = "BAAI/bge-reranker-v2-m3"

class CalendarConfig(BaseModel):
    """Konfiguration für den Kalender."""
    send_invitations_automatically: bool = False
    appointment_slots_path: str = "data/free_slots.md"

class FolderConfig(BaseModel):
    """Konfiguration der zu überwachenden Ordner und Dateitypen."""
    folders: List[str] = []
    exclude_patterns: List[str] = [".git", "node_modules", "*.tmp", "*.bak"]
    supported_extensions: List[str] = [".pdf", ".docx", ".md", ".txt", ".eml", ".msg", ".py", ".ipynb", ".json", ".html"]
    summarize_emails_individually: bool = False


class OntologyConfig(BaseModel):
    """Konfiguration für die Wissensgraph-Ontologie."""
    node_types: List[str] = ["Person", "Modul", "Unternehmen"]
    edge_types: List[str] = ["lehrt", "besucht"]
    edge_priorities: Dict[str, List[str]] = {}

class UserConfig(BaseModel):
    """Konfiguration für den Nutzer des Tools."""
    name: str = "Daniel Gaida"
    email: Union[str, List[str]] = "daniel.gaida@th-koeln.de"
    emails: List[str] = []

    @model_validator(mode="before")
    @classmethod
    def handle_email_list(cls, data: Any) -> Any:
        """Behandelt den Fall, dass 'email' als Liste angegeben wurde."""
        if isinstance(data, dict):
            email_val = data.get("email")
            if isinstance(email_val, list):
                if not data.get("emails"):
                    data["emails"] = email_val
                data["email"] = email_val[0] if email_val else ""
        return data

class Config:
    """Zentrale Konfigurationsklasse für das MCP University System.

    Lädt Einstellungen aus YAML-Dateien im 'config/'-Verzeichnis.
    """

    def __init__(self, config_dir: Path = None) -> None:
        """Initialisiert die Konfiguration.

        Args:
            config_dir (Path, optional): Pfad zum Konfigurationsverzeichnis. Defaults to None.
        """
        if config_dir is None:
            config_dir = Path(__file__).resolve().parent.parent / "config"

        self.config_dir = config_dir
        # Umgebungsvariablen aus .env oder secrets.env laden
        load_dotenv(self.config_dir.parent / ".env")
        load_dotenv(self.config_dir.parent / "secrets.env")
        load_dotenv(self.config_dir / ".env")
        load_dotenv(self.config_dir / "secrets.env")
        self.folders = self._load_yaml(config_dir / "folders.yaml", FolderConfig)
        self.user = self._load_yaml(config_dir / "user.yaml", UserConfig)
        if not self.user.emails:
            self.user.emails = [self.user.email]
        self._sync_vba_macros()
        self.ontology = self._load_yaml(config_dir / "ontology.yaml", OntologyConfig)

        models_data = self._load_raw_yaml(config_dir / "models.yaml")
        self.calendar = CalendarConfig(**models_data.get("calendar", {}))
        self.llm = LLMConfig(**models_data.get("llm", {}))
        self.embeddings = EmbeddingConfig(**models_data.get("embeddings", {}))
        self.reranker = RerankerConfig(**models_data.get("reranker", {}))

    def _sync_vba_macros(self) -> None:
        """Synchronisiert das VBA-Konto in den .bas Dateien mit der Benutzerkonfiguration."""
        try:
            macro_dir = self.config_dir.parent / "outlook_macro"
            if not macro_dir.exists():
                return

            user_email = self.user.email
            if not user_email:
                return

            import re
            pattern = re.compile(
                r'(Private\s+Const\s+ACCOUNT_NAME\s+(?:As\s+String\s+)?=\s*")[^"]*(")',
                re.IGNORECASE
            )

            for bas_file in macro_dir.glob("*.bas"):
                try:
                    content = bas_file.read_text(encoding="utf-8", errors="replace")
                    if pattern.search(content):
                        new_content = pattern.sub(r'\g<1>' + user_email + r'\g<2>', content)
                        if new_content != content:
                            bas_file.write_text(new_content, encoding="utf-8")
                except Exception:
                    pass
        except Exception:
            pass

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
    def th_personal_path(self) -> Path:
        """Gibt den Pfad zur TH-Personal-Datenbank zurück.

        Returns:
            Path: DB-Pfad.
        """
        return self.data_dir / "metadata" / "th_personal.db"

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

    @property
    def offline(self) -> bool:
        """Prüft, ob das System im Offline-Modus betrieben wird.

        Wird über die Umgebungsvariable 'MCP_UNIVERSITY_OFFLINE' gesteuert.
        Falls True, werden auch HF_HUB_OFFLINE und TRANSFORMERS_OFFLINE gesetzt.

        Returns:
            bool: True, wenn Offline-Modus aktiv.
        """
        is_offline = os.environ.get("MCP_UNIVERSITY_OFFLINE", "0").lower() in ("1", "true", "yes")
        if is_offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        return is_offline

def get_config() -> Config:
    """Singleton-ähnlicher Zugriff auf die Systemkonfiguration.

    Returns:
        Config: Die aktuelle Konfiguration.
    """
    return Config()
