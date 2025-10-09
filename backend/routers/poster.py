# backend/routers/poster.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from backend.models.poster_text_model import PosterTextRequest, PosterTextResponse
from backend.models.poster_image_model import PosterImageRequest
from backend.services.poster_service import generate_text, generate_image, get_history
from backend.auth import get_current_user

router = APIRouter(prefix="/poster", tags=["Poster"])

# ---------------------------------------------------------
# 🧠 텍스트 생성
# ---------------------------------------------------------
@router.post(
    "/text",
    response_model=PosterTextResponse,
    summary="포스터용 광고 문구 생성",
    description="매장 정보 및 광고 유형(브랜드/제품/이벤트)을 기반으로 포스터용 텍스트를 생성합니다."
)
def create_text(req: PosterTextRequest, user=Depends(get_current_user)):
    """
    ✅ 광고 텍스트 자동 생성 엔드포인트  
    - 매장 공통 입력(`store_name`, `category`, `address` 등) 포함  
    - 광고 유형(`브랜드`, `제품`, `이벤트`)에 따라 프롬프트 달라짐
    """
    try:
        return generate_text(req)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"텍스트 생성 중 오류 발생: {e}"
        )


# ---------------------------------------------------------
# 🎨 이미지 생성
# ---------------------------------------------------------
@router.post(
    "/image",
    response_class=StreamingResponse,
    summary="포스터 이미지 생성",
    description="OpenAI DALL·E 3 모델을 사용해 포스터 이미지를 생성하고, 지정된 위치/폰트/색상 옵션으로 텍스트를 합성합니다."
)
def create_image(req: PosterImageRequest, user=Depends(get_current_user)):
    """
    ✅ 포스터 이미지 생성 엔드포인트  
    - DALL·E3로 이미지 생성 후, `NanumGothic.ttf` 폰트로 한글 텍스트 오버레이  
    - 제목/본문 색상, 폰트 크기, 위치 지정 가능  
    - 생성된 결과 이미지는 사용자 이메일 폴더(`data/user_info/{email}/poster_img/`)에 저장됨
    """
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인 정보 누락")
    try:
        return generate_image(req, email)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 생성 중 오류 발생: {e}"
        )


# ---------------------------------------------------------
# 🗂️ 히스토리 조회
# ---------------------------------------------------------
@router.get(
    "/history",
    summary="포스터 생성 히스토리 조회",
    description="DB에 저장된 사용자의 포스터 생성 이력을 반환합니다."
)
def get_ads_history(user=Depends(get_current_user)):
    """
    ✅ 포스터 생성 히스토리 조회  
    - 이메일 기준으로 DB에서 포스터 기록을 불러옴  
    - 제목/본문/이미지 경로/생성일 포함
    """
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인 정보 누락")

    history = get_history(email)
    if not history:
        return JSONResponse(content={"history": [], "message": "히스토리가 없습니다."})

    return JSONResponse(content={"history": history})
