from pydantic import BaseModel, Field

class UserInformationRequest(BaseModel):
    email: str = Field(..., description="사용자 이메일")
    store_name: str = Field(..., description="매장명")
    category: str = Field(..., description="업종")
    phone: str = Field(..., description="연락처")
    address: str = Field(..., description="주소")

class UserInformationResponse(BaseModel):
    email: str
    store_name: str
    category: str
    phone: str
    address: str
