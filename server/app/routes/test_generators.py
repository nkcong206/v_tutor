"""
Test routes for question generators.
For development and testing purposes.
"""
from fastapi import APIRouter
from typing import List, Optional
from pydantic import BaseModel

from app.generators import get_available_types, QuestionType
from app.generators.factory import get_generator, is_media_type
from app.services.question_type_selector import select_question_types


router = APIRouter(tags=["Test Generators"])


class TestGeneratorRequest(BaseModel):
    """Request to test a generator."""
    prompt: str
    question_type: QuestionType = "single_choice"
    subject: str = "default"
    temperature: float = 0.7
    generate_media: bool = False  # Set to False for fast testing


class TestTypeSelectorRequest(BaseModel):
    """Request to test type selector."""
    subject: str
    prompt: str
    question_count: int = 5


@router.get("/available-types/{subject}")
async def get_subject_types(subject: str):
    """Get available question types for a subject."""
    return {
        "subject": subject,
        "available_types": get_available_types(subject)
    }


@router.post("/select-types")
async def test_select_types(request: TestTypeSelectorRequest):
    """Test the question type selector."""
    types = await select_question_types(
        subject=request.subject,
        prompt=request.prompt,
        question_count=request.question_count
    )
    return {
        "subject": request.subject,
        "prompt": request.prompt,
        "selected_types": types
    }


@router.post("/generate-question")
async def test_generate_question(request: TestGeneratorRequest):
    """Test generating a single question."""
    
    generator = get_generator(request.question_type)
    
    if not generator:
        return {
            "error": f"Generator not implemented for type: {request.question_type}",
            "implemented": ["single_choice", "multi_choice", "fill_in_blanks", 
                          "image_single_choice", "audio_single_choice"]
        }
    
    # Build kwargs
    kwargs = {
        "prompt": request.prompt,
        "temperature": request.temperature,
        "question_id": 1
    }
    
    # Add generate_media flag for media generators
    if is_media_type(request.question_type):
        kwargs["generate_media"] = request.generate_media
    
    # Generate question
    question = await generator.generate(**kwargs)
    
    if question:
        return {
            "success": True,
            "question": question.model_dump()
        }
    else:
        return {
            "success": False,
            "error": "Failed to generate question"
        }

