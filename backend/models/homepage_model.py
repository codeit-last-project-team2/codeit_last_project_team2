from pydantic import BaseModel, Field
from typing import List, Optional
from backend.models.user_information_model import Menu

class HomepageRequest(BaseModel):
    email: str
    store_name: str
    category_main: str
    category_sub: str
    call_number: str
    address: str

class GithubUploadRequest(BaseModel):
    html: str
    email: str
    store_name: str