"""
Image Multi Choice Question Generator.

Generates image-based multiple choice questions.
"""
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import GenImageMultiChoiceQuestion, ImageMultiChoiceQuestion
from app.services.image_service import search_and_get_image

class ImageMultiChoiceGenerator(BaseQuestionGenerator):
    """Generator for image multiple choice questions."""
    
    question_type = "image_multi_choice"

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        generate_media: bool = True,
        **kwargs
    ) -> Optional[ImageMultiChoiceQuestion]:
        """Generate an image multi choice question."""
        
        user_prompt = f"Tạo 1 câu hỏi trắc nghiệm (nhiều đáp án) có hình ảnh về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenImageMultiChoiceQuestion,
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
                
            return ImageMultiChoiceQuestion(
                id=question_id,
                type="image_multi_choice",
                image_url=image_url,
                **gen_question.model_dump()
            )
        except Exception as e:
            print(f"❌ Error processing image multi choice: {e}")
            return None

# Singleton instance
image_multi_choice_generator = ImageMultiChoiceGenerator()
