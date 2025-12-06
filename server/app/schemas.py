from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Union, Literal, Any
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


# =============================================================================
# V_Tutor Exam Schemas (for routes/exam.py)
# =============================================================================

class VTutorCreateExamRequest(BaseModel):
    """Request to create a new exam."""
    teacher_id: str
    teacher_name: str
    prompt: str
    question_count: int = 5
    num_questions: Optional[int] = None  # Alias for question_count
    session_id: Optional[str] = None
    temperature: float = 0.7


class VTutorQuestion(BaseModel):
    """A single exam question."""
    id: int
    text: str
    options: List[str]
    correct_answer: Union[str, int]
    explanation: Optional[str] = None


class VTutorExamResponse(BaseModel):
    """Response after creating an exam."""
    exam_id: str
    teacher_id: str
    student_url: str
    questions_count: int


class VTutorStartExamRequest(BaseModel):
    """Request to start an exam as a student."""
    student_name: str


class VTutorSubmitAnswerRequest(BaseModel):
    """Submit a single answer."""
    question_id: int
    answer: str


class VTutorSubmitExamRequest(BaseModel):
    """Submit all exam answers."""
    student_name: str
    answers: Dict[str, Any]  # question_id -> answer
    chat_history: Optional[List[dict]] = None


class VTutorStudentResult(BaseModel):
    """Student's exam result."""
    student_name: str
    score: int
    total: int
    percentage: float
    answers: Dict[str, dict]
    submitted_at: str
    analysis: Optional[dict] = None


class VTutorRegisterTeacherRequest(BaseModel):
    """Request to register a new teacher."""
    teacher_name: str


class VTutorSingleChoiceQuestion(BaseModel):
    """Text-only single choice question."""
    type: Literal["single_choice"] = "single_choice"
    text: str
    options: List[str]
    correct_answer: int  # 0-based index
    explanation: str

class VTutorImageSingleChoiceQuestion(BaseModel):
    """Image + single choice question."""
    type: Literal["image_single_choice"] = "image_single_choice"
    image_prompt: str
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    text: str
    options: List[str]
    correct_answer: int  # 0-based index
    explanation: str

class VTutorMultiChoiceQuestion(BaseModel):
    """Text-only multiple choice question."""
    type: Literal["multi_choice"] = "multi_choice"
    text: str
    options: List[str]
    correct_answers: List[int]  # 0-based indices
    explanation: str

class VTutorFillInBlanksQuestion(BaseModel):
    """Fill in the blanks question."""
    type: Literal["fill_in_blanks"] = "fill_in_blanks"
    text: str  # Text with blanks
    blanks_count: int
    correct_answers: List[str]  # Exact text answers
    explanation: str

class VTutorImageMultiChoiceQuestion(BaseModel):
    """Image + multiple choice question."""
    type: Literal["image_multi_choice"] = "image_multi_choice"
    image_prompt: str
    image_base64: Optional[str] = None
    text: str
    options: List[str]
    correct_answers: List[int]
    explanation: str

# Voice Type and Dialogue Segment (Same as generators/schemas.py)
VoiceType = Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]

class DialogueSegment(BaseModel):
    voice: VoiceType
    text: str

class VTutorAudioMultiChoiceQuestion(BaseModel):
    """Audio + multiple choice question."""
    type: Literal["audio_multi_choice"] = "audio_multi_choice"
    audio_script: List[DialogueSegment]
    audio_url: Optional[str] = None
    text: str
    options: List[str]
    correct_answers: List[int]
    explanation: str

class VTutorImageFillInBlanksQuestion(BaseModel):
    """Image + fill in the blanks question."""
    type: Literal["image_fill_in_blanks"] = "image_fill_in_blanks"
    image_prompt: str
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    text: str
    blanks_count: int
    correct_answers: List[str]
    explanation: str

class VTutorAudioFillInBlanksQuestion(BaseModel):
    """Audio + fill in the blanks question."""
    type: Literal["audio_fill_in_blanks"] = "audio_fill_in_blanks"
    audio_script: List[DialogueSegment]
    audio_url: Optional[str] = None
    text: str
    blanks_count: int
    correct_answers: List[str]
    explanation: str

class VTutorExamQuestionsResponse(BaseModel):
    """Response with generated questions."""
    questions: List[Union[
        VTutorSingleChoiceQuestion, 
        VTutorImageSingleChoiceQuestion,
        VTutorMultiChoiceQuestion,
        VTutorFillInBlanksQuestion,
        VTutorImageMultiChoiceQuestion,
        VTutorAudioMultiChoiceQuestion,
        VTutorImageFillInBlanksQuestion,
        VTutorAudioFillInBlanksQuestion
    ]]

