"""
Question Type Selector Service.

Uses LLM to select appropriate question types for an exam based on subject and topic.
"""
import json
from typing import List
from openai import OpenAI
from app.config import settings
from app.generators import QuestionType, get_available_types


# OpenAI client
client = OpenAI(api_key=settings.openai_api_key)


async def select_question_types(
    subject: str,
    prompt: str,
    question_count: int,
    temperature: float = 0.7
) -> List[QuestionType]:
    """
    Select question types for an exam using LLM.
    
    Args:
        subject: Subject (english, math, cs, etc.)
        prompt: Topic/prompt for the exam
        question_count: Number of questions to generate
        temperature: LLM temperature
        
    Returns:
        List of question types to generate
    """
    available_types = get_available_types(subject)
    
    # Get prompt from YAML and interpolate variables
    from app.services.prompt_management import get_system_prompt
    system_prompt = get_system_prompt(
        "question_type_selector",
        question_count=question_count,
        available_types=json.dumps(available_types, ensure_ascii=False)
    )

    user_prompt = f"Chủ đề: {prompt}\nSố câu: {question_count}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        # Parse response - handle both array and object with "types" key
        data = json.loads(content)
        
        if isinstance(data, list):
            types = data
        elif isinstance(data, dict) and "types" in data:
            types = data["types"]
        else:
            # Fallback: extract array from response
            types = list(data.values())[0] if data else []
        
        # Validate types are in available list
        validated_types = []
        for t in types:
            if t in available_types:
                validated_types.append(t)
            else:
                # Fallback to single_choice
                validated_types.append("single_choice")
        
        # Ensure correct count
        while len(validated_types) < question_count:
            validated_types.append("single_choice")
        
        validated_types = validated_types[:question_count]
        
        # ENFORCE DIVERSITY: If all same type and count >= 3, mix it up
        if question_count >= 3 and len(set(validated_types)) == 1:
            print(f"⚠️ All same type detected, enforcing diversity...")
            diverse_types = ["single_choice", "multi_choice", "fill_in_blanks"]
            validated_types = [diverse_types[i % len(diverse_types)] for i in range(question_count)]
        
        return validated_types
        
    except Exception as e:
        print(f"❌ Error selecting question types: {e}")
        # Fallback: diverse mix instead of all single choice
        diverse_fallback = ["single_choice", "multi_choice", "fill_in_blanks"]
        return [diverse_fallback[i % len(diverse_fallback)] for i in range(question_count)]

