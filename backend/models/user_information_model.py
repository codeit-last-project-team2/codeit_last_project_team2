from pydantic import BaseModel

class UserInformation(BaseModel):
    store_name: str
    category_main: str
    category_sub: str
    call_number: str
    address: str

class StoreInfoRequest(BaseModel):
    store_name: str