from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict
import shutil
import os
import json
import asyncio
import hashlib
from datetime import datetime
import time
import uuid
import base64
from openai import OpenAI

from app.config import settings
from app.services.semantic_cache import get_questions, add_question, get_questions_batch, add_cached_question
from app.services.sse_manager import sse_manager
from app.storage import exams_db, students_db, teachers_db, teacher_exams_db
from app.schemas import (
    VTutorCreateExamRequest as CreateExamRequest,
    VTutorQuestion as Question,
    VTutorExamResponse as ExamResponse,
    VTutorStartExamRequest as StartExamRequest,
    VTutorSubmitAnswerRequest as SubmitAnswerRequest,
    VTutorSubmitExamRequest as SubmitExamRequest,
    VTutorStudentResult as StudentResult,
    VTutorRegisterTeacherRequest as RegisterTeacherRequest,
    VTutorExamQuestionsResponse as ExamQuestionsResponse,
)

router = APIRouter(tags=["Exam"])

# Configure OpenAI client
client = OpenAI(api_key=settings.openai_api_key)


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


async def process_generated_question_async(exam_id: str, q_dict: dict, qt: str):
    """Helper to process, save, and broadcast a generated question."""
    if exam_id not in exams_db: return

    # Prepare audio as base64 if needed
    audio_url = q_dict.get("audio_url")
    if audio_url and audio_url.startswith("audio/"):
        try:
            audio_path = os.path.join(settings.upload_dir, audio_url)
            if os.path.exists(audio_path):
                with open(audio_path, "rb") as af:
                    b64_audio = base64.b64encode(af.read()).decode("utf-8")
                    audio_url = f"data:audio/mpeg;base64,{b64_audio}"
        except Exception as e:
            print(f"⚠️ Failed to convert audio to base64: {e}")
    
    q_cleaned = {
        "id": 0, # Placeholder, will assign based on length
        "text": q_dict.get("text", ""),
        "options": q_dict.get("options", []),
        "correct_answer": q_dict.get("correct_answer", 0),
        "explanation": q_dict.get("explanation", ""),
        "type": qt,
        "image_url": q_dict.get("image_url"),
        "image_base64": q_dict.get("image_base64"),
        "audio_url": audio_url,
        "blanks": q_dict.get("blanks"), 
        "correct_answers": q_dict.get("correct_answers"),
    }
    
    # Append to DB
    exam = exams_db[exam_id]
    questions = exam["questions"]
    q_cleaned["id"] = len(questions) + 1
    questions.append(q_cleaned)
    
    # Broadcast
    await sse_manager.broadcast(exam_id, {"type": "new_question", "data": q_cleaned})


async def generate_exam_background(
    exam_id: str,
    target_count: int,
    user_prompt: str,
    combined_context_text: str,
    files_hash_str: str,
    temperature: float,
    global_style: str
):
    try:
        from app.services.question_type_selector import select_question_types
        from app.generators.factory import get_generator, is_media_type
        from app.services.semantic_cache import get_cached_questions, add_cached_question
        import random

        # 1. Select Types
        selector_prompt = f"Request: {user_prompt}\nContext: {combined_context_text}"
        selected_types = await select_question_types(
            subject="default",
            prompt=selector_prompt,
            question_count=target_count,
            temperature=temperature
        )
        print(f"🤖 [BG] Selected Types: {selected_types}")
        
        # 2. Prepare Context Key
        final_generator_prompt = f"{user_prompt}\n{combined_context_text}\n{global_style}"
        full_context_key = f"{final_generator_prompt}\n---\n{files_hash_str}\n---\ntemp:{temperature}"
        
        # 3. Cache Check
        cached_questions = get_cached_questions(full_context_key)
        cached_by_type = {}
        for q in cached_questions:
            t = q.get("type", "single_choice")
            if t not in cached_by_type: cached_by_type[t] = []
            cached_by_type[t].append(q)
            
        generation_coroutines = []
        
        # 4. Processing Loop
        for q_type in selected_types:
            if q_type in cached_by_type and cached_by_type[q_type]:
                # CACHE HIT
                idx = random.randint(0, len(cached_by_type[q_type]) - 1)
                q = cached_by_type[q_type].pop(idx)
                print(f"✅ [BG] Cache Hit: {q_type}")
                # Process immediately
                await process_generated_question_async(exam_id, q, q_type)
            else:
                # GENERATE NEW
                async def gen_task(qt=q_type):
                    gen = get_generator(qt)
                    if not gen:
                        qt = "single_choice"
                        gen = get_generator("single_choice")
                    
                    kwargs = {
                        "prompt": final_generator_prompt,
                        "temperature": temperature,
                        "question_id": 0
                    }
                    if is_media_type(qt):
                        kwargs["generate_media"] = True
                        
                    return await gen.generate(**kwargs), qt

                generation_coroutines.append(gen_task())
        
        # 5. Execute Generation Tasks Streaming
        if generation_coroutines:
            print(f"⚡ [BG] Generating {len(generation_coroutines)} new questions...")
            for coro in asyncio.as_completed(generation_coroutines):
                try:
                    res, qt = await coro
                    if res:
                        q_dict = res.model_dump()
                        q_dict["type"] = qt
                        
                        print(f"🐛 [BG] Generated: {q_dict.get('text', '')[:50]}...")
                        # Add to Cache
                        add_cached_question(full_context_key, q_dict, qt)
                        # Process & Broadcast
                        await process_generated_question_async(exam_id, q_dict, qt)
                except Exception as e:
                    print(f"❌ [BG] Task Error: {e}")

        print(f"🏁 [BG] Exam {exam_id} generation finished.")

    except Exception as e:
        print(f"❌ [BG] Critical Error: {e}")
        import traceback
        traceback.print_exc()
        await sse_manager.broadcast(exam_id, {"type": "error", "message": str(e)})


@router.post("/create-exam", response_model=ExamResponse)
async def create_exam(request: CreateExamRequest, background_tasks: BackgroundTasks):
    """
    Teacher creates exam from prompt (Async with Background Task).
    Returns exam_id immediately. Questions are populated via SSE.
    """
    try:
        # 1. Input Processing
        target_count = request.num_questions if request.num_questions else request.question_count
        user_prompt = request.prompt
        
        if not user_prompt:
             raise HTTPException(status_code=400, detail="Prompt is required")

        # Global Instructions (Style only)
        global_style = """
[STYLE INSTRUCTIONS]
- Use specific emoji where appropriate.
- Keep tone friendly and engaging.
- NO copy-pasting from files (if any), create original similar content.
"""
        
        # Process Files to get Content & Hash (Sync part - fast enough)
        content_contexts = []
        file_hashes = []
        
        if request.session_id:
            session_dir = os.path.join("data", request.session_id)
            if os.path.exists(session_dir):
                for filename in sorted(os.listdir(session_dir)):
                    if filename.endswith(".base64"): continue
                    
                    file_path = os.path.join(session_dir, filename)
                    base64_path = f"{file_path}.base64"
                    
                    if os.path.exists(base64_path):
                         with open(base64_path, "r") as f: base64_string = f.read()
                    else:
                        with open(file_path, "rb") as f:
                            base64_string = base64.b64encode(f.read()).decode("utf-8")
                    
                    file_hashes.append(hashlib.md5(base64_string.encode()).hexdigest())
                    content_contexts.append(f"File: {filename}")

        files_hash_str = "_".join(file_hashes)
        combined_context_text = "\n".join(content_contexts)
        
        # 2. Setup Exam in DB (Empty)
        exam_id = str(uuid.uuid4())[:8]
        exams_db[exam_id] = {
            "exam_id": exam_id,
            "teacher_id": request.teacher_id,
            "teacher_name": request.teacher_name,
            "prompt": request.prompt,
            "temperature": request.temperature,
            "subject": "default",
            "questions": [], # Start empty
            "question_count_target": target_count,
            "created_at": datetime.now().isoformat(),
            "status": "generating" # Optional status flag
        }
        students_db[exam_id] = []
        
        if request.teacher_id not in teacher_exams_db:
             teacher_exams_db[request.teacher_id] = []
        teacher_exams_db[request.teacher_id].append(exam_id)
        
        # 3. Schedule Background Task
        background_tasks.add_task(
            generate_exam_background,
            exam_id,
            target_count,
            user_prompt,
            combined_context_text,
            files_hash_str,
            request.temperature,
            global_style
        )
        
        print(f"🚀 Exam {exam_id} creation started in background...")
        
        # 4. Return Immediate Response
        return {
            "exam_id": exam_id,
            "teacher_id": request.teacher_id,
            "student_url": f"/hoc_sinh/{exam_id}",
            "questions_count": target_count # Return target count as placeholder
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        # Prepare context fields
        image_desc = q.get("image_prompt")
        audio_text = None
        if q.get("audio_script"):
            # Convert script to markdown
            try:
                audio_text = ""
                for seg in q["audio_script"]:
                    # seg is dict
                    voice = seg.get("voice", "Speaker")
                    text = seg.get("text", "")
                    audio_text += f"**{voice}**: {text}\n"
            except:
                pass

        questions_for_student.append({
            "id": q["id"],
            "text": q["text"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],  # Need this for AI tutor
            "type": q.get("type", "single_choice"),
            "image_url": q.get("image_url"),
            "image_base64": q.get("image_base64"),
            "image_description": image_desc,
            "audio_url": q.get("audio_url"),
            "audio_script_text": audio_text,
            "blanks": q.get("blanks"),
            "correct_answers": q.get("correct_answers")
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

def run_exam_analysis(exam_id: str, result_index: int, student_name: str, score: int, total_questions: int, chat_history: List[dict]):
    """Background task to run AI analysis on exam performance"""
    try:
        from app.services.llm_service import llm_service
        print(f"🤖 Analyzing performance for {student_name} (Background)...")
        
        analysis = llm_service.analyze_performance(
            student_name=student_name,
            score=score,
            total_questions=total_questions,
            chat_history=chat_history
        )
        
        if analysis:
            # Update the result in memory
            if exam_id in students_db and len(students_db[exam_id]) > result_index:
                students_db[exam_id][result_index]["analysis"] = analysis
                # Broadcast the update to the teacher
                import asyncio
                from app.main import sse_manager # Assuming sse_manager is accessible
                asyncio.run(sse_manager.broadcast(exam_id, {
                    "type": "analysis_update",
                    "data": {
                        "result_index": result_index,
                        "analysis": analysis
                    }
                }))
                print(f"✅ Analysis complete and saved for {student_name}: Score {analysis['score']}")
            else:
                print(f"⚠️ Failed to save analysis for {student_name}: Record not found or index out of bounds")
    except Exception as e:
        print(f"⚠️ Analysis failed: {e}")



@router.get("/events/{exam_id}")
async def exam_events(exam_id: str, request: Request):
    """
    SSE Endpoint for real-time exam updates.
    """
    async def event_generator():
        queue = await sse_manager.connect(exam_id)
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
            sse_manager.disconnect(exam_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Async regeneration task
async def regenerate_question_async(
    exam_id: str, 
    system_prompt: str, 
    prompt: str, 
    temperature: float, 
    existing_content_hashes: set, 
    files_hash: str,
    question_type: str = "single_choice",
    subject: str = "default"
):
    """
    Background task to generate a replacement question and push to SSE.
    Uses the new generator system with question_type support.
    Strategy: Cache First -> Gen Second (with same type).
    """
    try:
        from app.generators.factory import get_generator, is_media_type
        from app.services.semantic_cache import add_cached_question
        import json
        
        final_question = None
        
        # 1. Try to find in CACHE first (matching type)
        full_context_key = f"{prompt}_{files_hash}_{temperature}_{system_prompt}"
        context_hash = hashlib.sha256(full_context_key.encode()).hexdigest()
        
        cached_questions = get_questions(context_hash)
        print(f"🔍 Checking cache for replacement (type: {question_type}). Found {len(cached_questions)} candidates.")
        
        for q in cached_questions:
             # Only consider questions of the same type
             cached_type = q.get("_cached_type", q.get("type", "single_choice"))
             if cached_type != question_type:
                 continue
                 
             # Check uniqueness against existing exam questions
             q_content = {k: v for k, v in q.items() if k not in ['id', '_cached_type']}
             q_json = json.dumps(q_content, ensure_ascii=False, sort_keys=True)
             q_hash = hashlib.md5(q_json.encode()).hexdigest()
             
             if q_hash not in existing_content_hashes:
                 print(f"✅ Found suitable unique question in CACHE (type: {question_type})!")
                 final_question = q_content.copy()
                 final_question["type"] = question_type
                 break
        
        # 2. If no cache hit, GENERATE new using the appropriate generator
        if not final_question:
            print(f"🤖 No cache hit. Generating new question with AI (type: {question_type})...")
            
            generator = get_generator(question_type)
            if not generator:
                print(f"❌ No generator for type: {question_type}. Falling back to single_choice.")
                generator = get_generator("single_choice")
                question_type = "single_choice"
            
            max_retries = 3
            
            for attempt in range(max_retries):
                # Use generator to create question
                kwargs = {
                    "prompt": prompt,
                    "temperature": temperature,
                    "question_id": 0  # Will be assigned later
                }
                # For media types, generate media
                if question_type in ["image_single_choice", "image_multi_choice", "image_fill_in_blanks", "audio_fill_in_blanks"]:
                    kwargs["generate_media"] = True
                new_question = await generator.generate(**kwargs)
                
                if new_question:
                    # Convert to dict
                    q_dict = new_question.model_dump()
                    q_content = {k: v for k, v in q_dict.items() if k not in ['id']}
                    q_json = json.dumps(q_content, ensure_ascii=False, sort_keys=True)
                    q_hash = hashlib.md5(q_json.encode()).hexdigest()
                    
                    if q_hash not in existing_content_hashes:
                        # Success
                        final_question = q_content.copy()
                        
                        # Convert audio to base64 if needed
                        if "audio_url" in final_question and final_question["audio_url"] and final_question["audio_url"].startswith("audio/"):
                            try:
                                audio_path = os.path.join(settings.upload_dir, final_question["audio_url"])
                                if os.path.exists(audio_path):
                                    with open(audio_path, "rb") as audio_file:
                                        encoded_string = base64.b64encode(audio_file.read()).decode('utf-8')
                                        final_question["audio_url"] = f"data:audio/mpeg;base64,{encoded_string}"
                                        print(f"✅ Converted audio to base64 for regeneration")
                            except Exception as e:
                                print(f"⚠️ Failed to convert audio to base64: {e}")

                        # Add this NEW question to cache for future
                        add_cached_question(full_context_key, final_question, question_type)
                        break
                    else:
                        print(f"⚠️ Async Duplicate generated (Attempt {attempt+1})")
                else:
                    print(f"⚠️ Generator returned None (Attempt {attempt+1})")

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
                await sse_manager.broadcast(exam_id, {"type": "new_question", "data": final_question})
        else:
             print("❌ Failed to generate unique question async.")
             await sse_manager.broadcast(exam_id, {"type": "error", "message": "Failed to generate unique replacement."})

    except Exception as e:
        print(f"⚠️ Async regeneration error: {e}") 
        await sse_manager.broadcast(exam_id, {"type": "error", "message": str(e)})


@router.delete("/exam/{exam_id}/question/{question_id}")
async def delete_question(exam_id: str, question_id: int, background_tasks: BackgroundTasks):
    """
    Delete a question IMMEDIATELY and regenerate replacement in BACKGROUND.
    The replacement will be generated with the SAME question type as the deleted one.
    """
    if exam_id not in exams_db:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài kiểm tra")
    
    exam = exams_db[exam_id]
    
    # Identify question to remove cache
    question_to_delete = next((q for q in exam["questions"] if q["id"] == question_id), None)
    
    # Remove from Exam DB
    exam["questions"] = [q for q in exam["questions"] if q["id"] != question_id]
    
    # Remove from Cache and get the question_type for regeneration
    prompt = exam.get("prompt", "")
    files_hash = exam.get("files_hash", "")
    system_prompt = exam.get("system_prompt", "")
    temperature = exam.get("temperature", 0.7)
    subject = exam.get("subject", "default")  # Need to store subject in exam
    
    removed_question_type = "single_choice"  # Default
    if question_to_delete:
         from app.services.semantic_cache import remove_cached_question
         full_context_key = f"{prompt}_{files_hash}_{temperature}_{system_prompt}"
         # Remove and get the question_type
         removed_question_type = remove_cached_question(full_context_key, question_to_delete)
         if not removed_question_type:
             # Fallback: check if question has type field or use cached type
             removed_question_type = question_to_delete.get("type", question_to_delete.get("_cached_type", "single_choice"))

    # 2. Add Replacement Task
    
    # Snapshot existing hashes for deduplication
    existing_content_hashes = set()
    for q in exam["questions"]:
         q_content = {k: v for k, v in q.items() if k not in ['id', '_cached_type']}
         q_json = json.dumps(q_content, ensure_ascii=False, sort_keys=True)
         existing_content_hashes.add(hashlib.md5(q_json.encode()).hexdigest())

    background_tasks.add_task(
        regenerate_question_async, 
        exam_id, 
        system_prompt, 
        prompt, 
        temperature, 
        existing_content_hashes,
        files_hash,
        removed_question_type,  # Pass the type to regenerate
        subject
    )
    
    # 3. Return immediately
    return {"success": True, "message": f"Question deleted, regenerating replacement (type: {removed_question_type})..."}



@router.post("/exam/{exam_id}/submit")
async def submit_exam(exam_id: str, request: SubmitExamRequest, background_tasks: BackgroundTasks):
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
        
        # Determine correctness based on type
        is_correct = False
        q_type = q.get("type", "single_choice")
        
        try:
            if "multi" in q_type:
                # Multi choice: compare sorted lists of strings
                correct_arr = q.get("correct_answers", [])
                student_arr = student_answer if isinstance(student_answer, list) else []
                # Convert all to string for comparison
                c_set = sorted([str(x) for x in correct_arr])
                s_set = sorted([str(x) for x in student_arr])
                is_correct = c_set == s_set
                
            elif "fill_in" in q_type:
                # Fill in blanks: compare list of strings
                correct_arr = q.get("correct_answers", [])
                student_arr = student_answer if isinstance(student_answer, list) else []
                
                if len(correct_arr) == len(student_arr):
                    # Check matching (case insensitive)
                    is_correct = all(str(a).strip().lower() == str(b).strip().lower() 
                                   for a, b in zip(correct_arr, student_arr))
            else:
                # Single choice: compare single value (int or string)
                correct_val = q.get("correct_answer")
                is_correct = str(student_answer) == str(correct_val)
        except Exception:
            is_correct = False

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

    # AI Performance Analysis
    students_db[exam_id].append(result)
    result_index = len(students_db[exam_id]) - 1

    # Broadcast new submission to teacher
    await sse_manager.broadcast(exam_id, {
        "type": "new_submission",
        "data": result
    })

    if request.chat_history:
        background_tasks.add_task(
            run_exam_analysis,
            exam_id,
            result_index,
            request.student_name,
            correct,
            total,
            request.chat_history
        )
    
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
