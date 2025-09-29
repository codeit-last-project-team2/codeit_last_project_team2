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

# ✅ 히스토리 저장용 모델
class MascotHistoryItem(BaseModel):
    user_email: str
    store_name: str
    keyword: Optional[str]
    mascot_personality: Optional[str]
    url: str
