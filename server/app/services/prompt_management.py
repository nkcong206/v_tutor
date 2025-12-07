"""
Prompt Management Service.

Centralizes all prompts in YAML files for easy management and updates.
"""
import os
import yaml
from typing import Optional, Dict, Any
from functools import lru_cache

# Path to prompts directory
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


@lru_cache(maxsize=50)
def _load_prompt_file(name: str) -> Optional[Dict[str, Any]]:
    """Load a prompt from YAML file with caching."""
    file_path = os.path.join(PROMPTS_DIR, f"{name}.yaml")
    
    if not os.path.exists(file_path):
        print(f"⚠️ Prompt file not found: {file_path}")
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error loading prompt {name}: {e}")
        return None


def get_prompt(name: str, **kwargs) -> Dict[str, str]:
    """
    Get a prompt by name.
    
    Args:
        name: Name of the prompt (without .yaml extension)
        **kwargs: Variables to interpolate into the prompt
        
    Returns:
        Dict with 'system_prompt' and optional 'human_prompt' keys
    """
    prompt_data = _load_prompt_file(name)
    
    if not prompt_data:
        return {"system_prompt": "", "human_prompt": ""}
    
    result = {}
    
    # Get system prompt
    system_prompt = prompt_data.get("system_prompt", "")
    if kwargs and system_prompt:
        try:
            system_prompt = system_prompt.format(**kwargs)
        except KeyError:
            pass  # Keep original if variable not provided
    result["system_prompt"] = system_prompt
    
    # Get human prompt (optional)
    human_prompt = prompt_data.get("human_prompt", "")
    if kwargs and human_prompt:
        try:
            human_prompt = human_prompt.format(**kwargs)
        except KeyError:
            pass
    result["human_prompt"] = human_prompt
    
    return result


def get_system_prompt(name: str, **kwargs) -> str:
    """Convenience function to get only the system prompt."""
    return get_prompt(name, **kwargs).get("system_prompt", "")


def clear_cache():
    """Clear the prompt cache (useful after updating YAML files)."""
    _load_prompt_file.cache_clear()
