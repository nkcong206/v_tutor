from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.config import settings
from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends
import json
import re
import uuid
import hashlib
from datetime import datetime
import time
import openai
from openai import OpenAI

# Use standard client for manual caching control
# from gptcache.adapter.openai import OpenAI as GPTCacheOpenAI

router = APIRouter(tags=["Exam"])

# Configure standard client
client = OpenAI(api_key=settings.openai_api_key)

# In-memory storage (in production, use database)
exams_db: Dict[str, dict] = {}
students_db: Dict[str, List[dict]] = {}  # exam_id -> list of student results
teachers_db: Dict[str, dict] = {}  # teacher_id -> teacher info (name, created_at)
teacher_exams_db: Dict[str, List[str]] = {}  # teacher_id -> list of exam_ids


class CreateExamRequest(BaseModel):
    teacher_id: str
    teacher_name: str
    prompt: str
    question_count: int = 5


class Question(BaseModel):
    id: int
    text: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None


class ExamResponse(BaseModel):
    exam_id: str
    teacher_id: str
    student_url: str
    questions_count: int


class StartExamRequest(BaseModel):
    student_name: str

class SubmitAnswerRequest(BaseModel):
    question_id: int
    answer: str

class SubmitExamRequest(BaseModel):
    student_name: str
    answers: Dict[str, str]  # question_id -> answer

class StudentResult(BaseModel):
    student_name: str
    score: int
    total: int
    percentage: float
    answers: Dict[str, dict]
    submitted_at: str


class RegisterTeacherRequest(BaseModel):
    teacher_name: str


@router.post("/register-teacher")
async def register_teacher(request: RegisterTeacherRequest):
    """
    Register a new teacher and get a unique teacher_id based on name hash
    Same name will always get the same teacher_id
    """
    # Create a deterministic ID from teacher name (hash-based)
    name_normalized = request.teacher_name.strip().lower()
    teacher_id = hashlib.md5(name_normalized.encode()).hexdigest()[:8]
    
    # Check if already exists
    if teacher_id not in teachers_db:
        teachers_db[teacher_id] = {
            "teacher_id": teacher_id,
            "teacher_name": request.teacher_name,  # Keep original case
            "created_at": datetime.now().isoformat()
        }
        teacher_exams_db[teacher_id] = []
    
    return {
        "teacher_id": teacher_id,
        "teacher_name": teachers_db[teacher_id]["teacher_name"],
        "teacher_url": f"/giao_vien/{teacher_id}"
    }

class ExamQuestionItem(BaseModel):
    text: str
    options: List[str]
    correct_answer: str
    explanation: str

class ExamQuestionsResponse(BaseModel):
    questions: List[ExamQuestionItem]

@router.post("/create-exam", response_model=ExamResponse)
async def create_exam(request: CreateExamRequest):
    """
    Teacher creates exam from prompt, returns student URL
    """
    import time
    
    try:
        start_time = time.time()
        
        system_prompt = """Bạn là một giáo viên chuyên nghiệp tạo câu hỏi trắc nghiệm.
YÊU CẦU:
1. Mỗi câu hỏi có 4 đáp án (A, B, C, D)
2. Đáp án phải rõ ràng, chỉ có 1 đáp án đúng
3. Câu hỏi phải có tính thực tiễn và sáng tạo
4. Kèm giải thích chi tiết cho đáp án đúng"""

        user_prompt = f"Tạo {request.question_count} câu hỏi trắc nghiệm về: {request.prompt}"
        
        if not user_prompt:
             raise HTTPException(status_code=400, detail="Prompt is required")
             
        # Manual Cache Check
        from app.services.semantic_cache import get_cached_response, save_to_cache
        
        # Construct cache key
        full_prompt_key = f"{system_prompt}\n---\n{user_prompt}"
         
        
        cached_json = get_cached_response(full_prompt_key)
        
        final_response_obj = None
        
        if cached_json:
            print(f"✅ EXAM CACHE HIT (Key: {full_prompt_key[:30]}...)")
            try:
                # Deserialize from cached JSON
                final_response_obj = ExamQuestionsResponse.model_validate_json(cached_json)
            except Exception as e:
                print(f"⚠️ Cache parse error: {e}")
                # Fallback to API if cache corrupt
                pass
        
        if not final_response_obj:
            # Cache Miss - Call OpenAI
            try:
                # Use Beta Parse method for Structured Outputs
                response = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    response_format=ExamQuestionsResponse
                )
                
                final_response_obj = response.choices[0].message.parsed
                
                elapsed = time.time() - start_time
                print(f"❌ EXAM CACHE MISS | Time: {elapsed:.3f}s")
                
                # Save to cache (serialize to JSON)
                if final_response_obj:
                    save_to_cache(full_prompt_key, final_response_obj.model_dump_json())
                    
            except Exception as e:
                print(f"❌ OpenAI API Error: {e}")
                raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")
        
        # Convert Pydantic model to dict list for processing
        # The existing logic expects list of dicts with 'text', 'options' etc.
        # final_response_obj.questions is List[ExamQuestionItem]
        questions_data = [q.model_dump() for q in final_response_obj.questions]
        
        # Generate unique exam ID
        exam_id = str(uuid.uuid4())[:8]
        
        # Format questions
        questions = []
        for idx, q in enumerate(questions_data[:request.question_count], 1):
            questions.append({
                "id": idx,
                "text": q.get("text", ""),
                "options": q.get("options", []),
                "correct_answer": q.get("correct_answer", "A"),
                "explanation": q.get("explanation", "")
            })
        
        # Store exam with teacher info
        exams_db[exam_id] = {
            "exam_id": exam_id,
            "teacher_id": request.teacher_id,
            "teacher_name": request.teacher_name,
            "prompt": request.prompt,
            "questions": questions,
            "created_at": datetime.now().isoformat()
        }
        students_db[exam_id] = []
        
        # Use the provided teacher_id
        teacher_id = request.teacher_id
        
        # Track exam under teacher_id
        if teacher_id not in teacher_exams_db:
            teacher_exams_db[teacher_id] = []
        teacher_exams_db[teacher_id].append(exam_id)
        
        return {
            "exam_id": exam_id,
            "teacher_id": teacher_id,
            "student_url": f"/hoc_sinh/{exam_id}",
            "questions_count": len(questions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo bài: {str(e)}")


@router.get("/exam/{exam_id}")
async def get_exam(exam_id: str):
    """
    Get exam info (for students - includes correct answers for AI tutor)
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    
    # Return questions with correct answer (for AI tutor to check)
    questions_for_student = []
    for q in exam["questions"]:
        questions_for_student.append({
            "id": q["id"],
            "text": q["text"],
            "options": q["options"],
            "correct_answer": q["correct_answer"]  # Need this for AI tutor
        })
    
    return {
        "exam_id": exam_id,
        "questions": questions_for_student,
        "total_questions": len(questions_for_student)
    }


@router.get("/exam/{exam_id}/full")
async def get_exam_full(exam_id: str):
    """
    Get full exam info for teacher (includes correct answers)
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    return {
        "exam_id": exam_id,
        "prompt": exam.get("prompt", ""),
        "teacher_name": exam.get("teacher_name", ""),
        "questions": exam["questions"],
        "created_at": exam["created_at"]
    }


@router.put("/exam/{exam_id}/question/{question_id}")
async def update_question(exam_id: str, question_id: int, question_data: dict):
    """
    Update a specific question in an exam
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    for q in exam["questions"]:
        if q["id"] == question_id:
            if "text" in question_data:
                q["text"] = question_data["text"]
            if "options" in question_data:
                q["options"] = question_data["options"]
            if "correct_answer" in question_data:
                q["correct_answer"] = question_data["correct_answer"]
            if "explanation" in question_data:
                q["explanation"] = question_data["explanation"]
            return {"success": True, "question": q}
    
    raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")


@router.delete("/exam/{exam_id}/question/{question_id}")
async def delete_question(exam_id: str, question_id: int):
    """
    Delete a specific question from an exam
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    original_len = len(exam["questions"])
    exam["questions"] = [q for q in exam["questions"] if q["id"] != question_id]
    
    if len(exam["questions"]) == original_len:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
    
    return {"success": True, "remaining_questions": len(exam["questions"])}


@router.post("/exam/{exam_id}/submit")
async def submit_exam(exam_id: str, request: SubmitExamRequest):
    """
    Student submits their exam
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    questions = exam["questions"]
    
    # Calculate score
    correct = 0
    answer_details = {}
    
    for q in questions:
        q_id = str(q["id"])
        student_answer = request.answers.get(q_id, "")
        is_correct = student_answer.upper() == q["correct_answer"].upper()
        
        if is_correct:
            correct += 1
        
        answer_details[q_id] = {
            "student_answer": student_answer,
            "correct_answer": q["correct_answer"],
            "is_correct": is_correct,
            "explanation": q["explanation"],
            "question_text": q["text"]
        }
    
    total = len(questions)
    percentage = (correct / total * 100) if total > 0 else 0
    
    # Store result
    result = {
        "student_name": request.student_name,
        "score": correct,
        "total": total,
        "percentage": round(percentage, 1),
        "answers": answer_details,
        "submitted_at": datetime.now().isoformat()
    }
    
    students_db[exam_id].append(result)
    
    return result


@router.get("/exam/{exam_id}/results")
async def get_exam_results(exam_id: str):
    """
    Teacher gets all student results for an exam
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    results = students_db.get(exam_id, [])
    
    # Calculate statistics
    if results:
        scores = [r["percentage"] for r in results]
        avg_score = sum(scores) / len(scores)
        highest = max(scores)
        lowest = min(scores)
    else:
        avg_score = 0
        highest = 0
        lowest = 0
    
    return {
        "exam_id": exam_id,
        "prompt": exam["prompt"],
        "total_students": len(results),
        "statistics": {
            "average_score": round(avg_score, 1),
            "highest_score": highest,
            "lowest_score": lowest
        },
        "students": results
    }


@router.get("/teacher/{teacher_id}")
async def get_teacher_exams(teacher_id: str):
    """
    Get all exams created by a teacher (by teacher_id)
    """
    if teacher_id not in teacher_exams_db:
        return {
            "teacher_id": teacher_id,
            "teacher_name": "",
            "exams": [],
            "total_exams": 0
        }
    
    # Get teacher name from teachers_db
    teacher_name = teachers_db.get(teacher_id, {}).get("teacher_name", "")
    
    exam_ids = teacher_exams_db[teacher_id]
    exams_list = []
    
    for exam_id in exam_ids:
        if exam_id in exams_db:
            exam = exams_db[exam_id]
            student_count = len(students_db.get(exam_id, []))
            exams_list.append({
                "exam_id": exam_id,
                "prompt": exam["prompt"],
                "question_count": len(exam["questions"]),
                "student_count": student_count,
                "student_url": f"/hoc_sinh/{exam_id}",
                "created_at": exam["created_at"]
            })
    
    return {
        "teacher_id": teacher_id,
        "teacher_name": teacher_name,
        "exams": exams_list,
        "total_exams": len(exams_list)
    }
