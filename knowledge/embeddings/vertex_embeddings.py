import structlog
from functools import lru_cache
from typing import Literal

import vertexai
from langchain_google_vertexai import VertexAIEmbeddings
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from config import settings

logger = structlog.get_logger()

TaskType = Literal[
    "RETRIEVAL_DOCUMENT",
    "RETRIEVAL_QUERY",
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION",
]


class VertexEmbedder:
    """
    Vertex AI text-embedding-004 wrapper.
    Supports task-type hints for asymmetric retrieval
    (documents stored with RETRIEVAL_DOCUMENT, queries use RETRIEVAL_QUERY).
    """

    def __init__(self):
        vertexai.init(
            project=settings.vertex_project,
            location=settings.vertex_location,
        )
        self._model = TextEmbeddingModel.from_pretrained(settings.embedding_model)
        self._dimensions = settings.embedding_dimensions

    def embed_document(self, text: str) -> list[float]:
        """Embed a regulatory document chunk for storage."""
        return self._embed(text, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query for retrieval."""
        return self._embed(text, task_type="RETRIEVAL_QUERY")

    def embed_batch(
        self, texts: list[str], task_type: TaskType = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Embed a batch of texts (max 250 per call per Vertex AI limits)."""
        results = []
        batch_size = 250

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = [TextEmbeddingInput(text, task_type) for text in batch]
            embeddings = self._model.get_embeddings(
                inputs, output_dimensionality=self._dimensions
            )
            results.extend([e.values for e in embeddings])
            logger.debug("batch_embedded", batch_start=i, batch_size=len(batch))

        return results

    def _embed(self, text: str, task_type: TaskType) -> list[float]:
        inputs = [TextEmbeddingInput(text, task_type)]
        embeddings = self._model.get_embeddings(
            inputs, output_dimensionality=self._dimensions
        )
        return embeddings[0].values


def get_langchain_embeddings() -> VertexAIEmbeddings:
    """
    Returns LangChain-compatible VertexAIEmbeddings instance.
    Used by LangChain's Qdrant vector store integration.
    """
    vertexai.init(
        project=settings.vertex_project,
        location=settings.vertex_location,
    )
    return VertexAIEmbeddings(
        model_name=settings.embedding_model,
        project=settings.vertex_project,
        location=settings.vertex_location,
    )
