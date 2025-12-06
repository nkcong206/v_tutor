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
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo câu hỏi trắc nghiệm CÓ HÌNH ẢNH.

Tạo câu hỏi trắc nghiệm gồm:
- 1 Mô tả hình ảnh (image_prompt) bằng Tiếng Anh để tìm/tạo hình
- 1 câu hỏi liên quan đến hình ảnh
- 4 đáp án (có thể chọn nhiều đáp án đúng)
- correct_answers: danh sách index (0-based) các đáp án đúng
- Giải thích chi tiết

QUAN TRỌNG:
- image_prompt: TIẾNG ANH.
    - Yêu cầu phong cách: "simple educational clip art", "children book illustration", "vector style", "white background".
    - Hình ảnh phải rõ ràng, đơn giản, tập trung vào chủ thể (giống flashcard).
    - TUYỆT ĐỐI KHÔNG chứa text/chữ trong hình ảnh (No text, no words).
    - Trong `image_prompt`, PHẢI bao gồm cụm từ: "no text, no words, no labels, isolated on white background".
- Nội dung câu hỏi KHÔNG ĐƯỢC yêu cầu học sinh đọc chữ từ trong hình ảnh.
- Nếu chủ đề là TIẾNG ANH: Nội dung câu hỏi (text) và đáp án (options) viết bằng TIẾNG ANH. Giải thích (explanation) viết bằng TIẾNG VIỆT.
- Nếu chủ đề khác: Viết toàn bộ (text, options, explanation) bằng TIẾNG VIỆT.

Sử dụng format strict JSON cho GenImageMultiChoiceQuestion."""

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
