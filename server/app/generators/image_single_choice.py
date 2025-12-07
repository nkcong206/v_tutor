"""
Image Single Choice Question Generator.

Generates questions with AI-generated images + single choice answers.
"""
import json
import random
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import ImageSingleChoiceQuestion, GenImageSingleChoiceQuestion, letter_to_index
from app.services.image_generator import generate_image


class ImageSingleChoiceGenerator(BaseQuestionGenerator):
    """Generator for image + single choice questions."""
    
    question_type = "image_single_choice"

    def _shuffle_options(self, options: list, correct_answer: int) -> tuple:
        """Shuffle options and return new options list with updated correct_answer index."""
        indexed_options = list(enumerate(options))
        random.shuffle(indexed_options)
        new_correct_answer = None
        shuffled_options = []
        for new_idx, (old_idx, option) in enumerate(indexed_options):
            shuffled_options.append(option)
            if old_idx == correct_answer:
                new_correct_answer = new_idx
        return shuffled_options, new_correct_answer

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        generate_media: bool = True,
        **kwargs
    ) -> Optional[ImageSingleChoiceQuestion]:
        """Generate an image + single choice question."""
        
        user_prompt = f"Tạo 1 câu hỏi trắc nghiệm có hình ảnh về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        # Use structured generation
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenImageSingleChoiceQuestion,
            temperature=temperature
        )
        
        if not gen_question:
            return None
            
        try:
            # Generate image if requested
            image_base64 = None
            if generate_media and gen_question.image_prompt:
                image_base64 = await generate_image(gen_question.image_prompt)
                
                if not image_base64:
                     print(f"❌ Failed to generate image for prompt: {gen_question.image_prompt}")
                     return None
            
            # Shuffle options to randomize correct answer position
            shuffled_options, new_correct_answer = self._shuffle_options(
                gen_question.options,
                gen_question.correct_answer
            )
            
            return ImageSingleChoiceQuestion(
                id=question_id,
                type="image_single_choice",
                image_base64=image_base64,
                image_prompt=gen_question.image_prompt,
                text=gen_question.text,
                options=shuffled_options,
                correct_answer=new_correct_answer,
                explanation=gen_question.explanation
            )
        except Exception as e:
            print(f"❌ Error processing generated question: {e}")
            return None


# Singleton instance
image_single_choice_generator = ImageSingleChoiceGenerator()

