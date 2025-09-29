from typing import Tuple, List, Optional
from dotenv import load_dotenv
import os, json, io, base64
from openai import OpenAI
from backend.models.cardnews_model import CardNewsTextRequest, CardNewsImgRequest
from PIL import Image
import requests


# 환경 변수 로드
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 설정
client = OpenAI(api_key=OPENAI_KEY)

def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.strip()
    if h.startswith("#") and len(h) == 7:
        return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
    return (20, 20, 20)

def normalize_page_item(x) -> str:
    if isinstance(x, dict):
        title = x.get("title") or ""
        body = x.get("body") or ""
        return f"{title}\n{body}"
    return str(x).strip()

def generate_cardnews_text(req:CardNewsTextRequest) -> List[str]:
    """페이지별 텍스트 생성."""
    def normalize_page_item(x) -> str:
        if isinstance(x, dict):
            title = x.get("title") or ""
            body = x.get("body") or ""
            return f"{title}\n{body}"
        return str(x).strip()
    
    model = "gpt-5-mini"
    sys_prompt = (
        "너는 한국어 카드뉴스 카피라이터이며, 명확한 톤으로 페이지별 텍스트를 작성한다. "
        "사실만 기반으로 적어야 하고, 각 페이지의 제목은 1줄, 내용은 5줄 이내로 작성해야 한다."
        "내용이 너무 성의 없으면 안 됌. 자세하고 양질의 정보를 공유해야하며, 너무 간단하게 적으면 안됨."
        "출력은 JSON 배열로만, 길이는 페이지 수와 동일. 첫 번째 페이지는 강력한 제목과 서브헤드, 마지막 페이지는 정리 또는 CTA."
        "각 페이지의 내용은 JSON 객체 형식으로 `{'title': '제목', 'body': '내용'}`과 같이 반환해야 한다."
        "500자 이내. 불필요한 이모지/특수문자 금지. 본문은 단락으로 구분할 것."
    )

    user_prompt = {
        "num_pages": req.num_pages, "topic": req.topic, "purpose": req.purpose, "must_include": req.must,
        "audience": req.audience, "tone": req.tone, "language": req.lang,
    }
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)}
        ]
    )
    text = resp.choices[0].message.content
    s = text.find("["); e = text.rfind("]") + 1
    arr = json.loads(text[s:e])

    arr = [normalize_page_item(x) for x in arr][:req.num_pages]

    # 카드가 원하는 페이지 수 보다 부족하면 처리 인 것으로 보이는데, i가 정의 안 되어 있음.
    # if len(arr) < num_pages:
    #     arr += [f"페이지 {i+1} 내용"] * (num_pages - len(arr))

    # OpenAI 생성 실패 시 수동으로 텍스트를 생성하는 부분 제거
    return arr


def generate_b64image_with_openai(prompt: str, model: str='dall-e-3', size_str: str="1024x1024"):
    resp = client.images.generate(
        model=model,
        prompt=str(prompt)[:2000],
        size=size_str,
        response_format="b64_json",
    )

    d0 = resp.data[0]
    b64 = getattr(d0, "b64_json", None)
    return b64


