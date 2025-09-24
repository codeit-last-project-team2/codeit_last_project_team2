from pydantic import BaseModel
from typing import Optional

class MascotRequest(BaseModel):
    main_color: str
    keyword: str
    personality: str
    brand_intro: str
    additional_requirements: Optional[str] = None
