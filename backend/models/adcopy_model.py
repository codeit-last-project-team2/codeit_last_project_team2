# backend/models/adcopy_model.py
from pydantic import BaseModel
from typing import List, Optional

class AdcopyTextRequest(BaseModel):
    product: str
    tone: str
    length: str = "short"      # "short" | "long"
    num_copies: int = 3
    model: str = "gpt-4.1-mini"

class AdcopyTextResponse(BaseModel):
    copies: List[str]
    raw_output: Optional[str] = None  # 디버그용(원하면 숨겨도 됨)

class AdcopyImageResponse(BaseModel):
    copies: List[str]
    raw_output: Optional[str] = None