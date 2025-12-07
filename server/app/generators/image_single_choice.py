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
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên tạo câu hỏi trắc nghiệm dựa trên hình ảnh.

Quy trình:
1. Tìm kiếm hình ảnh phù hợp từ Unsplash (query tiếng Anh) -> image_query
2. Tạo câu hỏi trắc nghiệm liên quan đến hình ảnh đó
3. 4 đáp án lựa chọn
4. 1 đáp án đúng (index 0-based)
5. Giải thích

QUAN TRỌNG:
- image_prompt: TIẾNG ANH.
    - Yêu cầu phong cách: "simple educational clip art", "children book illustration", "vector style", "white background".
    - Hình ảnh phải rõ ràng, đơn giản, tập trung vào chủ thể (giống flashcard).
    - TUYỆT ĐỐI KHÔNG chứa text/chữ trong hình ảnh (No text, no words).
    - Trong `image_prompt`, PHẢI bao gồm cụm từ: "no text, no words, no labels, isolated on white background".
- Nội dung câu hỏi KHÔNG ĐƯỢC yêu cầu học sinh đọc chữ từ trong hình ảnh.
- Nếu chủ đề là TIẾNG ANH: Nội dung câu hỏi (text) và đáp án (options) viết bằng TIẾNG ANH. Giải thích (explanation) viết bằng TIẾNG VIỆT.
- Nếu chủ đề khác: Viết toàn bộ (text, options, explanation) bằng TIẾNG VIỆT.

Sử dụng format strict JSON.
Trả về JSON theo format:
{
    "image_prompt": "Mô tả hình ảnh chi tiết để AI vẽ",
    "text": "Câu hỏi về hình ảnh",
    "options": ["Đáp án 1", "Đáp án 2", "Đáp án 3", "Đáp án 4"],
    "correct_answer": 0,
    "explanation": "Giải thích chi tiết"
}

Sử dụng format strict JSON."""

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

