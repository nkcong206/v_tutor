"""
Question Type Schemas.

Defines Pydantic models for each question type with type discriminator.

IMPORTANT: correct_answer uses 0-based index (int), not letters (A, B, C, D).
- single_choice: correct_answer = 0 (first option)
- multi_choice: correct_answers = [0, 2] (first and third options)
- fill_in_blanks: correct_answers = ["word1", "word2"] (exact text)
"""
from typing import List, Optional, Literal, Union
from pydantic import BaseModel


# --- Generation Schemas (No 'type' field, for LLM Only) ---

# --- New Models for Multi-Voice Audio ---

VoiceType = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

class DialogueSegment(BaseModel):
    voice: VoiceType
    text: str

# --- Generation Schemas (No 'type' field, for LLM Only) ---

class GenBaseQuestion(BaseModel):
    explanation: str

class GenSingleChoiceQuestion(GenBaseQuestion):
    text: str
    options: List[str]
    correct_answer: int

class GenMultiChoiceQuestion(GenBaseQuestion):
    text: str
    options: List[str]
    correct_answers: List[int]

class GenFillInBlanksQuestion(GenBaseQuestion):
    text: str
    blanks_count: int
    correct_answers: List[str]

class GenImageSingleChoiceQuestion(GenBaseQuestion):
    image_prompt: str
    text: str
    options: List[str]
    correct_answer: int

class GenImageMultiChoiceQuestion(GenBaseQuestion):
    image_prompt: str
    text: str
    options: List[str]
    correct_answers: List[int]

class GenAudioSingleChoiceQuestion(GenBaseQuestion):
    audio_script: List[DialogueSegment]
    text: str
    options: List[str]
    correct_answer: int

class GenAudioMultiChoiceQuestion(GenBaseQuestion):
    audio_script: List[DialogueSegment]
    text: str
    options: List[str]
    correct_answers: List[int]

class GenImageFillInBlanksQuestion(GenBaseQuestion):
    image_prompt: str
    text: str
    blanks_count: int
    correct_answers: List[str]

class GenAudioFillInBlanksQuestion(GenBaseQuestion):
    audio_script: List[DialogueSegment]
    text: str
    blanks_count: int
    correct_answers: List[str]

# --- Full Application Schemas (With 'type' field for DB/API) ---

class SingleChoiceQuestion(GenSingleChoiceQuestion):
    id: int
    type: Literal["single_choice"] = "single_choice"

class MultiChoiceQuestion(GenMultiChoiceQuestion):
    id: int
    type: Literal["multi_choice"] = "multi_choice"

class FillInBlanksQuestion(GenFillInBlanksQuestion):
    id: int
    type: Literal["fill_in_blanks"] = "fill_in_blanks"

class ImageSingleChoiceQuestion(GenImageSingleChoiceQuestion):
    id: int
    type: Literal["image_single_choice"] = "image_single_choice"
    image_base64: Optional[str] = None
    image_url: Optional[str] = None

class ImageMultiChoiceQuestion(GenImageMultiChoiceQuestion):
    id: int
    type: Literal["image_multi_choice"] = "image_multi_choice"
    image_base64: Optional[str] = None
    image_url: Optional[str] = None

class AudioSingleChoiceQuestion(GenAudioSingleChoiceQuestion):
    id: int
    type: Literal["audio_single_choice"] = "audio_single_choice"
    audio_url: Optional[str] = None

class AudioMultiChoiceQuestion(GenAudioMultiChoiceQuestion):
    id: int
    type: Literal["audio_multi_choice"] = "audio_multi_choice"
    audio_url: Optional[str] = None

class ImageFillInBlanksQuestion(GenImageFillInBlanksQuestion):
    id: int
    type: Literal["image_fill_in_blanks"] = "image_fill_in_blanks"
    image_base64: Optional[str] = None
    image_url: Optional[str] = None

class AudioFillInBlanksQuestion(GenAudioFillInBlanksQuestion):
    id: int
    type: Literal["audio_fill_in_blanks"] = "audio_fill_in_blanks"
    audio_url: Optional[str] = None


# Union type for any question
AnyQuestion = Union[
    SingleChoiceQuestion,
    MultiChoiceQuestion,
    FillInBlanksQuestion,
    ImageSingleChoiceQuestion,
    ImageMultiChoiceQuestion,
    AudioSingleChoiceQuestion,
    AudioMultiChoiceQuestion,
    ImageFillInBlanksQuestion,
    AudioFillInBlanksQuestion
]


def get_question_type(question: AnyQuestion) -> str:
    """Get the type string of a question."""
    return question.type


def letter_to_index(letter: str) -> int:
    """Convert letter (A, B, C, D) to 0-based index."""
    return ord(letter.upper()) - ord('A')


def index_to_letter(index: int) -> str:
    """Convert 0-based index to letter (A, B, C, D)."""
    return chr(ord('A') + index)

