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

