from fastapi import APIRouter
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
import structlog

from config import settings

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "ok", "service": "red-forge-api"}


@router.get("/deep")
async def deep_health_check():
    """Check connectivity to all dependent services."""
    results = {}

    # Qdrant
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collections()
        results["qdrant"] = "ok"
    except Exception as e:
        results["qdrant"] = f"error: {str(e)}"

    # Neo4j (Aura Cloud)
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        with driver.session() as s:
            s.run("RETURN 1")
        driver.close()
        results["neo4j"] = "ok"
    except Exception as e:
        results["neo4j"] = f"error: {str(e)}"

    # Supabase PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        results["supabase_postgres"] = "ok"
    except Exception as e:
        results["supabase_postgres"] = f"error: {str(e)}"

    # Redis
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        results["redis"] = "ok"
    except Exception as e:
        results["redis"] = f"error: {str(e)}"

    overall = "ok" if all(v == "ok" for v in results.values()) else "degraded"
    return {"status": overall, "services": results}
