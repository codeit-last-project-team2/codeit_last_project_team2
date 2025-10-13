from fastapi import APIRouter, Depends, Body
from fastapi.responses import HTMLResponse

from backend.services.homepage_service import generate_html, githubpage_upload
from backend.auth import get_current_user
from typing import Dict, Any

router = APIRouter(prefix="/homepage", tags=["homepage"])

@router.post("/generate", response_class=HTMLResponse)
def create_html(req: Dict[str, Any], user=Depends(get_current_user)):
    html = generate_html(req)
    return HTMLResponse(content=html)

@router.post("/upload")
def upload(html: str = Body(..., embed=True), user=Depends(get_current_user)):
    url = githubpage_upload(html, user["email"])
    return {"url": url}