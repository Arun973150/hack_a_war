"""
Supabase Storage client — replaces MinIO.
Handles raw regulatory document storage + retrieval.
Also exposes the Supabase PostgreSQL connection string.
"""
import io
import structlog
from datetime import datetime
from supabase import create_client, Client

from config import settings

logger = structlog.get_logger()


def get_supabase() -> Client:
    """Return authenticated Supabase client."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


class SupabaseStorageClient:
    """
    Supabase Storage client for regulatory documents.
    Replaces MinIO — same interface, cloud-hosted.
    """

    def __init__(self):
        self._client = get_supabase()
        self._ensure_buckets()

    def _ensure_buckets(self):
        existing = [b.name for b in self._client.storage.list_buckets()]
        for bucket in [
            settings.supabase_bucket_regulatory_docs,
            settings.supabase_bucket_processed,
        ]:
            if bucket not in existing:
                self._client.storage.create_bucket(
                    bucket,
                    options={"public": False},
                )
                logger.info("supabase_bucket_created", bucket=bucket)

    def store_document(
        self,
        content: bytes,
        content_type: str,
        source_id: str,
        jurisdiction: str,
    ) -> str:
        """Upload raw regulatory document to Supabase Storage. Returns object path."""
        ext = "pdf" if "pdf" in content_type else "html"
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        object_path = f"{jurisdiction}/{date_prefix}/{source_id}.{ext}"

        self._client.storage.from_(settings.supabase_bucket_regulatory_docs).upload(
            path=object_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"},
        )

        logger.info("document_stored_supabase", path=object_path, size=len(content))
        return object_path

    def get_document(self, object_path: str) -> bytes:
        """Download raw document by path."""
        response = self._client.storage.from_(
            settings.supabase_bucket_regulatory_docs
        ).download(object_path)
        return response

    def get_public_url(self, object_path: str) -> str:
        """Get public URL for a stored document (if bucket is public)."""
        return self._client.storage.from_(
            settings.supabase_bucket_regulatory_docs
        ).get_public_url(object_path)

    def list_documents(self, prefix: str = "") -> list[str]:
        """List all stored document paths."""
        items = self._client.storage.from_(
            settings.supabase_bucket_regulatory_docs
        ).list(prefix)
        return [item["name"] for item in items]

    def delete_document(self, object_path: str):
        """Delete a document from storage."""
        self._client.storage.from_(
            settings.supabase_bucket_regulatory_docs
        ).remove([object_path])
        logger.info("document_deleted_supabase", path=object_path)
