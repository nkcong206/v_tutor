"""
Generator Factory.

Provides centralized access to all question generators.
"""
from typing import Optional
from app.generators import QuestionType
from app.generators.base import BaseQuestionGenerator
from app.generators.single_choice import single_choice_generator
from app.generators.multi_choice import multi_choice_generator
from app.generators.fill_in_blanks import fill_in_blanks_generator
from app.generators.image_single_choice import image_single_choice_generator
from app.generators.audio_single_choice import audio_single_choice_generator
from app.generators.image_multi_choice import image_multi_choice_generator
from app.generators.audio_multi_choice import audio_multi_choice_generator
from app.generators.image_fill_in_blanks import image_fill_in_blanks_generator
from app.generators.audio_fill_in_blanks import audio_fill_in_blanks_generator


# Map question type to generator instance
GENERATORS: dict[QuestionType, BaseQuestionGenerator] = {
    "single_choice": single_choice_generator,
    "multi_choice": multi_choice_generator,
    "fill_in_blanks": fill_in_blanks_generator,
    "image_single_choice": image_single_choice_generator,
    "audio_single_choice": audio_single_choice_generator,
    "image_multi_choice": image_multi_choice_generator,
    "audio_multi_choice": audio_multi_choice_generator,
    "image_fill_in_blanks": image_fill_in_blanks_generator,
    "audio_fill_in_blanks": audio_fill_in_blanks_generator,
}


def get_generator(question_type: QuestionType) -> Optional[BaseQuestionGenerator]:
    """Get the generator for a question type."""
    return GENERATORS.get(question_type)


def is_media_type(question_type: QuestionType) -> bool:
    """Check if a question type requires media generation."""
    return question_type in [
        "image_single_choice",
        "image_multi_choice",
        "image_fill_in_blanks",
        "audio_single_choice",
        "audio_multi_choice",
        "audio_fill_in_blanks"
    ]
