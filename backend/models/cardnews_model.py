from pydantic import BaseModel
from typing import Tuple


class CardNewsTextRequest(BaseModel):
    num_pages: int
    topic: str
    purpose: str
    must: str
    audience: str
    tone: str
    lang: str

class CardNewsImgRequest(BaseModel):
    prompt: str
    size: Tuple[int, int]