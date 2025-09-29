from pydantic import BaseModel
from typing import Optional

class MascotRequest(BaseModel):
    main_color: str
    keyword: str
    mascot_personality: str
    store_name: str
    mood: Optional[str] = None
    output_style: str
    additional_requirements: Optional[str] = None
