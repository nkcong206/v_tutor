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
    
    def get_system_prompt(self) -> str:
        return """Bạn là giáo viên chuyên tạo câu hỏi điền vào chỗ trống CÓ HÌNH ẢNH.

Tạo câu hỏi gồm:
- 1 Mô tả hình ảnh (image_prompt) bằng Tiếng Anh để tìm/tạo hình
- 1 câu/đoạn văn (text) có các chỗ trống đánh dấu bằng ___ (liên quan đến hình)
- Số lượng chỗ trống (blanks_count)
- Danh sách đáp án đúng (correct_answers)
- Giải thích chi tiết (explanation) - Bằng Tiếng Việt

QUAN TRỌNG:
- image_prompt: TIẾNG ANH.
    - Yêu cầu phong cách: "simple educational clip art", "children book illustration", "vector style", "white background".
    - Hình ảnh phải rõ ràng, đơn giản, tập trung vào chủ thể (giống flashcard).
    - TUYỆT ĐỐI KHÔNG chứa text/chữ trong hình ảnh (No text, no words).
    - Trong `image_prompt`, PHẢI bao gồm cụm từ: "no text, no words, no labels, isolated on white background".
- Nội dung câu hỏi KHÔNG ĐƯỢC yêu cầu học sinh đọc chữ từ trong hình ảnh.
- Nếu chủ đề là TIẾNG ANH: Nội dung đoạn văn/câu hỏi (text) và từ cần điền (correct_answers) viết bằng TIẾNG ANH. Giải thích (explanation) viết bằng TIẾNG VIỆT.
- Nếu chủ đề khác: Viết toàn bộ (text, correct_answers, explanation) bằng TIẾNG VIỆT.
- CHÚ Ý TUYỆT ĐỐI: Chỗ cần điền PHẢI là đúng 3 dấu gạch dưới '___'. KHÔNG dùng '____', '__' hay '[...]'. UI chỉ nhận diện đúng 3 dấu gạch dưới '___'.

Sử dụng format strict JSON cho GenImageFillInBlanksQuestion."""

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
