"""
Audio Single Choice Question Generator.

Generates questions with AI-generated audio + single choice answers.
"""
import json
import uuid
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import GenAudioSingleChoiceQuestion, AudioSingleChoiceQuestion, letter_to_index
from app.services.tts_generator import generate_and_save_audio, generate_audio_from_script

# ...

class AudioSingleChoiceGenerator(BaseQuestionGenerator):
    """Generator for audio + single choice questions."""
    
    question_type = "audio_single_choice"
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo câu hỏi nghe hiểu Tiếng Anh (Audio Single Choice).
        
Tạo câu hỏi gồm:
- audio_script: Danh sách các đoạn hội thoại (DialogueSegment). Mỗi đoạn gồm:
  + voice: Chọn 1 trong [alloy, echo, fable, onyx, nova, shimmer].
  + text: Lời thoại Tiếng Anh.
- text: 1 câu hỏi về nội dung nghe (text)
- options: 4 đáp án lựa chọn
- correct_answer: vị trí 0-based
- explanation: Giải thích chi tiết (Bằng Tiếng Việt)

QUAN TRỌNG: 
- Kịch bản audio (audio_script) phải tự nhiên.
- Độ dài hội thoại NGẮN GỌN (khoảng 3-4 câu thoại).
- Câu hỏi và đáp án nên là TIẾNG ANH.
- Giải thích PHẢI là TIẾNG VIỆT.

Sử dụng format strict JSON for GenAudioSingleChoiceQuestion."""

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        generate_media: bool = True,
        **kwargs
    ) -> Optional[AudioSingleChoiceQuestion]:
        """Generate an audio + single choice question."""
        
        user_prompt = f"Tạo 1 câu hỏi nghe hiểu về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        # Use structured generation with GEN schema
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenAudioSingleChoiceQuestion,
            temperature=temperature
        )
        
        if not gen_question:
            return None
        
        try:
            # Generate audio if requested
            audio_url = None
            if generate_media and gen_question.audio_script:
                audio_filename = f"q_{question_id}_{uuid.uuid4().hex[:8]}"
                audio_url = await generate_audio_from_script(
                    script=gen_question.audio_script,
                    filename=audio_filename
                )
            
            # Convert to FULL schema (inject type, ID, audio_url)
            return AudioSingleChoiceQuestion(
                id=question_id,
                type="audio_single_choice",
                audio_url=audio_url,
                **gen_question.model_dump()
            )
        except Exception as e:
            print(f"❌ Error processing generated question: {e}")
            return None


# Singleton instance
audio_single_choice_generator = AudioSingleChoiceGenerator()

