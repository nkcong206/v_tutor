"""
Multi Choice Question Generator.

Generates text-only multiple choice questions (select all that apply).
"""
import json
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import letter_to_index, GenMultiChoiceQuestion, MultiChoiceQuestion


class MultiChoiceGenerator(BaseQuestionGenerator):
    """Generator for multiple choice questions."""
    
    question_type = "multi_choice"
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo câu hỏi trắc nghiệm nhiều đáp án đúng.

Tạo câu hỏi trắc nghiệm với:
- Câu hỏi yêu cầu chọn nhiều phương án
- 4-5 lựa chọn
- Danh sách correct_answers chứa các chỉ số (0-based) của đáp án đúng
- Giải thích chi tiết

QUAN TRỌNG:
- Nếu chủ đề là TIẾNG ANH: Nội dung câu hỏi (text) và đáp án (options) viết bằng TIẾNG ANH. Giải thích (explanation) viết bằng TIẾNG VIỆT.
- Nếu chủ đề khác: Viết toàn bộ bằng TIẾNG VIỆT.

Sử dụng format strict JSON cho GenMultiChoiceQuestion."""

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        **kwargs
    ) -> Optional[MultiChoiceQuestion]:
        """Generate a multiple choice question."""
        
        user_prompt = f"Tạo 1 câu hỏi trắc nghiệm nhiều lựa chọn về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenMultiChoiceQuestion,
            temperature=temperature
        )
        
        if gen_question:
            return MultiChoiceQuestion(
                id=question_id,
                type="multi_choice",
                **gen_question.model_dump()
            )
            
        return None


# Singleton instance
multi_choice_generator = MultiChoiceGenerator()
