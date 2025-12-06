"""
Fill in the Blanks Question Generator.

Generates fill-in-the-blank questions.
"""
import json
from typing import Optional
from app.generators.base import BaseQuestionGenerator




from app.generators.schemas import GenFillInBlanksQuestion, FillInBlanksQuestion

class FillInBlanksGenerator(BaseQuestionGenerator):
    """Generator for fill-in-blanks questions."""
    
    question_type = "fill_in_blanks"
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo bài tập điền từ.

Tạo câu hỏi điền từ với:
- 1 đoạn văn hoặc câu có các chỗ trống: BẮT BUỘC dùng đúng 3 dấu gạch dưới '___' cho mỗi chỗ trống.
- Danh sách các từ chính xác để điền vào (correct_answers)
- Số lượng chỗ trống phải khớp với số lượng đáp án
- Giải thích chi tiết

QUAN TRỌNG:
- CHÚ Ý TUYỆT ĐỐI về chỗ trống: PHẢI là đúng 3 dấu gạch dưới '___'. KHÔNG dùng '____', '__', '....' hay '[...]'. UI chỉ nhận diện đúng 3 dấu gạch dưới '___'.
- Nếu chủ đề là TIẾNG ANH: Nội dung đoạn văn/câu hỏi (text) và từ cần điền (correct_answers) viết bằng TIẾNG ANH. Giải thích (explanation) viết bằng TIẾNG VIỆT.
- Nếu chủ đề khác: Viết toàn bộ bằng TIẾNG VIỆT.

Sử dụng format strict JSON cho GenFillInBlanksQuestion."""


    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        **kwargs
    ) -> Optional[FillInBlanksQuestion]:
        """Generate a fill-in-blanks question."""
        
        user_prompt = f"Tạo 1 bài tập điền từ về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenFillInBlanksQuestion,
            temperature=temperature
        )
        
        if gen_question:
            return FillInBlanksQuestion(
                id=question_id,
                type="fill_in_blanks",
                **gen_question.model_dump()
            )
            
        return None


# Singleton instance
fill_in_blanks_generator = FillInBlanksGenerator()
