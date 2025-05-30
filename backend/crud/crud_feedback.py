# backend/crud/crud_feedback.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from backend.db.models import Feedback
from backend.schemas.feedback_schema import FeedbackCreate
from backend.schemas.sentiment_schema import SentimentResultCreate
from backend.services.sentiment_service import analyze_sentiment
from .crud_sentiment import create_sentiment_result

async def create_feedback(db: AsyncSession, feedback_in: FeedbackCreate) -> Feedback:
    """
    Create a new feedback entry in the database.
    """
    db_feedback = Feedback(
        text_content=feedback_in.text_content,
        source=feedback_in.source,
        metadata_=feedback_in.metadata_
        # timestamp is handled by the database default
    )
    db.add(db_feedback)
    await db.commit()  # Commit to get the feedback ID
    await db.refresh(db_feedback)

    # Perform sentiment analysis
    sentiment_data = await analyze_sentiment(db_feedback.text_content)

    # Create sentiment result linked to this feedback
    sentiment_create_schema = SentimentResultCreate(
        feedback_id=db_feedback.id,
        sentiment_label=sentiment_data["sentiment_label"],
        sentiment_score=sentiment_data["sentiment_score"],
        model_used=sentiment_data["model_used"]
    )
    await create_sentiment_result(db=db, sentiment_in=sentiment_create_schema)

    # Refresh again to load the sentiment_results relationship
    await db.refresh(db_feedback)
    return db_feedback

async def get_feedback(db: AsyncSession, feedback_id: int) -> Optional[Feedback]:
    """
    Retrieve a feedback entry by its ID.
    """
    result = await db.execute(select(Feedback).filter(Feedback.id == feedback_id))
    return result.scalars().first()

async def get_all_feedback(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Feedback]:
    """
    Retrieve a list of feedback entries.
    """
    result = await db.execute(select(Feedback).offset(skip).limit(limit))
    return result.scalars().all()

# Add update and delete functions here later if needed for MVP