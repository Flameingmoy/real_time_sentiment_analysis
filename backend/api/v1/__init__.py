# backend/api/v1/__init__.py
from fastapi import APIRouter
from .endpoints import feedback_router # We will create feedback_router next

# Main router for API v1
api_v1_router = APIRouter()

# Include routers from endpoint modules
# Example: api_v1_router.include_router(some_other_router.router, prefix="/items", tags=["items"])
api_v1_router.include_router(feedback_router.router, prefix="/feedback", tags=["Feedback"])