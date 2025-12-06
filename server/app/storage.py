"""
In-memory storage for exams, students, and teachers.
In production, this should be replaced with a proper database.
"""
from typing import Dict, List


# Exam storage: exam_id -> exam data
exams_db: Dict[str, dict] = {}

# Student results: exam_id -> list of student results
students_db: Dict[str, List[dict]] = {}

# Teacher info: teacher_id -> teacher info (name, created_at)
teachers_db: Dict[str, dict] = {}

# Teacher's exams: teacher_id -> list of exam_ids
teacher_exams_db: Dict[str, List[str]] = {}
