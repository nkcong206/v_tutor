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
        return """Bạn là giáo viên chuyên tạo bài tập điền từ cho học sinh tiểu học.

⚠️ YÊU CẦU QUAN TRỌNG NHẤT: CÂU HỎI PHẢI LIÊN QUAN TRỰC TIẾP ĐẾN CHỦ ĐỀ ĐƯỢC YÊU CẦU!

Tạo câu hỏi điền từ với:
- 1 đoạn văn hoặc câu có 1-3 chỗ trống (không quá nhiều)
- BẮT BUỘC dùng đúng 3 dấu gạch dưới '___' cho mỗi chỗ trống
- Nội dung PHẢI liên quan trực tiếp đến môn học/chủ đề
- Danh sách các từ chính xác để điền (correct_answers)
- Số lượng chỗ trống phải khớp với số lượng đáp án
- Giải thích chi tiết

VÍ DỤ THEO MÔN HỌC:

📚 TIẾNG ANH:
- Chủ đề "Fruits": "I like to eat ___. Apples are ___." → ["bananas", "sweet"]
- Chủ đề "Animals": "A ___ says meow. A ___ barks." → ["cat", "dog"]
- Chủ đề "Colors": "The sky is ___. Grass is ___." → ["blue", "green"]

📐 TOÁN:
- Chủ đề "Phép cộng": "5 + 3 = ___" → ["8"]
- Chủ đề "Hình học": "Hình vuông có ___ cạnh bằng nhau." → ["4"]
- Chủ đề "So sánh": "10 ___ 5 (lớn hơn/nhỏ hơn)" → ["lớn hơn"]

📖 TIẾNG VIỆT:
- Chủ đề "Từ vựng": "Mặt trời mọc ở hướng ___." → ["Đông"]
- Chủ đề "Ngữ pháp": "Hoa ___ rất thơm." → ["hồng"]

CHÚ Ý:
- PHẢI dùng đúng 3 dấu gạch dưới '___'. KHÔNG dùng '____', '__', '....'
- Nếu chủ đề là TIẾNG ANH: text và correct_answers bằng TIẾNG ANH, explanation bằng TIẾNG VIỆT.
- Nếu chủ đề khác: Viết toàn bộ bằng TIẾNG VIỆT.
- CÂU HỎI PHẢI ĐÚNG CHỦ ĐỀ - đây là yêu cầu quan trọng nhất!

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
        
        # Enhanced prompt with topic emphasis
        user_prompt = f"""CHỦ ĐỀ BẮT BUỘC: {prompt}

Hãy tạo 1 bài tập điền từ TRỰC TIẾP liên quan đến chủ đề "{prompt}".
Từ cần điền phải là từ khóa quan trọng của chủ đề này."""

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

