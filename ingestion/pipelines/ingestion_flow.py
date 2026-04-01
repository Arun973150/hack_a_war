"""
Prefect Ingestion Pipeline — Layer 1 orchestration.
Fetches regulatory documents, parses, chunks, embeds, stores.
Scheduled to run every hour.
"""
import hashlib
import structlog
from datetime import datetime, timedelta

from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash

from ingestion.connectors.base import RawRegulatoryDocument
from ingestion.connectors.federal_register import FederalRegisterConnector
from ingestion.connectors.eur_lex import EurLexConnector
from ingestion.connectors.sebi import SEBIConnector
from ingestion.parsers.document_parser import DocumentParser
from ingestion.chunkers.semantic_chunker import SemanticChunker
from knowledge.vectors.qdrant_store import RegulatoryVectorStore
from knowledge.graph.neo4j_client import Neo4jClient
from knowledge.graph.triplet_extractor import TripletExtractor
from storage.supabase_client import SupabaseStorageClient
from agents.graph import ComplianceOrchestrator

logger = structlog.get_logger()


# ─── Tasks ───────────────────────────────────────────────────────────────────

@task(retries=3, retry_delay_seconds=60, cache_key_fn=task_input_hash)
def fetch_from_source(source_name: str, since_hours: int = 24) -> list[dict]:
    """Fetch recent documents from a regulatory source."""
    pf_logger = get_run_logger()
    since = datetime.utcnow() - timedelta(hours=since_hours)

    connector_map = {
        "federal_register": FederalRegisterConnector,
        "eur_lex": EurLexConnector,
        "sebi": SEBIConnector,
    }

    ConnectorClass = connector_map.get(source_name)
    if not ConnectorClass:
        raise ValueError(f"Unknown source: {source_name}")

    connector = ConnectorClass()

    import asyncio

    async def _fetch():
        docs = []
        async for doc in connector.fetch_recent(since):
            docs.append(doc)
            pf_logger.info(f"Fetched: {doc.title[:60]}")
        return docs

    docs = asyncio.run(_fetch())
    pf_logger.info(f"Fetched {len(docs)} documents from {source_name}")

    # Serialize for Prefect (can't pass raw bytes through task boundaries)
    return [
        {
            "source_id": d.source_id,
            "source_url": d.source_url,
            "title": d.title,
            "jurisdiction": d.jurisdiction.value,
            "regulatory_body": d.regulatory_body,
            "document_type": d.document_type.value,
            "published_date": d.published_date.isoformat(),
            "raw_content": d.raw_content.hex(),   # hex-encode bytes
            "content_type": d.content_type,
            "metadata": d.metadata,
        }
        for d in docs
    ]


@task(retries=2)
def parse_and_chunk_document(doc_dict: dict) -> dict:
    """Parse document bytes and chunk into regulatory-aware pieces."""
    parser = DocumentParser()
    chunker = SemanticChunker()

    raw_content = bytes.fromhex(doc_dict["raw_content"])
    parsed = parser.parse(raw_content, doc_dict["content_type"], doc_dict["source_id"])

    doc_metadata = {
        "source_id": doc_dict["source_id"],
        "source_url": doc_dict["source_url"],
        "jurisdiction": doc_dict["jurisdiction"],
        "regulatory_body": doc_dict["regulatory_body"],
        "document_type": doc_dict["document_type"],
        "published_date": doc_dict["published_date"],
        "title": doc_dict["title"],
    }

    chunks = chunker.chunk(parsed, doc_metadata)

    return {
        "doc_metadata": doc_metadata,
        "parsed_text": parsed.text,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "section_title": c.section_title,
                "chunk_index": c.chunk_index,
                "total_chunks": c.total_chunks,
                "word_count": c.word_count,
                "metadata": c.metadata,
            }
            for c in chunks
        ],
    }


@task(retries=2)
def store_to_vector_db(processed: dict) -> int:
    """Embed chunks and store in Qdrant."""
    from ingestion.chunkers.semantic_chunker import RegulatoryChunk

    vector_store = RegulatoryVectorStore()
    chunks = [
        RegulatoryChunk(
            chunk_id=c["chunk_id"],
            text=c["text"],
            section_title=c["section_title"],
            chunk_index=c["chunk_index"],
            total_chunks=c["total_chunks"],
            word_count=c["word_count"],
            metadata=c["metadata"],
        )
        for c in processed["chunks"]
    ]

    count = vector_store.upsert_chunks(chunks, processed["doc_metadata"])
    return count


@task(retries=2)
def store_to_knowledge_graph(processed: dict) -> str:
    """Extract SPO triplets and store in Neo4j."""
    neo4j = Neo4jClient()
    extractor = TripletExtractor()

    # Upsert regulation node
    meta = processed["doc_metadata"]
    reg_id = neo4j.upsert_regulation({
        "id": meta["source_id"],
        "title": meta["title"],
        "jurisdiction": meta["jurisdiction"],
        "regulatory_body": meta["regulatory_body"],
        "document_type": meta["document_type"],
        "published_date": meta["published_date"],
        "effective_date": meta.get("effective_date", ""),
        "source_url": meta["source_url"],
        "summary": processed["parsed_text"][:500],
    })

    # Extract and store triplets from chunked text
    chunk_texts = [c["text"] for c in processed["chunks"][:10]]  # limit for cost
    triplets = extractor.extract_batch(chunk_texts, regulation_id=reg_id)

    logger.info("triplets_stored", count=len(triplets), regulation_id=reg_id)
    return reg_id


@task(retries=1)
def store_raw_to_supabase(doc_dict: dict) -> str:
    """Store original document bytes in Supabase Storage for audit trail."""
    storage = SupabaseStorageClient()
    raw_content = bytes.fromhex(doc_dict["raw_content"])
    path = storage.store_document(
        content=raw_content,
        content_type=doc_dict["content_type"],
        source_id=doc_dict["source_id"],
        jurisdiction=doc_dict["jurisdiction"],
    )
    return path


@task
def trigger_compliance_analysis(doc_dict: dict, parsed_text: str) -> dict:
    """Trigger the 5-agent LangGraph pipeline for compliance analysis."""
    orchestrator = ComplianceOrchestrator()
    result = orchestrator.process_document(
        document_id=doc_dict["source_id"],
        raw_text=parsed_text,
        source_url=doc_dict["source_url"],
        jurisdiction=doc_dict["jurisdiction"],
        regulatory_body=doc_dict["regulatory_body"],
        document_type=doc_dict["document_type"],
        published_date=doc_dict["published_date"],
    )
    return {
        "is_relevant": result.is_relevant,
        "action_items_count": len(result.action_items),
        "risk_score": result.overall_risk_score,
        "valid": result.validation.valid if result.validation else None,
    }


# ─── Main Flow ───────────────────────────────────────────────────────────────

@flow(
    name="regulatory-ingestion-pipeline",
    description="Fetch, parse, store, and analyze regulatory documents",
)
def regulatory_ingestion_flow(
    sources: list[str] | None = None,
    since_hours: int = 24,
    run_analysis: bool = True,
):
    """
    Main Prefect flow — orchestrates the full ingestion pipeline.
    Scheduled to run every hour via Prefect deployment.
    """
    pf_logger = get_run_logger()

    if sources is None:
        sources = ["federal_register", "eur_lex", "sebi"]

    pf_logger.info(f"Starting ingestion for sources: {sources}")

    all_results = []

    for source in sources:
        # Fetch documents from source
        raw_docs = fetch_from_source(source, since_hours)
        pf_logger.info(f"{source}: fetched {len(raw_docs)} documents")

        for doc_dict in raw_docs:
            # Parse + chunk
            processed = parse_and_chunk_document(doc_dict)

            # Store in parallel: vector DB, KG, MinIO
            vector_count = store_to_vector_db(processed)
            regulation_id = store_to_knowledge_graph(processed)
            minio_path = store_raw_to_supabase(doc_dict)

            # Trigger LangGraph analysis if enabled
            analysis_result = None
            if run_analysis:
                analysis_result = trigger_compliance_analysis(
                    doc_dict, processed["parsed_text"]
                )

            all_results.append({
                "source": source,
                "source_id": doc_dict["source_id"],
                "title": doc_dict["title"],
                "chunks_stored": vector_count,
                "regulation_id": regulation_id,
                "minio_path": minio_path,
                "analysis": analysis_result,
            })

    pf_logger.info(f"Ingestion complete. Processed {len(all_results)} documents.")
    return all_results


if __name__ == "__main__":
    regulatory_ingestion_flow()
