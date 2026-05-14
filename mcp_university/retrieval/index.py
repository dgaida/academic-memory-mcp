"""Schnittstelle zum Qdrant-basierten Suchindex."""
import logging
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

class SearchIndex:
    """Schnittstelle zum hybriden Suchindex (Qdrant + BM25).

    Ermöglicht die hybride Suche (semantisch und Schlüsselwort) über die Dokumentensammlung.
    """

    def __init__(self, location: str, embedding_model_name: str = "BAAI/bge-m3"):
        """Initialisiert den SearchIndex.

        Args:
            location (str): Pfad zum Speicherort des Index.
            embedding_model_name (str): Name des Embedding-Modells.
        """
        self.location = Path(location)
        self.location.mkdir(parents=True, exist_ok=True)

        self.client = QdrantClient(path=str(self.location))
        self.collection_name = "university_documents"
        self.model = SentenceTransformer(embedding_model_name)

        self.bm25_path = self.location / "bm25_index.pkl"
        self.corpus_path = self.location / "corpus.json"

        self._ensure_collection()
        self._load_bm25()

    def _ensure_collection(self) -> None:
        """Stellt sicher, dass die Qdrant-Collection existiert."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            # Get dimension from model
            dummy_vector = self.model.encode("dummy")
            vector_size = len(dummy_vector)

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )

    def _load_bm25(self) -> None:
        """Lädt den BM25-Index und den Corpus."""
        self.corpus = []
        self.bm25 = None

        if self.corpus_path.exists():
            with open(self.corpus_path, "r", encoding="utf-8") as f:
                self.corpus = json.load(f)

            if self.bm25_path.exists():
                with open(self.bm25_path, "rb") as f:
                    self.bm25 = pickle.load(f)
            else:
                self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        """Baut den BM25-Index neu auf."""
        if not self.corpus:
            self.bm25 = None
            return

        tokenized_corpus = [doc["content"].lower().split() for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

        with open(self.bm25_path, "wb") as f:
            pickle.dump(self.bm25, f)

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Fügt ein Dokument zum Index hinzu.

        Args:
            doc_id (str): Eindeutige ID (Pfad).
            content (str): Textinhalt.
            metadata (Dict[str, Any]): Metadaten.
        """
        # 1. Dense Vector
        vector = self.model.encode(content).tolist()

        import hashlib
        # Stable numeric ID from path
        doc_hash = int(hashlib.md5(doc_id.encode()).hexdigest(), 16) % (2**63 - 1)

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=doc_hash,
                    vector=vector,
                    payload={
                        "doc_id": doc_id,
                        "content": content,
                        **metadata
                    }
                )
            ]
        )

        # 2. Update BM25 Corpus
        # Remove existing if present (simple list management for local scale)
        self.corpus = [doc for doc in self.corpus if doc["doc_id"] != doc_id]
        self.corpus.append({
            "doc_id": doc_id,
            "content": content,
            "metadata": metadata
        })

        with open(self.corpus_path, "w", encoding="utf-8") as f:
            json.dump(self.corpus, f, ensure_ascii=False, indent=2)

        self._rebuild_bm25()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Führt eine hybride Suche im Index aus.

        Args:
            query (str): Die Suchanfrage.
            top_k (int): Anzahl der Ergebnisse.

        Returns:
            List[Dict[str, Any]]: Suchergebnisse.
        """
        # 1. Dense Search (Semantic)
        query_vector = self.model.encode(query).tolist()

        # Using query_points as per recommendation for v1.11+
        dense_results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k * 2
        ).points

        # 2. BM25 Search (Keyword)
        keyword_results = []
        if self.bm25:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            top_n = np.argsort(scores)[::-1][:top_k * 2]

            for idx in top_n:
                if scores[idx] > 0:
                    doc = self.corpus[idx]
                    keyword_results.append({
                        "path": doc["doc_id"],
                        "content": doc["content"],
                        "score": float(scores[idx]),
                        "metadata": doc["metadata"],
                        "filename": doc["metadata"].get("filename", "")
                    })

        # 3. Hybrid Reranking (Simple Reciprocal Rank Fusion approach or basic normalization)
        # For simplicity and given local scale, we merge and deduplicate
        results_map = {}

        # Process Dense
        for res in dense_results:
            path = res.payload["doc_id"]
            results_map[path] = {
                "path": path,
                "content": res.payload["content"],
                "filename": res.payload.get("filename", ""),
                "score": res.score,
                "metadata": res.payload
            }

        # Process Keywords (merge and boost score if in both)
        for res in keyword_results:
            path = res["path"]
            if path in results_map:
                results_map[path]["score"] += res["score"] * 0.1 # Small boost for keyword match
            else:
                results_map[path] = res

        # Sort and limit
        sorted_results = sorted(results_map.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results[:top_k]
