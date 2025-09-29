from fastapi import APIRouter, Depends
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
    return get_mascot_history(user["email"])
