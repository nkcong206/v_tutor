"""
Question Generators Package.

This module contains generators for different question types:
- single_choice: Text-only single choice questions
- multi_choice: Text-only multiple choice questions
- fill_in_blanks: Fill in the blanks questions
- image_single_choice: Image + single choice
- image_multi_choice: Image + multiple choice
- audio_single_choice: Audio + single choice
- audio_multi_choice: Audio + multiple choice
"""
from typing import List, Literal

# Supported question types
QuestionType = Literal[
    "single_choice",
    "multi_choice", 
    "fill_in_blanks",
    "image_single_choice",
    "image_multi_choice",
    "audio_single_choice",
    "audio_multi_choice"
]

# Subject to available question types mapping
SUBJECT_QUESTION_TYPES: dict[str, List[QuestionType]] = {
    "english": [
        "single_choice",
        "multi_choice",
        "fill_in_blanks",
        "image_single_choice",
        "audio_single_choice",
        "audio_multi_choice"
    ],
    "math": [
        "single_choice",
        "multi_choice",
        "fill_in_blanks",
        "image_single_choice"
    ],
    "cs": [
        "single_choice",
        "multi_choice",
        "fill_in_blanks",
        "image_single_choice"
    ],
    "default": [
        "single_choice",
        "multi_choice",
        "fill_in_blanks",
        "image_single_choice",
        "image_multi_choice",
        "audio_single_choice",
        "audio_multi_choice",
        "image_fill_in_blanks",
        "audio_fill_in_blanks"
    ]
}


def get_available_types(subject: str) -> List[QuestionType]:
    """Get available question types for a subject."""
    subject_lower = subject.lower()
    return SUBJECT_QUESTION_TYPES.get(subject_lower, SUBJECT_QUESTION_TYPES["default"])
