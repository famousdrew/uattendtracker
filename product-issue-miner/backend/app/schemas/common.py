from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int

class MessageResponse(BaseModel):
    """Simple message response."""
    message: str

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
