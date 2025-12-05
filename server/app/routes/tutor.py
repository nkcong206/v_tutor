from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
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
    selected_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    attempt_count: int = 0


class TutorChatResponse(BaseModel):
    response: str
    suggested_prompts: List[str]


# Structured output model for AI response
class TutorAIResponse(BaseModel):
    """Structured response from AI Tutor"""
    message: str
    suggestions: List[str]  # Exactly 4 suggestions that quiz the student


def get_system_prompt(question_text: str, options: List[str], selected_answer: Optional[str], 
                      correct_answer: Optional[str], is_correct: Optional[bool], attempt_count: int) -> str:
    options_text = "\n".join(options)
    
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

    return f"""Bạn là AI Tutor, trợ lý học tập thân thiện và kiên nhẫn.

CÂU HỎI ĐANG LÀM:
{question_text}

CÁC ĐÁP ÁN:
{options_text}

{status_info}

NGUYÊN TẮC QUAN TRỌNG - BẮT BUỘC TUÂN THỦ:
1. TUYỆT ĐỐI KHÔNG BAO GIỜ đưa ra đáp án trực tiếp (A, B, C, D)
2. KHÔNG nói "đáp án đúng là..." hay "em nên chọn..."
3. Hướng dẫn học sinh từng bước tư duy để tự tìm ra đáp án

CÁCH PHẢN HỒI THEO TRẠNG THÁI:
- Nếu học sinh CHƯA chọn đáp án: Hỏi học sinh đã hiểu đề chưa, gợi ý cách phân tích
- Nếu học sinh chọn ĐÚNG: Khen và hỏi em có thể giải thích vì sao em chọn đáp án này không?
- Nếu học sinh chọn SAI: Hãy khuyên học sinh chọn lại đáp án

GIỌNG VĂN:
- Thân thiện, gần gũi như anh/chị
- Dùng emoji phù hợp
- Động viên khi học sinh gặp khó khăn
- Ngắn gọn (tối đa 2-3 câu)

OUTPUT FORMAT (JSON ONLY):
Bạn bắt buộc phải trả về JSON format như sau (không thêm text nào khác):
{{
  "message": "Nội dung phản hồi của AI...",
  "suggestions": ["Gợi ý 1...", "Gợi ý 2...", "Gợi ý 3...", "Gợi ý 4..."]
}}

VỀ SUGGESTIONS (CỰC KỲ QUAN TRỌNG):
Bạn PHẢI tạo ĐÚNG 4 suggestions RẤT NGẮN GỌN (mỗi cái tối đa 5-7 từ).
Các suggestions này là các câu hỏi/lựa chọn để ĐÁNH ĐỐ học sinh:
- Nếu học sinh SAI: Đưa 4 hướng suy nghĩ, trong đó chỉ có 1-2 hướng đúng, còn lại là bẫy để xem học sinh có thực sự hiểu không
- Nếu học sinh ĐÚNG: Đưa 4 cách giải thích, trong đó có cả cách đúng và sai để kiểm tra hiểu biết
- Mục đích: Nếu học sinh chọn suggestion sai → họ chưa thực sự hiểu bài

Ví dụ với câu "Số nào lớn hơn 5?":
- Nếu sai: ["Số bé hơn 5", "Số lớn hơn 5", "Số bằng 5", "Số âm"]
- Nếu đúng: ["Vì 6 > 5", "Vì 6 < 5", "Vì 6 = 5", "Vì 6 là số chẵn"]"""



    
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
            request.attempt_count
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
                # Use Beta Parse for Structured Output
                response = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4000, # Increased to 4000 to prevent 'length limit reached'
                    response_format=TutorAIResponse
                )
                
                final_response_obj = response.choices[0].message.parsed
                
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
