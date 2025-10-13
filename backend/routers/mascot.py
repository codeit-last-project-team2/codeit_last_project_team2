from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from backend.models.mascot_model import MascotRequest, MascotHistoryItem
from backend.services.mascot_service import (
    generate_mascot_url_candidates,
    save_mascot_history,
    get_mascot_history
)
from backend.auth import get_current_user

router = APIRouter(prefix="/mascot", tags=["mascot"])

# 마스코트 이미지 후보 생성
@router.post("/generate")
def create_mascot(req: MascotRequest, user=Depends(get_current_user)):
    return generate_mascot_url_candidates(req)

# 마스코트 히스토리 저장
@router.post("/save")
def save_mascot(item: MascotHistoryItem, user=Depends(get_current_user)):
    save_mascot_history(item)
    return {"message": "saved"}

# 마스코트 히스토리 조회
@router.get("/history")
def history(user=Depends(get_current_user)):
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인 정보 누락")

    history = get_mascot_history(email)
    if not history:
        return JSONResponse(content={"history": [], "message": "히스토리가 없습니다."})

    return JSONResponse(content={"history": history})
