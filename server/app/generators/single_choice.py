"""
Single Choice Question Generator.

Generates text-only single choice questions.
"""
import json
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import letter_to_index



from app.generators.schemas import GenSingleChoiceQuestion, SingleChoiceQuestion

class SingleChoiceGenerator(BaseQuestionGenerator):
    """Generator for single choice questions."""
    
    question_type = "single_choice"
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo câu hỏi trắc nghiệm chất lượng cao.

Tạo câu hỏi trắc nghiệm với:
- 1 câu hỏi rõ ràng, chính xác
- 4 đáp án (KHÔNG có ký tự A, B, C, D phía trước - CHỈ nội dung đáp án)
- Chỉ có 1 đáp án đúng
- correct_answer là vị trí 0-based (0 = đáp án đầu tiên, 1 = đáp án thứ 2, ...)
- Giải thích chi tiết tại sao đáp án đó đúng

QUAN TRỌNG:
- Nếu chủ đề là TIẾNG ANH: Nội dung câu hỏi (text) và đáp án (options) viết bằng TIẾNG ANH. Giải thích (explanation) viết bằng TIẾNG VIỆT.
- Nếu chủ đề khác: Viết toàn bộ bằng TIẾNG VIỆT.
- Luôn đảm bảo giải thích chi tiết, dễ hiểu.

Sử dụng format strict JSON cho SingleChoiceQuestion."""

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        **kwargs
    ) -> Optional[SingleChoiceQuestion]:
        """Generate a single choice question."""
        
        user_prompt = f"Tạo 1 câu hỏi trắc nghiệm về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        # Use new structured generation with GEN schema (no 'type' field)
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenSingleChoiceQuestion, # Use GEN schema
            temperature=temperature
        )
        
        if gen_question:
            # Convert to FULL schema (inject type and ID)
            return SingleChoiceQuestion(
                id=question_id,
                type="single_choice",
                **gen_question.model_dump()
            )
            
        return None


# Singleton instance
single_choice_generator = SingleChoiceGenerator()
