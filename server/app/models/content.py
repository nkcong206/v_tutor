from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class QuestionType(str, enum.Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"


class Material(Base):
    """Learning materials uploaded by teachers"""
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    vector_store_id = Column(String, nullable=True)  # Chroma collection ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    questions = relationship("Question", back_populates="material")


class Question(Base):
    """Individual questions generated from materials"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True)
    text = Column(Text, nullable=False)
    type = Column(SQLEnum(QuestionType), nullable=False)
    options = Column(JSON, nullable=True)  # For multiple choice: ["A. ...", "B. ...", ...]
    correct_answer = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)  # Detailed solution for teacher review
    explanation = Column(Text, nullable=True)  # Concept explanation
    subject = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    creativity_level = Column(Integer, default=3)  # 1-5
    practical_level = Column(Integer, default=3)  # 1-5
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    material = relationship("Material", back_populates="questions")


class Exam(Base):
    """Exams created by teachers"""
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    question_ids = Column(JSON, nullable=False)  # List of question IDs
    time_limit = Column(Integer, nullable=True)  # Minutes
    exam_type = Column(String, nullable=False)  # "quiz_15min", "homework", "test"
    share_token = Column(String, unique=True, index=True)  # For sharing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sessions = relationship("ExamSession", back_populates="exam")
