from fastapi import APIRouter, Depends
from backend.models.user_information_model import UserInformationRequest
from backend.services.userinformation_service import save_user_info, get_user_info
from backend.auth import get_current_user

router = APIRouter(prefix="/userinfo", tags=["userinfo"])

# 매장 정보 저장/업데이트
@router.post("/save")
def save_info(req: UserInformationRequest, user=Depends(get_current_user)):
    return save_user_info(req)

# 매장 정보 조회
@router.get("/{email}")
def read_info(email: str, user=Depends(get_current_user)):
    return get_user_info(email)
