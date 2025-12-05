from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole
from app.models.content import QuestionType


# User Schemas
class UserBase(BaseModel):
    name: str
    email: Optional[str] = None
    role: UserRole


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Question Schemas
class QuestionBase(BaseModel):
    text: str
    type: QuestionType
    options: Optional[List[str]] = None
    correct_answer: str
    solution: str
    explanation: Optional[str] = None
    subject: str
    grade: str
    creativity_level: int = Field(ge=1, le=5, default=3)
    practical_level: int = Field(ge=1, le=5, default=3)


class QuestionCreate(QuestionBase):
    material_id: Optional[int] = None


class QuestionResponse(QuestionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Material Schemas
class MaterialCreate(BaseModel):
    title: str
    subject: str
    grade: str


class MaterialResponse(MaterialCreate):
    id: int
    teacher_id: int
    file_path: str
    vector_store_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Exam Schemas
class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None
    question_ids: List[int]
    time_limit: Optional[int] = None
    exam_type: str = "quiz_15min"


class ExamResponse(ExamCreate):
    id: int
    teacher_id: int
    share_token: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Session Schemas
class SessionStart(BaseModel):
    exam_id: int
    student_name: str
    student_email: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    exam_id: int
    student_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    score: Optional[float]
    is_completed: bool
    
    class Config:
        from_attributes = True


# AI Generation Request
class GenerateQuestionsRequest(BaseModel):
    material_id: int
    question_count: int = Field(ge=1, le=50, default=10)
    question_types: List[QuestionType] = [QuestionType.SINGLE_CHOICE]
    creativity_level: int = Field(ge=1, le=5, default=3)
    practical_level: int = Field(ge=1, le=5, default=3)
    subject: str
    grade: str


# AI Tutor Request
class TutorChatRequest(BaseModel):
    session_id: int
    question_id: int
    message: str
    current_answer: Optional[str] = None


class TutorChatResponse(BaseModel):
    message: str
    hint_type: str  # "concept", "step", "clarification", "encouragement"
    suggestions: List[str] = []
