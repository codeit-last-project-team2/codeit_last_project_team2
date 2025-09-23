from pydantic import BaseModel

class PosterTextRequest(BaseModel):
    product: str
    event: str
    date: str
    location: str
    vibe: str
    gpt_model: str = "gpt-4.1-mini"

class PosterTextResponse(BaseModel):
    title: str
    body: str
    dalle_prompt: str
