# 간단한 인증(헤더 기반 API 키) 데코레이터/의존성. 개발용으로 간단히 BACKEND_API_KEY 환경변수와 비교.

# backend/services/auth.py

import os
from fastapi import Header, HTTPException

API_KEY = os.getenv("BACKEND_API_KEY", "team2-key")  # .env나 secrets로 관리 가능

def get_api_key_header(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key