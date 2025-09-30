# FastAPI 라우터. /adcopy/text (JSON) 와 /adcopy/image (multipart/form-data) 엔드포인트 제공.
# 인증(간단 API key) 의존성 사용.

# backend/routers/adcopy.py
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from backend.models import create_text_model as adcopy_text_model
from backend.models import image_text_model as adcopy_image_model
from backend.services.auth import get_api_key_header

router = APIRouter(prefix="/adcopy", tags=["Adcopy"])
logger = logging.getLogger(__name__)

class TextRequest(BaseModel):
    product: str
    tone: str
    length: str = "short"
    num_copies: int = 3
    model: str = "gpt-4.1-mini"

@router.post("/text")
async def create_text_ad(
    req: TextRequest,
    x_api_key: str = Depends(get_api_key_header),
):
    """
    텍스트 기반 광고 문구 생성.
    내부 오류를 그대로 500로 숨기지 않고 502(Bad Gateway)와 함께 메시지를 반환해
    프론트에서 원인을 바로 확인할 수 있도록 함.
    """
    try:
        return adcopy_text_model.generate_ad_copies(
            product=req.product,
            tone=req.tone,
            length=req.length,
            num_copies=req.num_copies,
            model=req.model,
        )
    except Exception as e:
        # 서버 로그에는 스택추적 남기고, 클라이언트엔 메시지 전달
        logger.exception("create_text_ad failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"create_text_ad 실패: {e}",
        )

@router.post("/image")
async def create_image_ad(
    file: UploadFile = File(...),
    tone: str = Form("감성적인"),
    length: str = Form("short"),
    num_copies: int = Form(3),
    model: str = Form("gpt-4.1-mini"),
    x_api_key: str = Depends(get_api_key_header),
):
    """
    이미지 기반 광고 문구 생성.
    마찬가지로 예외를 502로 변환해 프론트에서 원인 메시지를 볼 수 있게 함.
    """
    try:
        image_bytes = await file.read()
        return adcopy_image_model.generate_ad_from_image(
            image_bytes=image_bytes,
            tone=tone,
            length=length,
            num_copies=num_copies,
            model=model,
        )
    except Exception as e:
        logger.exception("create_image_ad failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"create_image_ad 실패: {e}",
        )