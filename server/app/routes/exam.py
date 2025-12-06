from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import shutil
import os
import json
import asyncio
from app.config import settings
from app.services.semantic_cache import get_questions, add_question, get_questions_batch, add_cached_question
import hashlib
from datetime import datetime
import time
import uuid
from openai import OpenAI
import base64
from typing import List

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
    session_id: Optional[str] = None
    temperature: float = 0.7


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

@router.post("/upload")
async def upload_files(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    upload_dir = os.path.join("data", session_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_files = []
    for file in files:
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Pre-calculate base64 for faster usage later?
        # User said: "có thể lưu kèm file base64 để gửi nhanh hơn"
        # We can just read it when needed to avoid duplication or compute here.
        # Let's save a .base64 sidecar file
        with open(file_path, "rb") as f:
            data = f.read()
            base64_string = base64.b64encode(data).decode("utf-8")
        
        with open(f"{file_path}.base64", "w") as f:
            f.write(base64_string)
            
        saved_files.append(file.filename)
        
    return {"success": True, "files": saved_files}

@router.delete("/file")
async def delete_file(
    session_id: str = Form(...),
    filename: str = Form(...)
):
    upload_dir = os.path.join("data", session_id)
    file_path = os.path.join(upload_dir, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Remove base64 sidecar
    base64_path = f"{file_path}.base64"
    if os.path.exists(base64_path):
        os.remove(base64_path)
        
    return {"success": True}


class ExamQuestionItem(BaseModel):
    text: str
    options: List[str]
    correct_answer: str
    explanation: str

class ExamQuestionsResponse(BaseModel):
    questions: List[ExamQuestionItem]

@router.post("/create-exam", response_model=ExamResponse)
async def create_exam(request: CreateExamRequest, background_tasks: BackgroundTasks):
    """
    Teacher creates exam from prompt, returns student URL
    """
    import time
    import asyncio
    import random
    from openai import AsyncOpenAI
    
    # Init Async Client
    aclient = AsyncOpenAI(api_key=settings.openai_api_key)
    
    try:
        start_time = time.time()
        
        system_prompt = """Bạn là một chuyên gia giáo dục tiểu học và trung học, chuyên tạo đề thi trắc nghiệm KHÔNG CHỈ CHÍNH XÁC chuyên môn mà còn SÁNG TẠO, SINH ĐỘNG.

YÊU CẦU QUAN TRỌNG:
1. KHÔNG copy paste nội dung file. Hãy "bắt chước" phong cách, độ khó và dạng bài trong file (nếu có).
2. Nếu là file cho học sinh tiểu học (Lớp 1-5):
   - Ngôn ngữ phải cực kỳ đơn giản, thân thiện, dùng nhiều động từ mạnh.
   - Thêm emoji (🍎, ⭐️, 🚗) vào câu hỏi để sinh động.
   - Ví dụ: Thay vì "Số nào lớn hơn?", hãy viết "Chú thỏ nào cầm củ cà rốt to hơn? 🐰🥕".
3. Mỗi câu hỏi có 4 đáp án (A, B, C, D). Chỉ 1 đúng.
4. KHÔNG ĐƯỢC đặt câu hỏi dạng "Nội dung file là gì?". PHẢI TẠO BÀI TẬP MỚI tương tự.
5. Giải thích đáp án phải dễ hiểu, mang tính khuyến khích học sinh."""

        user_prompt = f"Yêu cầu giáo viên: {request.prompt}\n\nHãy tạo {request.question_count} câu hỏi trắc nghiệm dựa trên yêu cầu trên và các tài liệu đính kèm (nếu có)."
        
        if not user_prompt:
             raise HTTPException(status_code=400, detail="Prompt is required")
             
        # Cache Services
        from app.services.semantic_cache import get_cached_questions, add_cached_question
        
        # Prepare content with files
        content_payload = []
        file_hashes = []
        
        if request.session_id:
            session_dir = os.path.join("data", request.session_id)
            if os.path.exists(session_dir):
                for filename in sorted(os.listdir(session_dir)):
                    if filename.endswith(".base64"): continue
                    
                    file_path = os.path.join(session_dir, filename)
                    base64_path = f"{file_path}.base64"
                    
                    # File Processing (PDF/Image)
                    if filename.lower().endswith(".pdf"):
                        from pdf2image import convert_from_path
                        import io
                        try:
                            images = convert_from_path(file_path, first_page=1, last_page=5)
                            content_payload.append({
                                "type": "text",
                                "text": f"--- Tài liệu tham khảo: {filename} (Trang 1-{len(images)}) ---"
                            })
                            for image in images:
                                bonded = io.BytesIO()
                                image.save(bonded, format="JPEG")
                                img_str = base64.b64encode(bonded.getvalue()).decode("utf-8")
                                file_hashes.append(hashlib.md5(img_str.encode()).hexdigest())
                                content_payload.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}
                                })
                        except Exception as e:
                            print(f"⚠️ Error converting PDF {filename}: {e}")
                    
                    elif os.path.exists(base64_path):
                         with open(base64_path, "r") as f: base64_string = f.read()
                         file_hashes.append(hashlib.md5(base64_string.encode()).hexdigest())
                         content_payload.append({"type": "text", "text": f"--- Tài liệu tham khảo: {filename} ---"})
                         content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_string}"}})
                    
                    else:
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                            base64_string = base64.b64encode(file_bytes).decode("utf-8")
                        file_hashes.append(hashlib.md5(base64_string.encode()).hexdigest())
                        content_payload.append({"type": "text", "text": f"--- Tài liệu tham khảo: {filename} ---"})
                        content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_string}"}})

        files_hash_str = "_".join(file_hashes)
        full_context_key = f"{system_prompt}\n---\n{user_prompt}\n---\n{files_hash_str}\n---\ntemp:{request.temperature}"
        
        # 1. Fetch available questions from cache
        existing_questions = get_cached_questions(full_context_key)
        print(f"📊 Pooling: Found {len(existing_questions)} cached questions. Need {request.question_count}.")
        
        final_questions = []
        needed_count = request.question_count
        
        # 2. Pool Logic
        if len(existing_questions) >= needed_count:
            # We have enough, pick random subset
            print("✅ Cache sufficient. Picking random subset.")
            final_questions = random.sample(existing_questions, needed_count)
        else:
            # We need to generate more
            final_questions.extend(existing_questions)
            to_generate = needed_count - len(existing_questions)
            print(f"⚡ Generating {to_generate} new questions asynchronously...")
            
            # Prepare payload for single question generation
            # Slightly modify prompt to ask for just ONE question per request to maintain independence
            # Actually with 1 question request, we just ask for 1.
            
            content_payload.append({
                "type": "text",
                "text": user_prompt + "\n\n(Chỉ tạo 1 câu hỏi duy nhất)" 
            })
            
            # Define async generation function for a single question
            async def generate_single_question():
                try:
                    response = await aclient.beta.chat.completions.parse(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": content_payload}
                        ],
                        temperature=request.temperature, # High temp = more variety
                        response_format=ExamQuestionItem # Single item, not list
                    )
                    return response.choices[0].message.parsed
                except Exception as e:
                    print(f"⚠️ Async Gen Error: {e}")
                    return None

            # Launch parallel tasks
            tasks = [generate_single_question() for _ in range(to_generate)]
            results = await asyncio.gather(*tasks)
            
            # Process results
            new_questions = []
            
            # Create a set of existing hashes to prevent duplicates
            # FIX: Exclude 'id' field from hashing since new questions don't have it
            existing_hashes = set()
            for q in existing_questions:
                 # Create a copy without 'id' for fair comparison
                 q_content = {k: v for k, v in q.items() if k != 'id'}
                 q_json = json.dumps(q_content, ensure_ascii=False, sort_keys=True)
                 existing_hashes.add(hashlib.md5(q_json.encode()).hexdigest())

            for res in results:
                if res:
                    q_dict = res.model_dump()
                    q_json = json.dumps(q_dict, ensure_ascii=False, sort_keys=True)
                    q_hash = hashlib.md5(q_json.encode()).hexdigest()
                    
                    if q_hash not in existing_hashes:
                        new_questions.append(q_dict)
                        # Add to set to prevent duplicates within this new batch
                        existing_hashes.add(q_hash)
                        # Add to cache immediately (or async)
                        add_cached_question(full_context_key, q_dict)
                    else:
                         print(f"⚠️ Duplicate question generated (Hash: {q_hash[:8]}), skipping to ensure unique output.")
            
            final_questions.extend(new_questions)
            
            # FIX: If we still don't have enough, try generating more (up to 2 retries)
            retries = 0
            while len(final_questions) < request.question_count and retries < 2:
                retries += 1
                need_more = request.question_count - len(final_questions)
                print(f"🔁 Retry {retries}: Need {need_more} more unique questions...")
                
                retry_tasks = [generate_single_question() for _ in range(need_more + 1)]  # +1 buffer for failures
                retry_results = await asyncio.gather(*retry_tasks)
                
                for res in retry_results:
                    if res and len(final_questions) < request.question_count:
                        q_dict = res.model_dump()
                        q_json = json.dumps(q_dict, ensure_ascii=False, sort_keys=True)
                        q_hash = hashlib.md5(q_json.encode()).hexdigest()
                        
                        if q_hash not in existing_hashes:
                            new_questions.append(q_dict)
                            final_questions.append(q_dict)
                            existing_hashes.add(q_hash)
                            add_cached_question(full_context_key, q_dict)
            
            print(f"✅ Generated {len(new_questions)} new unique questions. Total available: {len(final_questions)}")

        # Calculate final elapsed time
        elapsed = time.time() - start_time
        print(f"⏱️ Total Time: {elapsed:.3f}s")
        
        # If we still don't have enough (failures), we just return what we have
        if not final_questions:
             raise HTTPException(status_code=500, detail="Failed to generate any questions.")

        
        # Convert to response format
        final_response_object = ExamQuestionsResponse(questions=final_questions)
        
        
        # Convert Pydantic model to dict list for processing
        # Convert Pydantic model to dict list for processing
        # With new async logic, 'final_questions' is already a list of dicts
        questions_data = final_questions
        
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
            "temperature": request.temperature, # Store for regeneration
            "files_hash": files_hash_str,       # Store for regeneration
            "system_prompt": system_prompt,     # Store for regeneration
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


# SSE Connection Manager
class ConnectionManager:
    def __init__(self):
        # map exam_id -> list of queues
        self.active_connections: Dict[str, List[asyncio.Queue]] = {}

    async def connect(self, exam_id: str) -> asyncio.Queue:
        if exam_id not in self.active_connections:
            self.active_connections[exam_id] = []
        queue = asyncio.Queue()
        self.active_connections[exam_id].append(queue)
        return queue

    def disconnect(self, exam_id: str, queue: asyncio.Queue):
        if exam_id in self.active_connections:
            if queue in self.active_connections[exam_id]:
                self.active_connections[exam_id].remove(queue)
            if not self.active_connections[exam_id]:
                del self.active_connections[exam_id]

    async def broadcast(self, exam_id: str, message: dict):
        if exam_id in self.active_connections:
            for queue in self.active_connections[exam_id]:
                await queue.put(message)

manager = ConnectionManager()


@router.get("/events/{exam_id}")
async def exam_events(exam_id: str, request: Request):
    """
    SSE Endpoint for real-time exam updates.
    """
    async def event_generator():
        queue = await manager.connect(exam_id)
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                    
                # Wait for message with timeout
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    yield f": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            manager.disconnect(exam_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Async regeneration task
async def regenerate_question_async(exam_id: str, system_prompt: str, prompt: str, temperature: float, existing_content_hashes: set, files_hash: str):
    """
    Background task to generate a replacement question and push to SSE.
    Strategy: Cache First -> Gen Second.
    """
    try:
        from openai import AsyncOpenAI
        import json
        aclient = AsyncOpenAI(api_key=settings.openai_api_key)
        
        final_question = None
        
        # 1. Try to find in CACHE first
        # Construct key (must match create_exam key construction)
        full_context_key = f"{prompt}_{files_hash}_{temperature}_{system_prompt}"
        context_hash = hashlib.sha256(full_context_key.encode()).hexdigest()
        
        cached_questions = get_questions(context_hash)
        print(f"🔍 Checking cache for replacement. Found {len(cached_questions)} candidates.")
        
        for q in cached_questions:
             # Check uniqueness against existing exam questions
             q_content = {
                "text": q.get("text"),
                "options": q.get("options"),
                "correct_answer": q.get("correct_answer"),
                "explanation": q.get("explanation")
             }
             q_json = json.dumps(q_content, ensure_ascii=False, sort_keys=True)
             q_hash = hashlib.md5(q_json.encode()).hexdigest()
             
             if q_hash not in existing_content_hashes:
                 print("✅ Found suitable unique question in CACHE!")
                 final_question = q_content.copy()
                 break
        
        # 2. If no cache hit, GENERATE new
        if not final_question:
            print("🤖 No cache hit. Generating new question with AI...")
            replacement_prompt = f"Yêu cầu gốc: {prompt}\n\nHãy tạo thêm 1 câu hỏi trắc nghiệm MỚI, KHÁC với những câu đã có. (Chỉ 1 câu)."
            
            max_retries = 3
            
            for attempt in range(max_retries):
                response = await aclient.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": replacement_prompt}
                    ],
                    temperature=temperature,
                    response_format=ExamQuestionItem
                )
                
                new_q_data = response.choices[0].message.parsed
                
                # Content for hashing (no ID)
                q_content = {
                    "text": new_q_data.text,
                    "options": new_q_data.options,
                    "correct_answer": new_q_data.correct_answer,
                    "explanation": new_q_data.explanation
                }
                q_json = json.dumps(q_content, ensure_ascii=False, sort_keys=True)
                q_hash = hashlib.md5(q_json.encode()).hexdigest()
                
                if q_hash not in existing_content_hashes:
                    # Success
                    final_question = q_content.copy()
                    
                    # Add this NEW question to cache for future
                    add_cached_question(full_context_key, final_question)
                    break
                else:
                    print(f"⚠️ Async Duplicate generated (Attempt {attempt+1})")

        # 3. Finalize and Push
        if final_question:
            if exam_id in exams_db:
                exam = exams_db[exam_id]
                questions = exam["questions"]
                new_id = max([q["id"] for q in questions]) + 1 if questions else 1
                final_question["id"] = new_id
                
                # Add to DB
                questions.append(final_question)
                
                # Broadcast event
                await manager.broadcast(exam_id, {"type": "new_question", "data": final_question})
        else:
             print("❌ Failed to generate unique question async.")
             await manager.broadcast(exam_id, {"type": "error", "message": "Failed to generate unique replacement."})

    except Exception as e:
        print(f"⚠️ Async regeneration error: {e}") 
        await manager.broadcast(exam_id, {"type": "error", "message": str(e)})


@router.delete("/exam/{exam_id}/question/{question_id}")
async def delete_question(exam_id: str, question_id: int, background_tasks: BackgroundTasks):
    """
    Delete a question IMMEDIATELY and regenerate replacement in BACKGROUND.
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    
    # 1. Update DB (Synchronous, fast)
    # Also remove from cache? NO, because we might want it for other contexts or re-use?
    # Actually, if it's "bad", maybe remove? But typical "Delete" here is "I don't like this ONE in this exam".
    # It might be fine for another exam.
    # However, to be safe and strictly follow "delete" semantics:
    # If the user deletes it, they likely don't want to see it again for this prompt.
    # So we SHOULD remove it from cache for this context.
    
    # Identify question to remove cache
    question_to_delete = next((q for q in exam["questions"] if q["id"] == question_id), None)
    
    # Remove from Exam DB
    exam["questions"] = [q for q in exam["questions"] if q["id"] != question_id]
    
    # Remove from Cache (Async/Sync)
    prompt = exam.get("prompt", "")
    files_hash = exam.get("files_hash", "")
    system_prompt = exam.get("system_prompt", "")
    temperature = exam.get("temperature", 0.7)
    
    if question_to_delete:
         from app.services.semantic_cache import remove_cached_question
         full_context_key = f"{prompt}_{files_hash}_{temperature}_{system_prompt}"
         # Remove this specific question from the cache for this context
         # This ensures we don't pick it up again in step 1 of regeneration
         remove_cached_question(full_context_key, question_to_delete)

    # 2. Add Replacement Task
    
    # Snapshot existing hashes for deduplication
    existing_content_hashes = set()
    for q in exam["questions"]:
         q_content = {k: v for k, v in q.items() if k != 'id'}
         q_json = json.dumps(q_content, ensure_ascii=False, sort_keys=True)
         existing_content_hashes.add(hashlib.md5(q_json.encode()).hexdigest())

    background_tasks.add_task(
        regenerate_question_async, 
        exam_id, 
        system_prompt, 
        prompt, 
        temperature, 
        existing_content_hashes,
        files_hash
    )
    
    # 3. Return immediately
    return {"success": True, "message": "Question deleted, regenerating replacement..."}



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
