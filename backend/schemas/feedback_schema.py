# backend/schemas/feedback_schema.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
import datetime
from typing import List
from .sentiment_schema import SentimentResult

class FeedbackBase(BaseModel):
    text_content: str
    source: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None # Ensure this matches your model

class FeedbackCreate(FeedbackBase):
    pass

class Feedback(FeedbackBase):
    id: int
    timestamp: datetime.datetime # Ensure this matches your model

    sentiment_results: List[SentimentResult] = []

    # Pydantic V2 config for ORM mode
    model_config = ConfigDict(from_attributes=True)