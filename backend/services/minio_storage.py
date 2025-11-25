"""MinIO storage service for file management."""
from minio import Minio
from minio.error import S3Error
from pathlib import Path
import logging
from typing import Optional
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MinIOStorage:
    """MinIO object storage client."""
    
    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        
        # Create bucket if it doesn't exist
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")
            raise
    
    def upload_file(self, file_path: str, object_name: str) -> str:
        """
        Upload file to MinIO.
        
        Args:
            file_path: Local file path
            object_name: Object name in MinIO (path)
            
        Returns:
            Object path in MinIO
        """
        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path
            )
            logger.info(f"Uploaded file to MinIO: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def download_file(self, object_name: str, file_path: str):
        """
        Download file from MinIO.
        
        Args:
            object_name: Object name in MinIO
            file_path: Local file path to save to
        """
        try:
            self.client.fget_object(
                self.bucket_name,
                object_name,
                file_path
            )
            logger.info(f"Downloaded file from MinIO: {object_name}")
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Get presigned URL for file access.
        
        Args:
            object_name: Object name in MinIO
            expires: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def delete_file(self, object_name: str):
        """
        Delete file from MinIO.
        
        Args:
            object_name: Object name in MinIO
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file from MinIO: {object_name}")
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            raise
    
    def list_files(self, prefix: Optional[str] = None) -> list:
        """
        List files in bucket.
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of object names
        """
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing files: {e}")
            raise


# Global instance
_minio_storage = None


def get_minio_storage() -> MinIOStorage:
    """Get singleton MinIO storage instance."""
    global _minio_storage
    if _minio_storage is None:
        _minio_storage = MinIOStorage()
    return _minio_storage
