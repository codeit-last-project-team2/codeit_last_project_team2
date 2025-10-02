from pydantic import BaseModel

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