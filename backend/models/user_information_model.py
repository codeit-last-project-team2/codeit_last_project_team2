from pydantic import BaseModel

from typing import List, Optional, Union

class Menu(BaseModel):
    img_path: Optional[str]  
    name: str
    price: Union[int, float]
    desc: Union[str]

class UserInformation(BaseModel):
    store_name: str
    category_main: str
    category_sub: str
    call_number: str
    address: str
    menus: List[Menu]
    targets: Optional[List[str]]
    selling_points: Optional[List[str]]
    ad_purpose: Optional[str]
    mood: Optional[str]
    event: Optional[str]
    tone: Optional[str]

class StoreInfoRequest(BaseModel):
    store_name: str