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

QUY TẮC CHỌN DẠNG CÂU HỎI (Ưu tiên ĐA DẠNG):

⚠️ YÊU CẦU QUAN TRỌNG: BẮT BUỘC phải đa dạng loại câu hỏi! 
- Nếu có >= 3 câu: PHẢI có ít nhất 2-3 loại KHÁC NHAU.
- TRÁNH chỉ dùng mỗi single_choice cho tất cả.
- Ưu tiên xen kẽ: single_choice, multi_choice, fill_in_blanks.

1. Môn TIẾNG ANH (English):
   - Ưu tiên cao: audio_single_choice, audio_multi_choice (Luyện nghe).
   - Tốt: image_single_choice, fill_in_blanks (Điền từ vựng).
   - Cơ bản: single_choice, multi_choice.
   - Khuyến nghị phân bổ: 30% audio, 30% fill_in_blanks, 40% choice.

2. Môn ĐỊA LÝ (Geography):
   - Ưu tiên: image_single_choice (Bản đồ, hình ảnh thiên nhiên).
   - Cơ bản: single_choice, multi_choice, fill_in_blanks.

3. Môn TOÁN (Math) / TIN HỌC (CS):
   - Ưu tiên: fill_in_blanks (Tính toán, điền số), single_choice.
   - Có thể dùng: image_single_choice (Hình học), multi_choice.
   - Khuyến nghị: 40% fill_in_blanks, 40% single_choice, 20% khác.

4. Môn TIẾNG VIỆT (Literature) / LỊCH SỬ (History):
   - Ưu tiên: multi_choice, fill_in_blanks, single_choice (Xen kẽ).
   - KHÔNG dùng Audio.

LƯU Ý QUAN TRỌNG:
- Dạng AUDIO chỉ dành cho TIẾNG ANH. Các môn khác TUYỆT ĐỐI KHÔNG DÙNG AUDIO.
- Nếu không xác định được môn, dùng đa dạng: single_choice, multi_choice, fill_in_blanks.

Danh sách các dạng ĐƯỢC PHÉP dùng:
{json.dumps(available_types, ensure_ascii=False)}

YÊU CẦU OUTPUT:
- Trả về JSON array chứa đúng {question_count} string là các dạng câu hỏi đã chọn.
- Ví dụ: ["single_choice", "fill_in_blanks", "multi_choice", "image_single_choice"]

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

