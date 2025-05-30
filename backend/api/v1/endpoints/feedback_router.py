# backend/api/v1/endpoints/feedback_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend import crud  # Updated import
from backend import schemas # Updated import
from backend.db.session import get_db # Make sure get_db is correctly defined

router = APIRouter()

@router.post("/", response_model=schemas.Feedback, status_code=201)
async def create_new_feedback(
    feedback_in: schemas.FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new feedback.
    """
    feedback = await crud.create_feedback(db=db, feedback_in=feedback_in)
    return feedback

@router.get("/{feedback_id}", response_model=schemas.Feedback)
async def read_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve feedback by ID.
    """
    db_feedback = await crud.get_feedback(db=db, feedback_id=feedback_id)
    if db_feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return db_feedback

@router.get("/", response_model=List[schemas.Feedback])
async def read_all_feedback(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all feedback entries with pagination.
    """
    feedback_list = await crud.get_all_feedback(db=db, skip=skip, limit=limit)
    return feedback_list