import urllib.parse
from typing import Optional

async def search_and_get_image(query: str) -> Optional[str]:
    """
    Get an image URL based on a text query.
    Uses Pollinations.ai for instant, free image generation via URL.
    This effectively acts as a deep search/generation for the requested concept.
    """
    if not query:
        return None
        
    # Encode query for URL
    encoded_query = urllib.parse.quote(query)
    
    # Construct URL
    # We can add parameters like width/height/seed if needed, but simple prompt is fine.
    # Using a deterministic seed based on query could be good for caching, 
    # but random is fine for "generation".
    # Let's just return the URL. The frontend will fetch it.
    
    return f"https://image.pollinations.ai/prompt/{encoded_query}"
