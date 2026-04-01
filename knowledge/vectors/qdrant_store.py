import structlog
import uuid
from dataclasses import asdict
from typing import Any

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from config import settings
from ingestion.chunkers.semantic_chunker import RegulatoryChunk
from knowledge.embeddings.vertex_embeddings import VertexEmbedder, get_langchain_embeddings

logger = structlog.get_logger()


class RegulatoryVectorStore:
    """
    Qdrant vector store for regulatory document chunks.
    Supports pre-search metadata filtering (jurisdiction, date, regulator).
    """

    COLLECTION_NAME = settings.qdrant_collection_name

    def __init__(self):
        self._client = QdrantClient(
            host=settings.qdrant_host, port=settings.qdrant_port
        )
        self._embedder = VertexEmbedder()
        self._lc_embeddings = get_langchain_embeddings()
        self._ensure_collection()

    def _ensure_collection(self):
        collections = [c.name for c in self._client.get_collections().collections]
        if self.COLLECTION_NAME not in collections:
            self._client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=qdrant_models.VectorParams(
                    size=settings.embedding_dimensions,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            # Create payload indexes for pre-search filtering
            for field in ["jurisdiction", "regulatory_body", "document_type", "source_id"]:
                self._client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field,
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
                )
            self._client.create_payload_index(
                collection_name=self.COLLECTION_NAME,
                field_name="published_date",
                field_schema=qdrant_models.PayloadSchemaType.FLOAT,
            )
            logger.info("qdrant_collection_created", name=self.COLLECTION_NAME)

    def upsert_chunks(self, chunks: list[RegulatoryChunk], doc_metadata: dict) -> int:
        """Embed and upsert regulatory chunks. Returns count of upserted chunks."""
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_batch(texts, task_type="RETRIEVAL_DOCUMENT")

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            payload = {
                "text": chunk.text,
                "section_title": chunk.section_title,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "word_count": chunk.word_count,
                **doc_metadata,
                **chunk.metadata,
            }
            points.append(qdrant_models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload,
            ))

        self._client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
            wait=True,
        )
        logger.info("chunks_upserted", count=len(points), source_id=doc_metadata.get("source_id"))
        return len(points)

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        """
        Semantic search with pre-search metadata filtering.
        filters: e.g. {"jurisdiction": "EU", "regulatory_body": "European Commission"}
        """
        query_vector = self._embedder.embed_query(query)
        qdrant_filter = self._build_filter(filters) if filters else None

        results = self._client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
        ).points
        return [{"score": r.score, **r.payload} for r in results]

    def get_langchain_store(self) -> QdrantVectorStore:
        """Returns LangChain-compatible vector store for use in LangChain chains."""
        return QdrantVectorStore(
            client=self._client,
            collection_name=self.COLLECTION_NAME,
            embedding=self._lc_embeddings,
        )

    def check_duplicate(self, chunk_id: str) -> bool:
        """Returns True if chunk already exists (deduplication)."""
        result = self._client.scroll(
            collection_name=self.COLLECTION_NAME,
            scroll_filter=qdrant_models.Filter(
                must=[qdrant_models.FieldCondition(
                    key="chunk_id",
                    match=qdrant_models.MatchValue(value=chunk_id),
                )]
            ),
            limit=1,
        )
        return len(result[0]) > 0

    def _build_filter(self, filters: dict) -> qdrant_models.Filter:
        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(qdrant_models.FieldCondition(
                    key=key,
                    match=qdrant_models.MatchAny(any=value),
                ))
            else:
                conditions.append(qdrant_models.FieldCondition(
                    key=key,
                    match=qdrant_models.MatchValue(value=value),
                ))
        return qdrant_models.Filter(must=conditions)
