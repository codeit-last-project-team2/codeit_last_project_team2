from pydantic import BaseModel, Field
from typing import List, Optional

class PosterTextRequest(BaseModel):
    # 공통 입력
    email: str = Field(..., description="사용자 이메일")
    store_name: str = Field(..., description="매장명")
    category: Optional[str] = Field(None, description="업종")
    phone: Optional[str] = Field(None, description="연락처")
    address: Optional[str] = Field(None, description="매장 주소")

    # 광고 관련 입력
    ad_type: str = Field(..., description="광고 유형: 브랜드 / 제품 / 이벤트 중 하나")
    brand_desc: Optional[str] = None
    product_name: Optional[str] = None
    product_feature: Optional[str] = None
    event_period: Optional[List[str]] = None
    event_desc: Optional[str] = None
    vibe: Optional[str] = None

class PosterTextResponse(BaseModel):
    title: str
    body: str
    dalle_prompt: str
