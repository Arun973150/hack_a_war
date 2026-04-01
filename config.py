from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Google Vertex AI
    vertex_project: str = "redforge"
    vertex_location: str = "us-central1"
    google_application_credentials: str = "./service-account.json"

    # Gemini Models
    gemini_flash_lite_model: str = "gemini-2.0-flash-lite"
    vertex_model: str = "gemini-2.0-flash"          # default model from .env
    gemini_flash_model: str = "gemini-2.0-flash"
    gemini_pro_model: str = "gemini-2.5-pro"
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "regulatory_docs"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "redforge_neo4j_password"

    # Supabase (PostgreSQL + Storage)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket_regulatory_docs: str = "regulatory-docs"
    supabase_bucket_processed: str = "processed-docs"

    # PostgreSQL via Supabase
    database_url: str = ""   # filled from supabase_url at runtime

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "red-forge-compliance"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-in-production"
    api_key: str = ""   # Set in .env — if empty, auth is disabled (dev mode)

    # Jira
    jira_base_url: str = ""
    jira_api_token: str = ""
    jira_email: str = ""
    jira_project_key: str = "COMP"

    # Slack
    slack_webhook_url: str = ""

    # Email (Gmail SMTP)
    smtp_sender_email: str = ""
    smtp_app_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
