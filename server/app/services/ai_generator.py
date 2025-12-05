"""
AI Content Generator Service using OpenAI
Generates questions from educational materials with RAG
"""

from langchain_openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from pypdf import PdfReader
from typing import List, Dict
import json
from app.config import settings
from app.models.content import QuestionType


class AIGeneratorService:
    """Service for generating educational content using AI"""
    
    def __init__(self):
        self.model = OpenAI(
            model_name="gpt-4o-mini",
            openai_api_key=settings.openai_api_key
        )
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key
        )
    
    def process_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    def create_vector_store(self, text: str, collection_name: str) -> Chroma:
        """Create vector store from text for RAG"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(text)
        
        vectorstore = Chroma.from_texts(
            texts=chunks,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=settings.vector_store_dir
        )
        return vectorstore
    
    def generate_questions(
        self,
        context: str,
        question_count: int,
        question_types: List[QuestionType],
        creativity_level: int,
        practical_level: int,
        subject: str,
        grade: str
    ) -> List[Dict]:
        """Generate questions from context using Gemini"""
        
        # Build prompt based on parameters
        creativity_desc = {
            1: "câu hỏi cơ bản, trực tiếp từ tài liệu",
            2: "câu hỏi khá đơn giản, ít biến tấu",
            3: "câu hỏi có tính sáng tạo vừa phải",
            4: "câu hỏi sáng tạo, yêu cầu tư duy",
            5: "câu hỏi rất sáng tạo, khó tìm trên mạng"
        }
        
        practical_desc = {
            1: "lý thuyết thuần túy",
            2: "có ít ứng dụng thực tế",
            3: "kết hợp lý thuyết và thực tiễn",
            4: "tập trung vào ứng dụng thực tế",
            5: "hoàn toàn dựa trên tình huống thực tế"
        }
        
        types_str = ", ".join([t.value for t in question_types])
        
        prompt = f"""
Bạn là một giáo viên giàu kinh nghiệm. Hãy tạo {question_count} câu hỏi từ tài liệu sau.

THÔNG TIN:
- Môn học: {subject}
- Lớp: {grade}
- Loại câu hỏi: {types_str}
- Độ sáng tạo: {creativity_level}/5 ({creativity_desc[creativity_level]})
- Tính thực tiễn: {practical_level}/5 ({practical_desc[practical_level]})

TÀI LIỆU:
{context[:3000]}

YÊU CẦU:
1. Câu hỏi phải SÁNG TẠO, tránh copy nguyên văn từ tài liệu
2. Nếu độ sáng tạo cao (≥3), hãy đặt câu hỏi theo tình huống mới
3. Nếu tính thực tiễn cao (≥3), đưa câu hỏi vào bối cảnh đời sống
4. MỖI câu hỏi PHẢI có:
   - Đề bài rõ ràng
   - 4 đáp án (A, B, C, D) nếu là trắc nghiệm
   - Đáp án đúng
   - Lời giải CHI TIẾT (các bước giải rõ ràng)
   - Giải thích khái niệm liên quan

ĐỊNH DẠNG JSON (QUAN TRỌNG - trả về ĐÚNG format này):
{{
  "questions": [
    {{
      "question_text": "Câu hỏi...",
      "type": "single_choice",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "A",
      "solution": "Bước 1: ... Bước 2: ... Kết luận: ...",
      "explanation": "Giải thích khái niệm..."
    }}
  ]
}}

Hãy tạo các câu hỏi NGAY BÂY GIỜ:
"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Clean up JSON response
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            # Parse JSON
            data = json.loads(result_text)
            questions = data.get("questions", [])
            
            # Add metadata
            for q in questions:
                q["subject"] = subject
                q["grade"] = grade
                q["creativity_level"] = creativity_level
                q["practical_level"] = practical_level
            
            return questions
            
        except Exception as e:
            print(f"Error generating questions: {e}")
            # Return fallback question
            return [{
                "question_text": "Không thể tạo câu hỏi. Vui lòng thử lại.",
                "type": "single_choice",
                "options": ["A. Thử lại", "B. Thử lại", "C. Thử lại", "D. Thử lại"],
                "correct_answer": "A",
                "solution": "Có lỗi xảy ra khi tạo câu hỏi.",
                "explanation": str(e),
                "subject": subject,
                "grade": grade,
                "creativity_level": creativity_level,
                "practical_level": practical_level
            }]
