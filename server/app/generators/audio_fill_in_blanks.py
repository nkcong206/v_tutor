"""
Audio Fill In Blanks Question Generator.

Generates audio-based fill-in-the-blank questions.
"""
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import GenAudioFillInBlanksQuestion, AudioFillInBlanksQuestion
from app.services.tts_generator import generate_and_save_audio, generate_audio_from_script
import uuid

class AudioFillInBlanksGenerator(BaseQuestionGenerator):
    """Generator for audio fill in the blanks questions."""
    
    question_type = "audio_fill_in_blanks"
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo câu hỏi luyện nghe điền từ (Audio Fill in Blanks) Tiếng Anh.

Tạo câu hỏi gồm:
- audio_script: Danh sách các đoạn hội thoại (DialogueSegment). Mỗi đoạn gồm:
  + voice: Chọn 1 trong [alloy, echo, fable, onyx, nova, shimmer].
  + text: Lời thoại Tiếng Anh.
- text: 1 câu/đoạn văn (text) có các chỗ trống. BẮT BUỘC dùng đúng 3 dấu gạch dưới '___'.
- blanks_count: Số lượng chỗ trống
- correct_answers: Danh sách đáp án đúng
- explanation: Giải thích chi tiết (Bằng Tiếng Việt)

QUAN TRỌNG:
- CHÚ Ý TUYỆT ĐỐI về chỗ trống: PHẢI là đúng 3 dấu gạch dưới '___'. KHÔNG dùng '____', '__' hay '[...]'. UI chỉ nhận diện đúng 3 dấu gạch dưới '___'.
- Kịch bản audio (audio_script) nên là hội thoại tự nhiên hoặc đoạn văn đọc rõ ràng.
- Độ dài NGẮN GỌN (khoảng 3-4 câu hoặc 30-50 từ).
- text (với blank): TIẾNG ANH.
- correct_answers: TIẾNG ANH.
- explanation: TIẾNG VIỆT.

Sử dụng format strict JSON cho GenAudioFillInBlanksQuestion."""

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        generate_media: bool = True,
        **kwargs
    ) -> Optional[AudioFillInBlanksQuestion]:
        """Generate an audio fill in the blanks question."""
        
        user_prompt = f"Tạo 1 câu hỏi luyện nghe điền từ (fill in blanks) về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenAudioFillInBlanksQuestion,
            temperature=temperature
        )
        
        if not gen_question:
            return None
            
        try:
             # Generate audio from script
            audio_url = None
            if generate_media and gen_question.audio_script:
                audio_filename = f"q_{question_id}_{uuid.uuid4().hex[:8]}"
                audio_url = await generate_audio_from_script(
                    script=gen_question.audio_script,
                    filename=audio_filename
                )
                
            return AudioFillInBlanksQuestion(
                id=question_id,
                type="audio_fill_in_blanks",
                audio_url=audio_url,
                **gen_question.model_dump()
            )
        except Exception as e:
            print(f"❌ Error processing audio fill in blanks: {e}")
            return None

# Singleton instance
audio_fill_in_blanks_generator = AudioFillInBlanksGenerator()
