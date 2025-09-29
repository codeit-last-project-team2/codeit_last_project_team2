from backend.models.mascot_model import MascotRequest

from openai import OpenAI

import os

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 마스코트 이미지 링크 생성
def generate_mascot_url_candidates(req: MascotRequest, num:int=3):
    """
    사용자 입력을 기반으로 여러 개의 마스코트 후보를 생성
    """
    prompt = f"""
    브랜드 홍보를 위한 마스코트를 제작할 것입니다.
    아래의 [조건]과 [참고]를 활용하여 마스코트 생성해주세요.

    [조건]
    1. 배경은 반드시 흰색입니다.
    2. 마스코트를 제외한 모든 요소(로고, 그림자, 배경 등)는 생성하지 않습니다.

    [참고]
    - 대표 색상: {req.main_color}
    - 키워드: {req.keyword}
    - 캐릭터의 성격: {req.personality}
    - 브랜드 소개: {req.brand_intro}
    - 추가 요구 사항: {req.additional_requirements}
    """

    urls = []
    for _ in range(num):
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        urls.append(result.data[0].url)
    return urls