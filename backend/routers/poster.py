# backend/routers/poster.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from backend.models.poster_text_model import PosterTextRequest, PosterTextResponse
from backend.models.poster_image_model import PosterImageRequest
from backend.services.poster_service import generate_text, generate_image, get_history
from backend.auth import get_current_user

router = APIRouter(prefix="/poster", tags=["Poster"])

@router.post("/text", response_model=PosterTextResponse)
def create_text(req: PosterTextRequest, user=Depends(get_current_user)):
    return generate_text(req)

@router.post("/image")
def create_image(req: PosterImageRequest, user=Depends(get_current_user)):
    email = user["email"]
    return generate_image(req, email)

# 광고 히스토리 조회
@router.get("/history")
def get_ads_history(user=Depends(get_current_user)):
    email = user["email"]
    history = get_history(email)
    return JSONResponse(content={"history": history})
