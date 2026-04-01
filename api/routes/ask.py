from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import structlog

from config import settings
from knowledge.graph.neo4j_client import Neo4jClient
from knowledge.vectors.qdrant_store import QdrantStore

logger = structlog.get_logger()
router = APIRouter()


class AskRequest(BaseModel):
    question: str
    jurisdiction: Optional[str] = None


@router.post("/")
async def ask_question(request: AskRequest):
    """
    RAG-based Q&A over regulations, controls, and policies.
    Searches Qdrant for relevant chunks, queries Neo4j for related controls,
    then uses Gemini to synthesise an answer with sources.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(400, "Question must not be empty")

    # ── Step 1: Semantic search in Qdrant ────────────────────────────────
    vector_results = []
    try:
        store = QdrantStore()
        vector_results = store.search(question, limit=5)
    except Exception as e:
        logger.error("ask_qdrant_search_failed", error=str(e))
        # Continue without vector results — Neo4j may still provide context

    # ── Step 2: Query Neo4j for related controls and obligations ─────────
    neo4j_controls = []
    neo4j_obligations = []
    try:
        neo4j = Neo4jClient()

        # Find obligations whose text matches keywords from the question
        obligation_query = """
        MATCH (r:Regulation)-[:REQUIRES]->(o:Obligation)
        WHERE toLower(o.what) CONTAINS toLower($keyword)
        """
        params = {"keyword": question.split()[0] if question.split() else question}

        if request.jurisdiction:
            obligation_query += " AND toLower(r.jurisdiction) = toLower($jurisdiction)\n"
            params["jurisdiction"] = request.jurisdiction

        obligation_query += """
        RETURN o.id AS obligation_id,
               o.what AS requirement,
               r.title AS regulation_title,
               r.jurisdiction AS jurisdiction
        LIMIT 5
        """
        neo4j_obligations = neo4j.run_cypher(obligation_query, params)

        # Find controls related to those obligations
        control_query = """
        MATCH (c:ComplianceControl)-[addr:ADDRESSES]->(o:Obligation)
        WHERE toLower(o.what) CONTAINS toLower($keyword)
        RETURN c.id AS control_id,
               c.name AS control_name,
               c.framework AS framework,
               c.coverage_score AS coverage_score,
               addr.coverage_pct AS coverage_pct,
               o.id AS obligation_id
        LIMIT 10
        """
        neo4j_controls = neo4j.run_cypher(control_query, {"keyword": params["keyword"]})
    except Exception as e:
        logger.error("ask_neo4j_query_failed", error=str(e))

    # ── Step 3: Build context for the LLM ────────────────────────────────
    context_parts = []

    if vector_results:
        context_parts.append("=== Relevant Regulation Excerpts ===")
        for i, vr in enumerate(vector_results, 1):
            text = vr.get("text", "")
            metadata = vr.get("metadata", {})
            source = metadata.get("source_id", "unknown")
            context_parts.append(f"[Source {i}: {source}] {text}")

    if neo4j_obligations:
        context_parts.append("\n=== Related Regulatory Obligations ===")
        for ob in neo4j_obligations:
            context_parts.append(
                f"- [{ob.get('regulation_title', 'N/A')} / {ob.get('jurisdiction', 'N/A')}] "
                f"{ob.get('requirement', '')}"
            )

    if neo4j_controls:
        context_parts.append("\n=== Related Compliance Controls ===")
        for ctrl in neo4j_controls:
            coverage = ctrl.get("coverage_score")
            coverage_str = f"{float(coverage) * 100:.0f}%" if coverage is not None else "N/A"
            context_parts.append(
                f"- {ctrl.get('control_name', 'N/A')} "
                f"(framework: {ctrl.get('framework', 'N/A')}, coverage: {coverage_str})"
            )

    context_text = "\n".join(context_parts) if context_parts else "No relevant context found."

    # ── Step 4: Call Gemini via LangChain ChatVertexAI ────────────────────
    try:
        from langchain_google_vertexai import ChatVertexAI
        from langchain_core.prompts import ChatPromptTemplate

        llm = ChatVertexAI(
            model_name=settings.gemini_flash_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0.1,
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are Red Forge, a compliance intelligence assistant. "
                "Answer the user's question based ONLY on the provided context. "
                "If the context does not contain enough information, say so clearly. "
                "Cite sources where possible. Be concise and actionable.",
            ),
            (
                "human",
                "Context:\n{context}\n\nQuestion: {question}",
            ),
        ])

        chain = prompt | llm
        response = chain.invoke({"context": context_text, "question": question})
        answer = response.content
    except Exception as e:
        logger.error("ask_vertex_ai_failed", error=str(e))
        return {
            "answer": None,
            "error": f"AI service unavailable: {str(e)}",
            "sources": [
                {
                    "text": vr.get("text", "")[:200],
                    "score": vr.get("score", 0),
                    "source_id": vr.get("metadata", {}).get("source_id", "unknown"),
                }
                for vr in vector_results
            ],
            "controls_referenced": [
                ctrl.get("control_id") for ctrl in neo4j_controls
            ],
        }

    # ── Step 5: Build response ───────────────────────────────────────────
    sources = [
        {
            "text": vr.get("text", "")[:200],
            "score": vr.get("score", 0),
            "source_id": vr.get("metadata", {}).get("source_id", "unknown"),
        }
        for vr in vector_results
    ]

    controls_referenced = list({
        ctrl.get("control_id") for ctrl in neo4j_controls if ctrl.get("control_id")
    })

    return {
        "answer": answer,
        "sources": sources,
        "controls_referenced": controls_referenced,
    }
