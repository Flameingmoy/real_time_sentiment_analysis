from fastapi import FastAPI
import logging

from backend.db.base_class import Base  # Import Base
from backend.db.session import async_engine # Import async_engine
# Import models to ensure they are registered with Base.metadata
from backend.db.models import Feedback, SentimentResult, Embedding

# Import API router
from backend.api.v1 import api_v1_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Real-Time Sentiment Analysis API", version="0.1.0")

# Include the API router
app.include_router(api_v1_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup - Initializing database...")
    async with async_engine.begin() as conn:
        # For synchronous 'create_all', we run it within run_sync
        # This is important for async engines like the one we are using.
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialization complete.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")

@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Sentiment Analysis API"}

# Further endpoints will be added here
