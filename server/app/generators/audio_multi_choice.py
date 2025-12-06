"""
Audio Multi Choice Question Generator.

Generates audio-based multiple choice questions.
"""
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import GenAudioMultiChoiceQuestion, AudioMultiChoiceQuestion
from app.services.tts_generator import generate_and_save_audio, generate_audio_from_script
import uuid

class AudioMultiChoiceGenerator(BaseQuestionGenerator):
    """Generator for audio multiple choice questions."""
    
    question_type = "audio_multi_choice"
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo câu hỏi luyện nghe (Audio) Tiếng Anh, đặc biệt là các đoạn hội thoại đa vai.

Tạo câu hỏi gồm:
- audio_script: Danh sách các đoạn hội thoại (DialogueSegment). Mỗi đoạn gồm:
  + voice: Chọn 1 trong [alloy, echo, fable, onyx, nova, shimmer]. Nên đổi giọng luân phiên (VD: Nam - Nữ).
  + text: Lời thoại Tiếng Anh.
- text: 1 câu hỏi liên quan đến nội dung nghe
- options: 4 đáp án
- correct_answers: danh sách index (0-based) các đáp án đúng
- explanation: Giải thích chi tiết (Bằng Tiếng Việt)

QUAN TRỌNG:
- Hãy tạo kịch bản hội thoại tự nhiên giữa 2 người trở lên.
- Độ dài hội thoại NGẮN GỌN (khoảng 3-4 câu thoại).
- Sử dụng format strict JSON cho GenAudioMultiChoiceQuestion."""

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        generate_media: bool = True,
        **kwargs
    ) -> Optional[AudioMultiChoiceQuestion]:
        """Generate an audio multi choice question."""
        
        user_prompt = f"Tạo 1 câu hỏi luyện nghe (nhiều đáp án) hội thoại về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenAudioMultiChoiceQuestion,
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
                
            return AudioMultiChoiceQuestion(
                id=question_id,
                type="audio_multi_choice",
                audio_url=audio_url,
                **gen_question.model_dump()
            )
        except Exception as e:
            print(f"❌ Error processing audio multi choice: {e}")
            return None


# Singleton instance
audio_multi_choice_generator = AudioMultiChoiceGenerator()
