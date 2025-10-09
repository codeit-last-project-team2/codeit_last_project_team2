from pydantic import BaseModel, Field
from typing import Literal, Optional

class PosterImageRequest(BaseModel):
    title: str
    body: str
    dalle_prompt: str
    dalle_size: str = "1024x1024"
    position: Literal["top", "center", "bottom"] = "bottom"

    # 추가 스타일 옵션
    title_color: str = Field("#FFFFFF", description="제목 색상")
    body_color: str = Field("#FFFF00", description="본문 색상")
    title_font_size: int = Field(80, description="제목 폰트 크기")
    body_font_size: int = Field(50, description="본문 폰트 크기")
    stroke_width_title: int = Field(3, description="제목 테두리 두께")
    stroke_width_body: int = Field(2, description="본문 테두리 두께")
    stroke_color_title: str = Field("#000000", description="제목 테두리 색상")
    stroke_color_body: str = Field("#000000", description="본문 테두리 색상")
    font_name: Optional[str] = Field(None, description="선택한 폰트 이름 (data/fonts 내 파일명)")
