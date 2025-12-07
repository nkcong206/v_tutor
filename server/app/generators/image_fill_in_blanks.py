"""
Image Fill In Blanks Question Generator.

Generates image-based fill-in-the-blank questions.
"""
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import GenImageFillInBlanksQuestion, ImageFillInBlanksQuestion
from app.services.image_service import search_and_get_image

class ImageFillInBlanksGenerator(BaseQuestionGenerator):
    """Generator for image fill in the blanks questions."""
    
    question_type = "image_fill_in_blanks"

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        generate_media: bool = True,
        **kwargs
    ) -> Optional[ImageFillInBlanksQuestion]:
        """Generate an image fill in the blanks question."""
        
        user_prompt = f"Tạo 1 câu hỏi điền vào chỗ trống có hình ảnh về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenImageFillInBlanksQuestion,
            temperature=temperature
        )
        
        if not gen_question:
            return None
            
        try:
             # Generate/Search image
            image_url = None
            if generate_media and gen_question.image_prompt:
                image_url = await search_and_get_image(gen_question.image_prompt)
                
                if not image_url:
                     print(f"❌ Failed to get image for prompt: {gen_question.image_prompt}")
                     return None
                
            return ImageFillInBlanksQuestion(
                id=question_id,
                type="image_fill_in_blanks",
                image_url=image_url,
                **gen_question.model_dump()
            )
        except Exception as e:
            print(f"❌ Error processing image fill in blanks: {e}")
            return None

# Singleton instance
image_fill_in_blanks_generator = ImageFillInBlanksGenerator()
