from pydantic import BaseModel

class PosterImageRequest(BaseModel):
    title: str
    body: str
    dalle_prompt: str
    dalle_size: str = "1024x1024"
    position: str = "bottom"  # top, center, bottom
