"""
Base Generator Class.

Provides common functionality for all question generators.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type
from openai import OpenAI
from app.config import settings
from app.generators.schemas import AnyQuestion
from app.services.prompt_management import get_system_prompt as get_prompt_from_yaml


class BaseQuestionGenerator(ABC):
    """Abstract base class for question generators."""
    
    # Question type identifier - must be overridden
    question_type: str = "base"
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[AnyQuestion]:
        """
        Generate a single question.
        
        Args:
            prompt: The topic/prompt for the question
            context: Additional context (e.g., from uploaded files)
            temperature: LLM temperature
            **kwargs: Additional parameters
            
        Returns:
            Generated question or None if failed
        """
        pass
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this question type from YAML file."""
        return get_prompt_from_yaml(self.question_type)
    
    async def _generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[AnyQuestion],
        temperature: float = 0.7
    ) -> Optional[AnyQuestion]:
        """
        Generate a structured question using the new service.
        """
        from app.services.llm_service import llm_service
        
        return llm_service.generate_response(
            response_model=response_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )

    # Legacy method kept for compatibility but warning added
    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        DEPRECATED: Use _generate_structured instead.
        """
        print("⚠️ Warning: Legacy _call_llm used. Please migrate to _generate_structured.")
        try:
            kwargs = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature
            }
            if response_format:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ LLM call error: {e}")
            return None
