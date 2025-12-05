from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from openai import OpenAI
from app.config import settings
from datetime import datetime

router = APIRouter(tags=["Tutor"])

# Configure OpenAI
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
    is_correct: Optional[bool] = None
    attempt_count: int = 0


class TutorChatResponse(BaseModel):
    response: str
    suggested_prompts: List[str]


def get_system_prompt(question_text: str, options: List[str], selected_answer: Optional[str], 
                      is_correct: Optional[bool], attempt_count: int) -> str:
    options_text = "\n".join(options)
    
    status_info = ""
    if selected_answer:
        status_info = f"""
TRẠNG THÁI HIỆN TẠI:
- Học sinh đã chọn: {selected_answer}
- Kết quả: {"ĐÚNG" if is_correct else "SAI"}
- Số lần thử: {attempt_count}
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
- Nếu học sinh chọn ĐÚNG: "Tốt lắm! Nhưng em có thể giải thích vì sao em chọn đáp án này không?"
- Nếu học sinh chọn SAI lần 1: "Hmm, chưa đúng lắm. Em thử suy nghĩ lại xem, hãy đọc kỹ đề bài nhé!"
- Nếu học sinh SAI lần 2+: Đưa gợi ý cụ thể hơn về kiến thức cần áp dụng (nhưng KHÔNG nói đáp án)

GIỌNG VĂN:
- Thân thiện, gần gũi như anh/chị
- Dùng emoji phù hợp
- Động viên khi học sinh gặp khó khăn
- Ngắn gọn, không dài dòng (tối đa 2-3 câu)"""


def get_suggested_prompts(is_correct: Optional[bool], attempt_count: int) -> List[str]:
    if is_correct is None:
        return [
            "Em chưa hiểu đề bài lắm",
            "Giải thích từ khóa trong đề",
            "Gợi ý cách làm"
        ]
    elif is_correct:
        return [
            "Em chọn vì thấy hợp lý nhất",
            "Em dùng phương pháp loại trừ",
            "Giải thích thêm cho em"
        ]
    else:
        if attempt_count >= 2:
            return [
                "Cho em gợi ý thêm",
                "Kiến thức nào cần dùng?",
                "Em vẫn chưa hiểu"
            ]
        return [
            "Em thử lại nhé",
            "Gợi ý cho em cách suy nghĩ",
            "Đề bài có từ khóa gì quan trọng?"
        ]


@router.post("/chat", response_model=TutorChatResponse)
async def tutor_chat(request: TutorChatRequest):
    """
    AI Tutor chat endpoint - guides students without giving direct answers
    """
    try:
        # Create chat key
        chat_key = f"{request.exam_id}_{request.student_name}"
        
        # Initialize chat history if needed
        if chat_key not in tutor_chats_db:
            tutor_chats_db[chat_key] = []
        
        # Get system prompt
        system_prompt = get_system_prompt(
            request.question_text,
            request.options,
            request.selected_answer,
            request.is_correct,
            request.attempt_count
        )
        
        # Build messages for API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent chat history (last 6 messages to keep context manageable)
        recent_history = tutor_chats_db[chat_key][-6:]
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        ai_response = response.choices[0].message.content.strip()
        
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
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get suggested prompts
        suggested = get_suggested_prompts(request.is_correct, request.attempt_count)
        
        return TutorChatResponse(
            response=ai_response,
            suggested_prompts=suggested
        )
        
    except Exception as e:
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
