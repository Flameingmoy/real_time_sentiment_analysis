# backend/crud/crud_sentiment.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.db.models import SentimentResult
from backend.schemas.sentiment_schema import SentimentResultCreate

async def create_sentiment_result(db: AsyncSession, sentiment_in: SentimentResultCreate) -> SentimentResult:
    """
    Create a new sentiment result in the database.
    """
    db_sentiment = SentimentResult(
        feedback_id=sentiment_in.feedback_id,
        sentiment_label=sentiment_in.sentiment_label,
        sentiment_score=sentiment_in.sentiment_score,
        model_used=sentiment_in.model_used
    )
    db.add(db_sentiment)
    await db.commit()
    await db.refresh(db_sentiment)
    return db_sentiment

async def get_sentiment_results_for_feedback(db: AsyncSession, feedback_id: int) -> list[SentimentResult]:
    """
    Retrieve all sentiment results for a given feedback_id.
    """
    result = await db.execute(
        select(SentimentResult).where(SentimentResult.feedback_id == feedback_id)
    )
    return result.scalars().all()
