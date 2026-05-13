import os
from pathlib import Path
from typing import List, Dict, Any
import yaml
from pydantic import BaseModel, Field

class LLMConfig(BaseModel):
    model: str = "gemma2:2b"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434"

class EmbeddingConfig(BaseModel):
    model: str = "BAAI/bge-m3"

class RerankerConfig(BaseModel):
    model: str = "BAAI/bge-reranker-v2-m3"

class FolderConfig(BaseModel):
    folders: List[str] = []
    exclude_patterns: List[str] = [".git", "node_modules", "*.tmp", "*.bak"]
    supported_extensions: List[str] = [".pdf", ".docx", ".md", ".txt", ".eml", ".msg", ".py", ".ipynb", ".json", ".html"]

class Config:
    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            # Try to find config dir relative to this file
            config_dir = Path(__file__).resolve().parent.parent / "config"

        self.config_dir = config_dir
        self.folders = self._load_yaml(config_dir / "folders.yaml", FolderConfig)

        models_data = self._load_raw_yaml(config_dir / "models.yaml")
        self.llm = LLMConfig(**models_data.get("llm", {}))
        self.embeddings = EmbeddingConfig(**models_data.get("embeddings", {}))
        self.reranker = RerankerConfig(**models_data.get("reranker", {}))

    def _load_yaml(self, path: Path, model_class):
        if not path.exists():
            return model_class()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return model_class(**data) if data else model_class()

    def _load_raw_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def data_dir(self) -> Path:
        return self.config_dir.parent / "data"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "metadata" / "university.db"

    @property
    def qdrant_path(self) -> Path:
        return self.data_dir / "indexes" / "qdrant"

def get_config() -> Config:
    return Config()
