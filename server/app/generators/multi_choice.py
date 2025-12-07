"""
Multi Choice Question Generator.

Generates text-only multiple choice questions (select all that apply).
"""
import json
import random
from typing import Optional
from app.generators.base import BaseQuestionGenerator
from app.generators.schemas import letter_to_index, GenMultiChoiceQuestion, MultiChoiceQuestion


class MultiChoiceGenerator(BaseQuestionGenerator):
    """Generator for multiple choice questions."""
    
    question_type = "multi_choice"

    def _shuffle_options(self, options: list, correct_answers: list) -> tuple:
        """Shuffle options and return new options list with updated correct_answers indices."""
        indexed_options = list(enumerate(options))
        random.shuffle(indexed_options)
        new_correct_answers = []
        shuffled_options = []
        for new_idx, (old_idx, option) in enumerate(indexed_options):
            shuffled_options.append(option)
            if old_idx in correct_answers:
                new_correct_answers.append(new_idx)
        return shuffled_options, sorted(new_correct_answers)

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.7,
        question_id: int = 1,
        **kwargs
    ) -> Optional[MultiChoiceQuestion]:
        """Generate a multiple choice question."""
        
        user_prompt = f"Tạo 1 câu hỏi trắc nghiệm nhiều lựa chọn về: {prompt}"
        if context:
            user_prompt += f"\n\nNội dung tham khảo:\n{context}"
        
        gen_question = await self._generate_structured(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            response_model=GenMultiChoiceQuestion,
            temperature=temperature
        )
        
        if gen_question:
            # Shuffle options to randomize correct answer positions
            shuffled_options, new_correct_answers = self._shuffle_options(
                gen_question.options,
                gen_question.correct_answers
            )
            
            return MultiChoiceQuestion(
                id=question_id,
                type="multi_choice",
                text=gen_question.text,
                options=shuffled_options,
                correct_answers=new_correct_answers,
                explanation=gen_question.explanation
            )
            
        return None


# Singleton instance
multi_choice_generator = MultiChoiceGenerator()

