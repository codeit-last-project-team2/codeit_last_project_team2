from pydantic import BaseModel, Field
from typing import Optional

class MascotRequest(BaseModel):
    # 공통 입력
    user_email: str = Field(..., description="사용자 이메일")
    store_name: str = Field(..., description="매장명")
    category: Optional[str] = Field(None, description="업종")

    # 마스코트 전용 입력
    main_color: str = Field(..., description="대표 색상")
    keyword: str = Field(..., description="키워드")
    mascot_personality: str = Field(..., description="캐릭터 성격")
    mood: Optional[str] = Field(None, description="브랜드 분위기")
    output_style: str = Field(..., description="출력 스타일 (예: 3D, 일러스트, 심플 로고 등)")
    additional_requirements: Optional[str] = Field(None, description="추가 요구사항")

class MascotHistoryItem(BaseModel):
    user_email: str
    store_name: str
    keyword: Optional[str]
    mascot_personality: Optional[str]
    path: str
