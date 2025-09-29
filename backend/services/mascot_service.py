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
    2. 로고, 그림자, 배경을 포함하지 않습니다.
    3. 단 하나의 캐릭터를 생성합니다.

    [출력 형태 가이드]
    - "2d": 애니메이션이나 만화 같은 평면적인 느낌, 단순한 선과 색감
    - "3d": 입체적인 질감과 깊이를 가진 스타일, 사실적이거나 귀여운 3D 피규어 같은 느낌
    - "픽셀": 고전 게임 그래픽처럼 작은 픽셀로 이루어진 레트로 스타일
    - "카툰": 과장된 표정과 선명한 색감을 가진 만화풍 스타일
    - "실사 일러스트": 현실적인 디테일을 강조한 반실사 풍의 캐릭터
    - "미니멀": 불필요한 디테일을 줄이고 단순한 도형과 색상 위주로 표현
    - "심볼/아이콘": 로고처럼 간결하고 상징적인 형태로 제작
    - "수채화풍": 붓질과 번짐 효과가 느껴지는 따뜻한 수채화 느낌
    - "사이버/메카닉": 금속 질감, 네온 라이트, 미래적인 디자인 요소가 포함된 스타일

    [참고]
    - 대표 색상: {req.main_color}
    - 키워드: {req.keyword}
    - 캐릭터의 성격: {req.mascot_personality}
    - 브랜드 분위기: {req.mood}
    - 출력 형태: {req.output_style}
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