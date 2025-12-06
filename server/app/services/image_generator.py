"""
Image Generation Service using OpenAI GPT Image API.
Model: gpt-image-1
"""
import base64
from typing import Optional
from openai import OpenAI
from app.config import settings


# OpenAI client
client = OpenAI(api_key=settings.openai_api_key)


async def generate_image(
    prompt: str,
    model: str = "dall-e-2",
    size: str = "1024x1024"
) -> Optional[str]:
    """
    Generate an image from a text prompt.
    
    Args:
        prompt: Description of the image to generate
        model: Model to use (dall-e-2, dall-e-3, or gpt-image-1-mini if verified)
        size: Image size (256x256, 512x512, 1024x1024 for dall-e-2)
    
    Returns:
        Base64 encoded image string, or None if failed
    """
    try:
        result = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            n=1,
            response_format="b64_json"
        )
        return result.data[0].b64_json
        
    except Exception as e:
        print(f"❌ Image generation error: {e}")
        return None


def save_image_to_file(base64_image: str, filepath: str) -> bool:
    """
    Save a base64 encoded image to a file.
    
    Args:
        base64_image: Base64 encoded image string
        filepath: Path to save the image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        image_bytes = base64.b64decode(base64_image)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return True
    except Exception as e:
        print(f"❌ Error saving image: {e}")
        return False
