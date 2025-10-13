# FastAPI 라우터. /adcopy/text (JSON) 와 /adcopy/image (multipart/form-data) 엔드포인트 제공.

# backend/routers/adcopy.py
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
import logging

# 스키마는 models, 로직은 services
from backend.models.adcopy_model import AdcopyTextRequest, AdcopyTextResponse, AdcopyImageResponse
from backend.services.adcopy_service import generate_text, generate_image

# 팀의 JWT 인증
from backend.auth import get_current_user

router = APIRouter(prefix="/adcopy", tags=["Adcopy"])
logger = logging.getLogger(__name__)

@router.post("/text", response_model=AdcopyTextResponse)
async def create_text_ad(
    req: AdcopyTextRequest,
    # [MOD] JWT 토큰 필요
    user = Depends(get_current_user),
):
    try:
        return generate_text(req)
    except Exception as e:
        # 서버 로그에는 스택추적 남기고, 클라이언트엔 메시지 전달
        logger.exception("create_text_ad failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"create_text_ad 실패: {e}",
        )

@router.post("/image", response_model=AdcopyImageResponse)
async def create_image_ad(
    file: UploadFile = File(...),
    tone: str = Form("감성적인"),
    length: str = Form("short"),
    num_copies: int = Form(3),
    model: str = Form("gpt-4.1-mini"),
    # [MOD] JWT 토큰 필요
    user = Depends(get_current_user),
):
    try:
        image_bytes = await file.read()
        return generate_image(image_bytes, tone, length, num_copies, model)
    except Exception as e:
        logger.exception("create_image_ad failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"create_image_ad 실패: {e}",
        )