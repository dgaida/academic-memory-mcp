"""Semantische E-Mail-Suche mittels Ollama-Embedding-Modell und Qdrant-Vektordatenbank.

Dieses Modul stellt einen persistenten Vektorindex für E-Mails bereit und
ermöglicht eine schnelle semantische Ähnlichkeitssuche auf Basis des
``embeddinggemma-2:270m``-Modells via Ollama.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from mcp_university.config import get_config

logger = logging.getLogger(__name__)

DEFAULT_SEMANTIC_MODEL = "embeddinggemma-2:270m"
COLLECTION_NAME = "email_semantic_index"
_VECTOR_STORE_DIR_NAME = "semantic_email_index"


def _doc_id_to_int(doc_id: str) -> int:
    """Wandelt eine beliebige Zeichenkette in eine positive 63-Bit-Ganzzahl um.

    Args:
        doc_id (str): Eindeutige Dokumenten-ID (z. B. Dateipfad).

    Returns:
        int: Positive 63-Bit-Ganzzahl als Qdrant-Point-ID.
    """
    return int(hashlib.md5(doc_id.encode()).hexdigest(), 16) % (2**63 - 1)


class SemanticEmailSearchEngine:
    """Semantische Suchmaschine für E-Mails auf Basis von Ollama-Embeddings und Qdrant.

    Hält einen Qdrant-In-Process-Store am Speicherort ``data/semantic_email_index/``.
    Embeddings werden über ``ollama.Client.embed`` mit dem Modell
    ``embeddinggemma-2:270m`` erzeugt.
    """

    def __init__(
        self,
        store_dir: Optional[Path] = None,
        embedding_model: str = DEFAULT_SEMANTIC_MODEL,
        ollama_base_url: Optional[str] = None,
        batch_size: int = 32,
    ) -> None:
        """Initialisiert die semantische Such-Engine.

        Args:
            store_dir (Optional[Path]): Pfad zum Qdrant-Speicherverzeichnis.
                Defaults to ``data/semantic_email_index/``.
            embedding_model (str): Ollama-Modellname. Defaults to
                ``embeddinggemma-2:270m``.
            ollama_base_url (Optional[str]): Basis-URL des Ollama-Servers.
                Defaults to dem in ``models.yaml`` konfigurierten Wert.
            batch_size (int): Anzahl Texte pro Ollama-Anfrage.
        """
        self.config = get_config()
        if store_dir is None:
            store_dir = self.config.data_dir / _VECTOR_STORE_DIR_NAME
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self.embedding_model = embedding_model
        self.ollama_base_url = ollama_base_url or str(self.config.llm.base_url)
        self.batch_size = batch_size

        # Lazy-loaded Qdrant client
        self._client: Optional[Any] = None
        self._embedding_dim: Optional[int] = None

        # Metadaten-Store (Pfad → Metadaten) für Offline-Lesezugriff
        self._meta_path = self.store_dir / "meta.json"
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._load_meta()

    # ------------------------------------------------------------------
    # Persistenz-Hilfsmethoden
    # ------------------------------------------------------------------

    def _load_meta(self) -> None:
        """Lädt den Metadaten-Store aus ``meta.json``.

        Returns:
            None
        """
        if self._meta_path.exists():
            try:
                with open(self._meta_path, "r", encoding="utf-8") as fh:
                    self._meta = json.load(fh)
                logger.info(f"Semantischer Index-Metadaten geladen: {len(self._meta)} Einträge.")
            except Exception as exc:
                logger.error(f"Fehler beim Laden der semantischen Metadaten: {exc}")
                self._meta = {}

    def _save_meta(self) -> None:
        """Speichert den Metadaten-Store atomar in ``meta.json``.

        Returns:
            None
        """
        try:
            tmp_path = self._meta_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(self._meta, fh, ensure_ascii=False, indent=2)
            tmp_path.replace(self._meta_path)
        except Exception as exc:
            logger.error(f"Fehler beim Speichern der semantischen Metadaten: {exc}")

    # ------------------------------------------------------------------
    # Qdrant-Zugriff
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Gibt den Qdrant-Client zurück und initialisiert ihn bei Bedarf.

        Returns:
            Any: Initialisierter QdrantClient.

        Raises:
            ImportError: Falls ``qdrant-client`` nicht installiert ist.
        """
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import QdrantClient  # type: ignore[import]
            self._client = QdrantClient(path=str(self.store_dir))
            logger.info(f"Qdrant-Client initialisiert: {self.store_dir}")
            self._ensure_collection()
        except ImportError:
            logger.error(
                "qdrant-client ist nicht installiert. "
                "Bitte mit 'pip install qdrant-client' nachinstallieren."
            )
            raise
        return self._client

    def _ensure_collection(self) -> None:
        """Stellt sicher, dass die Qdrant-Collection existiert.

        Erstellt die Collection mit korrekter Vektordimension, falls sie noch
        nicht vorhanden ist.

        Returns:
            None
        """
        from qdrant_client import models  # type: ignore[import]

        client = self._client
        if client is None:
            return

        collections = client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            embedding_dim = self._get_embedding_dim()
            logger.info(
                f"Erstelle Qdrant-Collection '{COLLECTION_NAME}' "
                f"mit Dimension {embedding_dim}."
            )
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=embedding_dim,
                    distance=models.Distance.COSINE,
                ),
            )

    def _get_embedding_dim(self) -> int:
        """Bestimmt die Embedding-Dimension einmalig per Probe-Embedding.

        Returns:
            int: Dimension des Embedding-Vektors.
        """
        if self._embedding_dim is not None:
            return self._embedding_dim
        probe = self._embed(["Probe"])[0]
        self._embedding_dim = len(probe)
        return self._embedding_dim

    # ------------------------------------------------------------------
    # Embedding-Erzeugung
    # ------------------------------------------------------------------

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Erzeugt Embeddings für eine Liste von Texten über Ollama.

        Args:
            texts (List[str]): Zu encodierende Texte.

        Returns:
            List[List[float]]: Liste von Embedding-Vektoren.

        Raises:
            Exception: Bei Kommunikationsfehler mit dem Ollama-Server.
        """
        import ollama  # type: ignore[import]

        client = ollama.Client(host=self.ollama_base_url)
        all_embeddings: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            try:
                response = client.embed(model=self.embedding_model, input=batch)
            except Exception as exc:
                logger.error(
                    f"Ollama-Embedding-Fehler für Modell '{self.embedding_model}' "
                    f"unter '{self.ollama_base_url}': {exc}"
                )
                raise
            embeddings = (
                response.embeddings
                if hasattr(response, "embeddings")
                else response["embeddings"]
            )
            all_embeddings.extend(embeddings)
        return all_embeddings

    # ------------------------------------------------------------------
    # Index-Verwaltung
    # ------------------------------------------------------------------

    @property
    def indexed_count(self) -> int:
        """Gibt die Anzahl der indizierten E-Mails zurück.

        Returns:
            int: Anzahl der Einträge im Metadaten-Store.
        """
        return len(self._meta)

    def is_indexed(self, doc_id: str) -> bool:
        """Prüft, ob ein Dokument bereits im semantischen Index enthalten ist.

        Args:
            doc_id (str): Eindeutige Dokument-ID (Dateipfad).

        Returns:
            bool: True, falls bereits indiziert.
        """
        return doc_id in self._meta

    def upsert_emails(self, emails: List[Dict[str, Any]]) -> None:
        """Fügt E-Mails zum Vektorindex hinzu oder aktualisiert bestehende.

        Jede E-Mail wird durch ``SUBJECT: … | FROM: … [SEP] …`` repräsentiert.
        Die Embeddings werden in Batches erzeugt und atomar nach Qdrant geschrieben.

        Args:
            emails (List[Dict[str, Any]]): Liste von E-Mail-Metadaten mit
                mindestens den Schlüsseln ``path``, ``subject``, ``from``,
                ``from_name`` und optional ``body_preview``.

        Returns:
            None
        """
        if not emails:
            return

        client = self._get_client()
        from qdrant_client import models  # type: ignore[import]

        texts = []
        for mail in emails:
            subject = mail.get("subject") or "(Kein Betreff)"
            from_name = mail.get("from_name") or mail.get("from") or ""
            body_preview = mail.get("body_preview") or ""
            text = f"SUBJECT: {subject} | FROM: {from_name} [SEP] {body_preview}"
            texts.append(text)

        logger.info(
            f"Erzeuge Embeddings für {len(texts)} E-Mails "
            f"mit Modell '{self.embedding_model}'…"
        )
        embeddings = self._embed(texts)

        points = []
        for mail, vector in zip(emails, embeddings):
            doc_id = mail.get("path", "")
            if not doc_id:
                continue
            point_id = _doc_id_to_int(doc_id)
            payload = {
                "doc_id": doc_id,
                "subject": mail.get("subject") or "",
                "from": mail.get("from") or "",
                "from_name": mail.get("from_name") or "",
                "date": mail.get("date") or "",
                "filename": mail.get("filename") or "",
                "folder": mail.get("folder") or "Inbox",
                "email_class": mail.get("email_class") or "",
            }
            points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))
            self._meta[doc_id] = payload

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        self._save_meta()
        logger.info(f"{len(points)} E-Mails erfolgreich in den semantischen Index aufgenommen.")

    def remove_missing(self, known_paths: List[str]) -> int:
        """Entfernt Einträge aus dem Index, die nicht mehr auf der Festplatte existieren.

        Args:
            known_paths (List[str]): Liste gültiger Dateipfade.

        Returns:
            int: Anzahl entfernter Einträge.
        """
        from qdrant_client import models  # type: ignore[import]

        known_set = set(known_paths)
        to_remove = [doc_id for doc_id in self._meta if doc_id not in known_set]
        if not to_remove:
            return 0

        client = self._get_client()
        point_ids = [_doc_id_to_int(doc_id) for doc_id in to_remove]
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(points=point_ids),
        )
        for doc_id in to_remove:
            del self._meta[doc_id]
        self._save_meta()
        logger.info(f"{len(to_remove)} veraltete Einträge aus dem semantischen Index entfernt.")
        return len(to_remove)

    # ------------------------------------------------------------------
    # Suche
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Führt eine semantische Suche über den Vektorindex aus.

        Args:
            query (str): Freier Suchbegriff.
            top_k (int): Maximale Anzahl zurückgegebener Ergebnisse.

        Returns:
            List[Dict[str, Any]]: Liste der ähnlichsten E-Mails mit
                Score und Metadaten, sortiert nach Score absteigend.
        """
        if not query:
            return []

        try:
            client = self._get_client()
        except Exception as exc:
            logger.error(f"Semantische Suche nicht verfügbar: {exc}")
            return []

        try:
            query_vector = self._embed([query])[0]
        except Exception as exc:
            logger.error(f"Fehler beim Erzeugen des Anfrage-Embeddings: {exc}")
            return []

        try:
            results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=top_k,
            )
            points = getattr(results, "points", results)
        except Exception as exc:
            logger.error(f"Qdrant-Suche fehlgeschlagen: {exc}")
            return []

        output = []
        for point in points:
            payload = point.payload or {}
            output.append({
                "path": payload.get("doc_id", ""),
                "subject": payload.get("subject", ""),
                "from": payload.get("from", ""),
                "from_name": payload.get("from_name", ""),
                "date": payload.get("date", ""),
                "filename": payload.get("filename", ""),
                "folder": payload.get("folder", "Inbox"),
                "email_class": payload.get("email_class", ""),
                "semantic_score": float(point.score),
            })
        return output
