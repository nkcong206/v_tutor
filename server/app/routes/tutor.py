from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Union
from app.config import settings
from datetime import datetime
import json
import time
import re

# Use standard client for manual caching
from openai import OpenAI

router = APIRouter(tags=["Tutor"])

# Configure standard client
client = OpenAI(api_key=settings.openai_api_key)

# In-memory storage for chat history
tutor_chats_db: Dict[str, List[dict]] = {}  # key: exam_id_student_name -> list of messages


class TutorChatRequest(BaseModel):
    exam_id: str
    question_id: int
    student_name: str
    message: str
    question_text: str
    options: List[str]
    selected_answer: Optional[Union[str, int, List[str], List[int]]] = None
    correct_answer: Optional[Union[str, int, List[str], List[int]]] = None
    is_correct: Optional[bool] = None
    attempt_count: int = 0
    image_description: Optional[str] = None
    audio_script_text: Optional[str] = None


class TutorChatResponse(BaseModel):
    response: str
    suggested_prompts: List[str]


# Structured output model for AI response
class TutorAIResponse(BaseModel):
    """Structured response from AI Tutor"""
    message: str
    suggestions: List[str]  # Exactly 4 suggestions that quiz the student


def get_system_prompt(question_text: str, options: List[str], selected_answer: Optional[Union[str, int, List[str], List[int]]], 
                      correct_answer: Optional[Union[str, int, List[str], List[int]]], is_correct: Optional[bool], attempt_count: int,
                      image_description: Optional[str] = None, audio_script_text: Optional[str] = None) -> str:
    options_text = "\n".join(options)
    
    context_info = ""
    if image_description:
         context_info += f"\n\nMÔ TẢ HÌNH ẢNH (Image Description):\n{image_description}"
    if audio_script_text:
         context_info += f"\n\nNỘI DUNG HỘI THOẠI (Transcript):\n{audio_script_text}"

    if is_correct is True:
        status_info = f"""
TRẠNG THÁI HIỆN TẠI: CHÍNH XÁC (CORRECT)
- Học sinh đã chọn: {selected_answer}
- Kết quả: ĐÚNG ✅
- Số lần thử: {attempt_count}

!!! KỊCH BẢN PHẢN HỒI KHI ĐÚNG !!!
Bạn phải thể hiện sự vui mừng và phấn khích. Hãy dùng nhiều lời khen ngợi tích cực.
Mục tiêu là củng cố kiến thức và thách thức học sinh hiểu sâu hơn.
Hãy yêu cầu giải thích "Tại sao lại chọn như vậy?" để đảm bảo không phải đoán mò.
"""
    elif is_correct is False:
        status_info = f"""
TRẠNG THÁI HIỆN TẠI: SAI (INCORRECT)
- Học sinh đã chọn: {selected_answer}
- Kết quả: SAI ❌
- Số lần thử: {attempt_count}

!!! KỊCH BẢN PHẢN HỒI KHI SAI !!!
Bạn phải thật sự kiên nhẫn và đồng cảm. Đừng chỉ trích.
Hãy đưa ra gợi ý, manh mối, hoặc ví dụ tương tự.
Mục tiêu là hướng dẫn học sinh nhận ra lỗi sai của mình.
Hãy hỏi những câu hỏi dẫn dắt để học sinh tự sửa.
"""
    else:
        status_info = f"""
TRẠNG THÁI HIỆN TẠI: CHƯA LÀM
- Học sinh đang đọc đề.
"""

    # Load template from YAML and fill in dynamic placeholders
    from app.services.prompt_management import get_system_prompt as get_prompt
    return get_prompt(
        "tutor_chat",
        question_text=question_text,
        context_info=context_info,
        options_text=options_text,
        status_info=status_info
    )



    
@router.post("/chat", response_model=TutorChatResponse)
async def tutor_chat(request: TutorChatRequest):
    """
    AI Tutor chat endpoint - guides students without giving direct answers
    Uses structured output for dynamic suggestions with caching
    """
    import time
    
    try:
        start_time = time.time()
        
        # Create chat key
        chat_key = f"{request.exam_id}_{request.student_name}"
        
        # Initialize chat history if needed
        if chat_key not in tutor_chats_db:
            tutor_chats_db[chat_key] = []
        
        # Get recent history for context (last 10 messages)
        recent_history = tutor_chats_db[chat_key][-10:]
        
        # Get system prompt
        system_prompt = get_system_prompt(
            request.question_text,
            request.options,
            request.selected_answer,
            request.correct_answer,
            request.is_correct,
            request.attempt_count,
            request.image_description,
            request.audio_script_text
        )
        
        # Build messages for API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # --- Manual Caching Implementation ---
        from app.services.semantic_cache import get_cached_response, save_to_cache
        
        if request.message.startswith("[Học sinh chọn:") or request.message.startswith("[Student selected:"):
            status_str = "CORRECT" if request.is_correct else "WRONG"
            # REPEAT status to force semantic difference, and TRUNCATE question to reduce noise
            # Structure: STATUS (x3) | ANSWER | QUESTION (first 100 chars)
            messages_key = f"SCENARIO_STATUS: {status_str} {status_str} {status_str} | ANSWER: {request.selected_answer} | Q: {request.question_text[:100]}"
            print(f"🔑 Using Optimized Cache Key: {messages_key}")
            
            # Use EXACT match lookup (Hash Cache)
            cached_json = get_cached_response(messages_key)
        else:
            # For normal chat, we need full history context
            # (Note: History injection removed, now stateless)
            # CRITICAL FIX: Prefix with LATEST USER MESSAGE to avoid truncation issues with long history
            # The embedding model might truncate the end of long JSON, missing the new question.
            messages_key = f"LATEST_USER_MSG: {request.message} ||| HISTORY_JSON: {json.dumps(messages, ensure_ascii=False)}"
            
            # Use EXACT match lookup (Hash Cache)
            cached_json = get_cached_response(messages_key)
        final_response_obj = None
        
        if cached_json:
            elapsed = time.time() - start_time
            print(f"✅ TUTOR CACHE HIT | Time: {elapsed:.3f}s")
            try:
                final_response_obj = TutorAIResponse.model_validate_json(cached_json)
            except Exception as e:
                print(f"⚠️ Cache parse error: {e}")
        
        if not final_response_obj:
            # Cache Miss
            try:
                # Use Structured Service
                from app.services.llm_service import llm_service
                
                # Reconstruct prompts for the service interface
                # Note: llm_service expects (sys, user) strings, but here we have messages list for history.
                
                sys_msg = messages[0]["content"]
                usr_msg = messages[1]["content"] if len(messages) > 1 else ""
                
                final_response_obj = llm_service.generate_response(
                    response_model=TutorAIResponse,
                    system_prompt=sys_msg,
                    user_prompt=usr_msg,
                    temperature=0.7,
                    max_tokens=4000
                )
                
                elapsed = time.time() - start_time
                print(f"❌ TUTOR CACHE MISS | Time: {elapsed:.3f}s")
                
                if final_response_obj:
                    save_to_cache(messages_key, final_response_obj.model_dump_json())
                    
            except Exception as e:
                print(f"ERROR OpenAI: {str(e)}")
                raise e

        # Extract data
        ai_message = final_response_obj.message
        suggestions = final_response_obj.suggestions

        # Ensure we have exactly 4 suggestions
        if not isinstance(suggestions, list):
            suggestions = []
        while len(suggestions) < 4:
            suggestions.append("Hỏi thêm")
        suggestions = suggestions[:4]
 
        # Save to history
        tutor_chats_db[chat_key].append({
            "role": "user",
            "content": request.message,
            "question_id": request.question_id,
            "selected_answer": request.selected_answer,
            "is_correct": request.is_correct,
            "timestamp": datetime.now().isoformat()
        })
        tutor_chats_db[chat_key].append({
            "role": "assistant",
            "content": ai_message,
            "timestamp": datetime.now().isoformat()
        })
        
        return TutorChatResponse(
            response=ai_message,
            suggested_prompts=suggestions
        )
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi AI Tutor: {str(e)}")


from fastapi.responses import StreamingResponse

@router.post("/stream")
async def tutor_chat_stream(request: TutorChatRequest):
    """
    Streaming AI Tutor chat endpoint.
    Streams the text response first, followed by a delimiter '|||SUGGESTIONS|||',
    then the JSON array of suggestions.
    """
    import json
    
    # Create chat key for history
    chat_key = f"{request.exam_id}_{request.student_name}"
    if chat_key not in tutor_chats_db:
        tutor_chats_db[chat_key] = []
    
    # Get system prompt
    system_prompt_content = get_system_prompt(
        request.question_text,
        request.options,
        request.selected_answer,
        request.correct_answer,
        request.is_correct,
        request.attempt_count,
        request.image_description,
        request.audio_script_text
    )
    
    # We want to force the model to output just the message text first, then suggestions.
    # We will tweak the prompt slightly for this specific streaming endpoint if needed,
    # OR we can just ask for the same JSON and parse it manually?
    # Parsing broken JSON while streaming is hard.
    # EASY WAY: Ask for plain text first, then a delimiter, then the suggestions list.
    
    stream_prompt = system_prompt_content.replace(
        "OUTPUT FORMAT (JSON ONLY):", 
        "OUTPUT FORMAT (STREAMING COMPATIBLE):"
    ).replace(
        """Bạn bắt buộc phải trả về JSON format như sau (không thêm text nào khác):
{
  "message": "Nội dung phản hồi của AI...",
  "suggestions": ["Gợi ý 1...", "Gợi ý 2...", "Gợi ý 3...", "Gợi ý 4..."]
}""",
        """Bạn hãy trả về kết quả theo đúng định dạng sau (quan trọng để hệ thống streaming hoạt động):

[Nội dung phản hồi của bạn]
|||SUGGESTIONS|||
["Gợi ý 1", "Gợi ý 2", "Gợi ý 3", "Gợi ý 4"]

Lưu ý:
1. Phần nội dung phản hồi viết bình thường (text).
2. Sau khi xong nội dung, bắt buộc xuống dòng và viết chính xác dòng: |||SUGGESTIONS|||
3. Sau dòng đó là một JSON Array chứa 4 gợi ý."""
    )
    
    messages = [{"role": "system", "content": stream_prompt}]
    
    # Add recent history (last 5 messages for context)
    recent_history = tutor_chats_db[chat_key][-5:]
    for msg in recent_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": request.message})
    
    async def generate_stream():
        full_response_text = ""
        
        try:
            stream = client.chat.completions.create(
                model="gpt-4o", # Or usage model from settings
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response_text += content
                    yield content

            # After streaming is done, we save to history
            # We need to parse out the message and suggestions to save properly
            parts = full_response_text.split("|||SUGGESTIONS|||")
            ai_message = parts[0].strip()
            suggestions = []
            if len(parts) > 1:
                try:
                    suggestions = json.loads(parts[1].strip())
                except:
                    pass
            
            # Save to history
            tutor_chats_db[chat_key].append({
                "role": "user",
                "content": request.message,
                "timestamp": datetime.now().isoformat()
            })
            tutor_chats_db[chat_key].append({
                "role": "assistant",
                "content": ai_message, # Save clean message
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            yield f"\n[Lỗi kết nối AI: {str(e)}]"

    return StreamingResponse(generate_stream(), media_type="text/plain")


@router.get("/history/{exam_id}/{student_name}")
async def get_chat_history(exam_id: str, student_name: str):
    """Get chat history for analytics"""
    chat_key = f"{exam_id}_{student_name}"
    return {
        "exam_id": exam_id,
        "student_name": student_name,
        "messages": tutor_chats_db.get(chat_key, []),
        "total_messages": len(tutor_chats_db.get(chat_key, []))
    }
