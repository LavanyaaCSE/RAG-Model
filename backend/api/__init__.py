"""API package initialization."""
from .upload import router as upload_router
from .search import router as search_router
from .query import router as query_router
from .documents import router as documents_router

__all__ = [
    "upload_router",
    "search_router",
    "query_router",
    "documents_router",
]
