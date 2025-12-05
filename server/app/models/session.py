from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ExamSession(Base):
    """Student exam session tracking"""
    __tablename__ = "exam_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_name = Column(String, nullable=False)
    student_email = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    answers = Column(JSON, default={})  # {question_id: answer}
    is_completed = Column(Boolean, default=False)
    
    # Relationships
    exam = relationship("Exam", back_populates="sessions")
    tutor_conversations = relationship("TutorConversation", back_populates="session")


class TutorConversation(Base):
    """AI Tutor conversation history and analytics"""
    __tablename__ = "tutor_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=False)
    question_id = Column(Integer, nullable=False)
    messages = Column(JSON, default=[])  # [{"role": "student/ai", "content": "...", "timestamp": "..."}]
    
    # Analytics
    total_hints_given = Column(Integer, default=0)
    concepts_explained = Column(JSON, default=[])  # List of concepts discussed
    thinking_time_seconds = Column(Integer, default=0)
    student_questions = Column(JSON, default=[])  # Questions asked by student
    
    # Status
    answer_reached = Column(Boolean, default=False)
    is_correct = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    session = relationship("ExamSession", back_populates="tutor_conversations")
