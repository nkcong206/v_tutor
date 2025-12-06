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
    
    system_prompt = f"""Bạn là chuyên gia thiết kế bài kiểm tra cho học sinh TIỂU HỌC.

Nhiệm vụ:
1. Phân tích nội dung (prompt) để xác định MÔN HỌC (Toán, Tiếng Việt, Tiếng Anh, Sử, Địa, Tin học).
2. Chọn danh sách {question_count} dạng câu hỏi phù hợp nhất theo quy tắc sau:

QUY TẮC CHỌN DẠNG CÂU HỎI (Ưu tiên Tiểu học):

1. Môn TIẾNG ANH (English):
   - Ưu tiên cao: audio_single_choice, audio_multi_choice (Luyện nghe).
   - Tốt: image_single_choice (Nhìn hình đoán từ).
   - Cơ bản: single_choice, multi_choice, fill_in_blanks.

2. Môn ĐỊA LÝ (Geography):
   - Ưu tiên: image_single_choice (Bản đồ, hình ảnh thiên nhiên).
   - Cơ bản: single_choice, fill_in_blanks.

3. Môn TOÁN (Math) / TIN HỌC (CS):
   - Cơ bản: single_choice, fill_in_blanks (Tính toán, điền số).
   - Có thể dùng: image_single_choice (Hình học, mô hình) nhưng không ưu tiên quá nhiều trừ khi cần trực quan.

4. Môn TIẾNG VIỆT (Literature) / LỊCH SỬ (History):
   - Ưu tiên: text only (single_choice, multi_choice, fill_in_blanks).
   - Hạn chế image trừ khi cần thiết.
   - KHÔNG dùng Audio.

LƯU Ý QUAN TRỌNG:
- Dạng AUDIO chỉ dành cho TIẾNG ANH. Các môn khác TUYỆT ĐỐI KHÔNG DÙNG AUDIO.
- Nếu không xác định được môn, dùng dạng text (single_choice) là an toàn nhất.

Danh sách các dạng ĐƯỢC PHÉP dùng:
{json.dumps(available_types, ensure_ascii=False)}

YÊU CẦU OUTPUT:
- Trả về JSON array chứa đúng {question_count} string là các dạng câu hỏi đã chọn.
- Ví dụ: ["single_choice", "image_single_choice", "..."]

CHỈ trả về JSON array."""

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
        
        return validated_types[:question_count]
        
    except Exception as e:
        print(f"❌ Error selecting question types: {e}")
        # Fallback: all single choice
        return ["single_choice"] * question_count
