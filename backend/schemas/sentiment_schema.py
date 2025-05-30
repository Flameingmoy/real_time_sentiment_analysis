# backend/schemas/sentiment_schema.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime

class SentimentResultBase(BaseModel):
    sentiment_label: str
    sentiment_score: Optional[float] = None
    model_used: Optional[str] = None

class SentimentResultCreate(SentimentResultBase):
    feedback_id: int

class SentimentResult(SentimentResultBase):
    id: int
    feedback_id: int
    analyzed_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
