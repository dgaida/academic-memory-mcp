import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import numpy as np

logger = logging.getLogger(__name__)

class SearchIndex:
    def __init__(self, location: str, embedding_model_name: str = "BAAI/bge-m3"):
        self.client = QdrantClient(path=location)
        self.collection_name = "university_docs"
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self._ensure_collection()

        # BM25 state
        self.bm25: Optional[BM25Okapi] = None
        self.bm25_docs: List[Dict[str, Any]] = []

    def _ensure_collection(self):
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
                )
        except Exception:
            # Fallback for older versions
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 50]
        if not chunks and content.strip():
            chunks = [content.strip()]

        points = []
        for i, chunk in enumerate(chunks):
            vector = self.embedding_model.encode(chunk).tolist()
            point_id = hash(f"{doc_id}_{i}") % (2**63)
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "doc_id": doc_id,
                    "content": chunk,
                    "chunk_index": i,
                    **metadata
                }
            ))
            self.bm25_docs.append({
                "doc_id": doc_id,
                "content": chunk,
                "tokens": chunk.lower().split(),
                **metadata
            })

        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            self._update_bm25()

    def _update_bm25(self):
        corpus = [d["tokens"] for d in self.bm25_docs]
        if corpus:
            self.bm25 = BM25Okapi(corpus)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.embedding_model.encode(query).tolist()

        # Using query_points as search is not found in this version's QdrantClient
        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k
            )
            dense_results = [p.payload for p in response.points]
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            dense_results = []

        bm25_results = []
        if self.bm25:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            top_n = np.argsort(scores)[::-1][:top_k]
            for idx in top_n:
                if scores[idx] > 0:
                    bm25_results.append(self.bm25_docs[idx])

        combined = []
        seen_contents = set()

        for payload in dense_results:
            combined.append(payload)
            seen_contents.add(payload["content"])

        for res in bm25_results:
            if res["content"] not in seen_contents:
                combined.append(res)

        return combined[:top_k]
