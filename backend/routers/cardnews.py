from fastapi import APIRouter, Depends
import io
from backend.models.cardnews_model import CardNewsTextRequest, CardNewsImgRequest
from backend.services.cardnews_service import generate_cardnews_text, generate_b64image_with_openai
from backend.auth import get_current_user

router = APIRouter(prefix="/cardnews", tags=["cardnews"])

@router.post("/generate/text")
def create_text(req: CardNewsTextRequest, user=Depends(get_current_user)):
    return generate_cardnews_text(req)

@router.post("/generate/b64img")
def generate_b64img(prompt: str, user=Depends(get_current_user)):
    return generate_b64image_with_openai(prompt=prompt)
