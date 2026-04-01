"""
Database connection via Supabase PostgreSQL.
Used by SQLAlchemy (org_context models) and LangGraph checkpointer.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from supabase import create_client

from config import settings


def get_database_url() -> str:
    """
    Build PostgreSQL connection string from Supabase URL.
    Supabase URL format: https://<project-ref>.supabase.co
    PostgreSQL format:   postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
    """
    if settings.database_url:
        return settings.database_url

    # Auto-derive from supabase_url
    project_ref = settings.supabase_url.replace("https://", "").split(".")[0]
    return (
        f"postgresql://postgres:{settings.supabase_service_role_key}"
        f"@db.{project_ref}.supabase.co:5432/postgres"
    )


def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


def get_session() -> Session:
    SessionLocal = sessionmaker(bind=get_engine())
    return SessionLocal()


def get_supabase_client():
    """Direct Supabase client for REST API operations."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
