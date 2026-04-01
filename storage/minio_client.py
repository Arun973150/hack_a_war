import io
import structlog
from datetime import datetime
from minio import Minio
from minio.error import S3Error

from config import settings

logger = structlog.get_logger()


class MinIOClient:
    """MinIO object storage client for raw regulatory documents."""

    def __init__(self):
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        for bucket in [
            settings.minio_bucket_regulatory_docs,
            settings.minio_bucket_processed,
        ]:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
                logger.info("minio_bucket_created", bucket=bucket)

    def store_document(
        self,
        content: bytes,
        content_type: str,
        source_id: str,
        jurisdiction: str,
    ) -> str:
        """Store raw regulatory document. Returns object path."""
        ext = "pdf" if "pdf" in content_type else "html"
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        object_path = f"{jurisdiction}/{date_prefix}/{source_id}.{ext}"

        self._client.put_object(
            bucket_name=settings.minio_bucket_regulatory_docs,
            object_name=object_path,
            data=io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
        logger.info("document_stored", path=object_path, size=len(content))
        return object_path

    def get_document(self, object_path: str) -> bytes:
        """Retrieve raw document by path."""
        response = self._client.get_object(
            bucket_name=settings.minio_bucket_regulatory_docs,
            object_name=object_path,
        )
        return response.read()

    def list_documents(self, prefix: str = "") -> list[str]:
        """List all stored document paths."""
        objects = self._client.list_objects(
            settings.minio_bucket_regulatory_docs,
            prefix=prefix,
            recursive=True,
        )
        return [obj.object_name for obj in objects]
