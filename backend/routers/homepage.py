from fastapi import APIRouter, Depends

from backend.models.homepage_model import HomepageRequest,  GithubUploadRequest
from backend.services.homepage_service import generate_html, githubpage_upload
from backend.auth import get_current_user

router = APIRouter(prefix="/homepage", tags=["homepage"])

@router.post("/generate")
def create_text(req: HomepageRequest, user=Depends(get_current_user)):
    return generate_html(req)

@router.post("/upload")
def create_text(req: GithubUploadRequest, user=Depends(get_current_user)):
    return githubpage_upload(req)

