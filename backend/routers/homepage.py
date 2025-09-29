from fastapi import APIRouter, Depends

from backend.models.homepage_model import GithubUploadRequest, HomepageRequest

from backend.services.homepage_service import generate_html, githubpage_upload
from backend.auth import get_current_user

router = APIRouter(prefix="/homepage", tags=["homepage"])

@router.post("/generate")
def create_html(req: HomepageRequest, user=Depends(get_current_user)):
    return generate_html(req)

@router.post("/upload")
def upload(req: GithubUploadRequest, user=Depends(get_current_user)):
    return githubpage_upload(req)

