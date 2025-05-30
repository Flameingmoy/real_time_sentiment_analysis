# backend/db/models.py
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector  # For pgvector support

from backend.db.base_class import Base

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    text_content = Column(Text, nullable=False)
    source = Column(String(100), index=True) # e.g., 'csv_import', 'webhook_x', 'manual'
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    metadata_ = Column(JSON, nullable=True) # For any additional, unstructured source-specific data

    # Relationships
    sentiment_results = relationship("SentimentResult", back_populates="feedback_item", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="feedback_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Feedback(id={self.id}, source='{self.source}', text='{self.text_content[:30]}...')>"

class SentimentResult(Base):
    __tablename__ = "sentiment_results"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sentiment_label = Column(String(50), nullable=False, index=True) # e.g., 'positive', 'negative', 'neutral'
    sentiment_score = Column(Float, nullable=True) # Confidence score, if applicable
    
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    model_used = Column(String(100), nullable=True) # e.g., 'granite-instruct-v1'

    # Relationship
    feedback_item = relationship("Feedback", back_populates="sentiment_results")

    def __repr__(self):
        return f"<SentimentResult(id={self.id}, feedback_id={self.feedback_id}, label='{self.sentiment_label}')>"

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False, unique=True, index=True) # Assuming one embedding per feedback
    
    # Assuming a fixed dimension for embeddings, e.g., 768 or 1024.
    # Replace 1024 with the actual dimension of your Granite embeddings.
    # If you don't know it yet, you can leave it out or make it configurable.
    embedding_vector = Column(Vector(1024), nullable=False) # Example dimension
    
    generated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    model_used = Column(String(100), nullable=True) # e.g., 'granite-embed-text-v1'

    # Relationship
    feedback_item = relationship("Feedback", back_populates="embeddings")

    def __repr__(self):
        return f"<Embedding(id={self.id}, feedback_id={self.feedback_id}, model='{self.model_used}')>"

# To ensure all models are known to Base.metadata for Alembic or create_all
# you can create a simple __init__.py in the db directory that imports them,
# or ensure they are imported somewhere before Base.metadata.create_all is called.
# For now, this file defines them.
