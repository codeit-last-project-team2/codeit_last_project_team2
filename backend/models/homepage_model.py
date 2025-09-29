from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class MenuItem(BaseModel):
    name: str = Field(min_length=1)
    price: int = Field(ge=0)  # 0원 이상

class HomepageRequest(BaseModel):
    store_name: str
    category_main: str
    category_sub: str
    menus: List[MenuItem]
    targets: List[str]
    selling_points: List[str]
    ad_purpose: str
    mood: str
    location: str
    event: str
    tone: str

class GithubUploadRequest(BaseModel):
    html: str
    store_id: str