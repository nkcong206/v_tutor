"""
AI Tutor Service using OpenAI
Provides intelligent hints without giving direct answers
"""

import openai
from typing import Dict, List, Optional
from app.config import settings
from datetime import datetime

# Configure Gemini
openai.api_key = settings.openai_api_key


class AITutorService:
    """Service for AI tutoring that guides students without giving answers"""
    
    def __init__(self):
        self.model = openai.OpenAI('gpt-4o-mini')
        # Store conversation context
        self.conversations: Dict[str, List[Dict]] = {}
    
    def get_tutor_response(
        self,
        session_id: int,
        question_id: int,
        student_message: str,
        current_answer: Optional[str],
        question_data: Dict,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Generate tutor response based on student's message
        
        Args:
            session_id: Current exam session ID
            question_id: Question being discussed
            student_message: Student's question or statement
            current_answer: Student's current answer choice
            question_data: Full question data including correct answer
            conversation_history: Previous messages in this conversation
        
        Returns:
            Dict with message, hint_type, and suggestions
        """
        
        # Build conversation context
        context_key = f"{session_id}_{question_id}"
        
        # Determine student's state
        is_answer_correct = False
        if current_answer:
            is_answer_correct = self._check_answer(
                current_answer, 
                question_data.get("correct_answer", "")
            )
        
        # Build system prompt
        system_prompt = f"""
BẠN LÀ MỘT GIÁO VIÊN DẠY HỌC THÔNG MINH.

QUY TẮC VÀNG:
1. KHÔNG BAO GIỜ đưa ra đáp án trực tiếp
2. Hướng dẫn học sinh TƯ DUY bằng cách:
   - Đặt câu hỏi gợi mở
   - Đưa ra gợi ý từng bước
   - Giải thích khái niệm liên quan
   - Khuyến khích học sinh tự suy nghĩ

3. Phát hiện và phản hồi trạng thái của học sinh:
   - Nếu học sinh chọn SAI → Hỏi "Tại sao em chọn đáp án này?"
   - Nếu học sinh giải thích SAI → Chỉ ra lỗ hổng trong suy luận
   - Nếu học sinh giải thích ĐÚNG → Khen ngợi và dẫn đến bước tiếp theo
   - Nếu học sinh BÍ → Đưa ra gợi ý về khái niệm cần dùng

4. TỰ ĐỘNG đưa ra gợi ý, KHÔNG đợi học sinh hỏi

THÔNG TIN BÀI TẬP:
Câu hỏi: {question_data.get('text', '')}
Các đáp án: {question_data.get('options', [])}

Đáp án của học sinh hiện tại: {current_answer if current_answer else 'Chưa chọn'}
Trạng thái: {'ĐÚNG' if is_answer_correct else 'SAI' if current_answer else 'Chưa trả lời'}

Lời giải đúng (CHỈ để bạn tham khảo, KHÔNG nói cho học sinh):
{question_data.get('solution', '')}

Khái niệm cần biết:
{question_data.get('explanation', '')}
"""
        
        # Build conversation history for context
        history_text = "\n".join([
            f"{'Học sinh' if msg['role'] == 'student' else 'AI'}: {msg['content']}"
            for msg in conversation_history[-5:]  # Last 5 messages
        ])
        
        # Create user prompt
        user_prompt = f"""
LỊCH SỬ HỘI THOẠI:
{history_text}

TIN NHẮN MỚI TỪ HỌC SINH:
{student_message}

NHIỆM VỤ CỦA BẠN:
Phản hồi học sinh với 1 trong các kiểu sau:

1. "concept" - Giải thích khái niệm khi học sinh chưa hiểu nền tảng
2. "step" - Gợi ý bước tiếp theo trong quá trình giải
3. "clarification" - Làm rõ khi học sinh hiểu sai
4. "encouragement" - Động viên khi học sinh làm đúng

Trả về JSON theo format:
{{
  "message": "Tin nhắn của bạn cho học sinh (thân thiện, dễ hiểu)",
  "hint_type": "concept|step|clarification|encouragement",
  "suggestions": ["Gợi ý 1 học sinh có thể hỏi", "Gợi ý 2...", "Gợi ý 3..."]
}}

Hãy phản hồi NGAY:
"""
        
        try:
            # Generate response
            response = self.model.generate_content(system_prompt + "\n\n" + user_prompt)
            result_text = response.text.strip()
            
            # Clean JSON
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            import json
            data = json.loads(result_text.strip())
            
            return {
                "message": data.get("message", "Hãy thử suy nghĩ thêm nhé!"),
                "hint_type": data.get("hint_type", "step"),
                "suggestions": data.get("suggestions", [
                    "Em chưa hiểu khái niệm này, thầy giải thích được không?",
                    "Bước tiếp theo em cần làm gì?",
                    "Em suy nghĩ đúng rồi phải không thầy?"
                ])
            }
            
        except Exception as e:
            print(f"Error in tutor response: {e}")
            # Fallback response
            if is_answer_correct:
                return {
                    "message": "Tuyệt vời! Em đã chọn đúng. Hãy giải thích tại sao em chọn đáp án này nhé!",
                    "hint_type": "encouragement",
                    "suggestions": [
                        "Em chọn vì...",
                        "Em áp dụng công thức...",
                        "Sang câu tiếp theo"
                    ]
                }
            elif current_answer:
                return {
                    "message": "Hmm, đáp án này có vẻ chưa chính xác. Em có thể giải thích tại sao em chọn đáp án này không?",
                    "hint_type": "clarification",
                    "suggestions": [
                        "Em chọn vì...",
                        "Em nghĩ rằng...",
                        "Cho em gợi ý thêm"
                    ]
                }
            else:
                return {
                    "message": "Hãy thử đọc kỹ đề bài và suy nghĩ về khái niệm liên quan nhé!",
                    "hint_type": "concept",
                    "suggestions": [
                        "Khái niệm nào liên quan đến bài này?",
                        "Công thức cần dùng là gì?",
                        "Cho em một gợi ý"
                    ]
                }
    
    def _check_answer(self, student_answer: str, correct_answer: str) -> bool:
        """Check if student answer matches correct answer"""
        # Normalize answers for comparison
        student = student_answer.strip().upper()
        correct = correct_answer.strip().upper()
        
        # Handle multiple choice (A, B, C, D)
        if len(student) == 1 and len(correct) == 1:
            return student == correct
        
        # Handle text answers
        return student == correct
    
    def analyze_conversation(self, conversation_history: List[Dict]) -> Dict:
        """Analyze conversation for insights"""
        total_messages = len(conversation_history)
        student_questions = [m for m in conversation_history if m["role"] == "student"]
        
        # Count hint types
        hint_types = {}
        for msg in conversation_history:
            if msg["role"] == "ai" and "hint_type" in msg:
                hint_type = msg["hint_type"]
                hint_types[hint_type] = hint_types.get(hint_type, 0) + 1
        
        return {
            "total_messages": total_messages,
            "student_questions_count": len(student_questions),
            "hints_given": hint_types,
            "conversation_length": sum(len(m["content"]) for m in conversation_history)
        }
