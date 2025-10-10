from pydantic import BaseModel, Field
from typing import List, Optional

class MenuItem(BaseModel):
    name: str
    price: str
    feature: Optional[str] = None

class HomepageRequest(BaseModel):
    # 공통 입력
    email: str = Field(..., description="사용자 이메일")
    store_name: str = Field(..., description="매장명")
    category: Optional[str] = Field(None, description="업종")
    phone: Optional[str] = Field(None, description="연락처")
    address: Optional[str] = Field(None, description="매장 주소")

    # 홈페이지 구성
    menus: List[MenuItem] = Field(..., description="메뉴 리스트")
    style: Optional[str] = Field(None, description="홈페이지 톤앤매너 (예: 심플, 모던 등)")
    purpose: Optional[str] = Field(None, description="홈페이지 제작 목적 (예: 신규 고객 유치 등)")
    mood: Optional[str] = Field(None, description="홈페이지 전반 분위기")
    tone: Optional[str] = Field(None, description="카피라이팅 톤")
    sample_id: Optional[str] = Field(default="1", description="참고 템플릿 ID (기본 1)")

class GithubUploadRequest(BaseModel):
    html: str
    email: str
    store_name: str
