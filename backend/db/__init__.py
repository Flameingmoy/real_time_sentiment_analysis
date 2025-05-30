# backend/db/__init__.py
from .base_class import Base
from .models import Feedback, SentimentResult, Embedding

# This makes Base.metadata aware of all models imported above
# when this __init__.py is processed.
