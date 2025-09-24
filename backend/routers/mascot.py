from fastapi import APIRouter, Depends

from backend.models.mascot_model import MascotRequest
from backend.services.mascot_service import generate_mascot_url_candidates
from backend.auth import get_current_user

router = APIRouter(prefix="/mascot", tags=["mascot"])

@router.post("/generate")
def create_text(req: MascotRequest, user=Depends(get_current_user)):
    return generate_mascot_url_candidates(req)

