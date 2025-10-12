from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.cardnews_model import CardNewsTextRequest
from backend.services.cardnews_service import generate_cardnews_text, generate_b64image_with_openai, save_cardnews, get_history
from backend.auth import get_current_user
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/cardnews", tags=["CardNews"])


@router.post("/generate/text")
def create_text(req: CardNewsTextRequest, user=Depends(get_current_user)):
    return generate_cardnews_text(req)

@router.post("/generate/b64img")
def generate_b64img(prompt: str, user=Depends(get_current_user)):
    return generate_b64image_with_openai(prompt=prompt)

@router.post("/save")
def save_card(req: dict, user=Depends(get_current_user)):
    """최종 카드뉴스 ZIP 저장"""
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인 필요")
    try:
        save_cardnews(email, req)
        return {"message": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}")

@router.get("/history")
def history(user=Depends(get_current_user)):
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인 필요")
    return JSONResponse(content={"history": get_history(email)})
