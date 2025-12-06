"""
Text-to-Speech Generation Service using OpenAI TTS API.
Model: gpt-4o-mini-tts
"""
import asyncio
import os
from pathlib import Path
from typing import Optional
import io
from openai import OpenAI
from pydub import AudioSegment
from app.config import settings


# OpenAI client
client = OpenAI(api_key=settings.openai_api_key)

# Audio storage directory
AUDIO_DIR = Path(settings.upload_dir) / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


async def generate_audio(
    text: str,
    voice: str = "coral",
    model: str = "gpt-4o-mini-tts",
    instructions: Optional[str] = None
) -> Optional[bytes]:
    """
    Generate audio from text using OpenAI TTS.
    
    Args:
        text: Text to convert to speech
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer, coral)
        model: Model to use (gpt-4o-mini-tts or tts-1)
        instructions: Optional speaking instructions
        
    Returns:
        Audio bytes (MP3), or None if failed
    """
    try:
        kwargs = {
            "model": model,
            "voice": voice,
            "input": text,
            "speed": 0.8
        }
        
        if instructions:
            kwargs["instructions"] = instructions
        
        def _sync_gen():
            with client.audio.speech.with_streaming_response.create(**kwargs) as response:
                audio_bytes = b""
                for chunk in response.iter_bytes():
                    audio_bytes += chunk
                return audio_bytes

        # Run blocking I/O in thread pool to avoid blocking event loop
        return await asyncio.to_thread(_sync_gen)
            
    except Exception as e:
        print(f"❌ TTS generation error: {e}")
        return None


async def generate_and_save_audio(
    text: str,
    filename: str,
    voice: str = "coral",
    instructions: Optional[str] = None
) -> Optional[str]:
    """
    Generate audio and save to file.
    
    Args:
        text: Text to convert to speech
        filename: Filename (without extension)
        voice: Voice to use
        instructions: Optional speaking instructions
        
    Returns:
        Relative path to saved audio file, or None if failed
    """
    audio_bytes = await generate_audio(text, voice, instructions=instructions)
    
    if audio_bytes is None:
        return None
    
    try:
        filepath = AUDIO_DIR / f"{filename}.mp3"
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        
        # Return relative path for serving
        return f"audio/{filename}.mp3"
        
    except Exception as e:
        print(f"❌ Error saving audio: {e}")
        return None


async def generate_audio_from_script(
    script: list,
    filename: str
) -> Optional[str]:
    """
    Generate multi-voice audio from a script and save to file.
    
    Args:
        script: List of dicts or objects with 'voice' and 'text' attributes.
        filename: Filename (without extension)
        
    Returns:
        Relative path to saved audio file, or None if failed
    """
    combined_audio = AudioSegment.empty()
    
    try:
        # Check if script is empty
        if not script:
            return None

        tasks = []
        valid_segments = []

        # Prepare tasks
        for i, segment in enumerate(script):
            # Handle both dict and object access
            voice = segment.voice if hasattr(segment, 'voice') else segment.get('voice')
            text = segment.text if hasattr(segment, 'text') else segment.get('text')
            
            if not text:
                continue
                
            # Default to alloy if voice is invalid or missing
            if not voice:
                voice = "alloy"
            
            # Store metadata for logging/debugging if needed
            valid_segments.append({'index': i, 'text': text, 'voice': voice})
            
            # Add async task
            tasks.append(generate_audio(text, voice=voice, model="tts-1"))

        if not tasks:
            return None
            
        print(f"🚀 Batch generating {len(tasks)} audio segments...")
        
        # Execute in parallel
        results = await asyncio.gather(*tasks)

        # Stitch results
        for i, audio_bytes in enumerate(results):
            segment_info = valid_segments[i]
            
            if audio_bytes:
                # Convert bytes to pydub AudioSegment
                segment_audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                combined_audio += segment_audio
                
                # Add a small pause between segments (300ms)
                combined_audio += AudioSegment.silent(duration=300)
            else:
                print(f"⚠️ Failed to generate audio for segment {segment_info['index']+1}")

        # Save combined audio
        filepath = AUDIO_DIR / f"{filename}.mp3"
        
        # Export as MP3
        combined_audio.export(filepath, format="mp3")
        
        print(f"✅ Saved dialogue audio: {filepath}")
        return f"audio/{filename}.mp3"
        
    except Exception as e:
        print(f"❌ Error generating dialogue audio: {e}")
        return None
