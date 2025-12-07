"""
Structured LLM Service.

Encapsulates OpenAI's beta structured output capabilities.
"""
from typing import Type, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
from openai import OpenAI
from app.config import settings

T = TypeVar("T", bound=BaseModel)

class PerformanceAnalysis(BaseModel):
    summary: str
    score: int = Field(..., ge=0, le=10, description="Score on 0-10 scale based on engagement and understanding")

class StructuredLLMService:
    """Service for generating structured outputs from LLMs."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-2024-08-06"

    def generate_response(
        self,
        response_model: Type[T],
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> Optional[T]:
        """
        Generate a structured response ensuring it matches the Pydantic model.
        """
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return completion.choices[0].message.parsed
            
        except Exception as e:
            print(f"❌ Structured LLM Generation Error: {e}")
            return None

    def analyze_performance(self, student_name: str, score: int, total_questions: int, chat_history: List[dict]) -> Optional[dict]:
        """
        Analyze student performance based on results and chat history.
        """
        try:
            # Filter chat history to role/content to save tokens
            clean_history = [
                {"role": m.get("role"), "content": m.get("content")} 
                for m in chat_history if m.get("content")
            ]
            
            # Get prompt from YAML
            from app.services.prompt_management import get_system_prompt
            system_prompt = get_system_prompt("performance_analysis")
            
            user_prompt = f"""
            Học sinh: {student_name}
            Kết quả bài thi: {score}/{total_questions} câu đúng.
            
            Lịch sử Chat với AI Tutor:
            {clean_history if clean_history else "Không có hội thoại nào."}
            
            Hãy phân tích và đánh giá.
            """
            
            result = self.generate_response(
                response_model=PerformanceAnalysis,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7
            )
            
            if result:
                return result.model_dump()
            return None
            
        except Exception as e:
            print(f"❌ Analysis Error: {e}")
            return None


# Singleton instance
llm_service = StructuredLLMService()
