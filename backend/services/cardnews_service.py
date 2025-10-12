# backend/services/cardnews_service.py
from typing import Tuple, List
from dotenv import load_dotenv
import os, json, io, base64, sqlite3
from datetime import datetime
from openai import OpenAI
from backend.models.cardnews_model import CardNewsTextRequest
from PIL import Image
import requests

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

BASE_DIR = os.path.join("data", "user_info")
DB_PATH = os.path.join(BASE_DIR, "database.db")
os.makedirs(BASE_DIR, exist_ok=True)

def _ensure_db():
    os.makedirs(BASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cardnews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            title TEXT,
            zip_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

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

def generate_cardnews_text(req: CardNewsTextRequest) -> List[str]:
    """
    페이지별 텍스트 생성. 출력은 "제목\n본문" 형태 문자열 리스트
    """
    model = "gpt-4o-mini"  # 안정적인 저비용 모델(수정 가능)
    sys_prompt = (
        "너는 한국어 카드뉴스 카피라이터이며, 명확한 톤으로 페이지별 텍스트를 작성한다. "
        "사실만 기반으로 적어야 하고, 각 페이지의 제목은 1줄, 내용은 5줄 이내로 작성해야 한다. "
        "내용이 너무 성의 없으면 안 된다. 자세하고 양질의 정보를 공유하되 과장·허위는 금지. "
        "출력은 JSON 배열로만, 길이는 페이지 수와 동일. 첫 페이지는 강력한 제목+서브헤드, "
        "마지막 페이지는 요약 또는 CTA. 각 항목은 {'title': '제목', 'body': '내용'} 형식."
    )
    user_prompt = {
        "num_pages": req.num_pages,
        "topic": req.topic,
        "purpose": req.purpose,
        "must_include": req.must,
        "audience": req.audience,
        "tone": req.tone,
        "language": req.lang,
    }

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        temperature=0.7,
    )
    text = resp.choices[0].message.content or "[]"
    s = text.find("[")
    e = text.rfind("]") + 1
    raw = text[s:e] if (s != -1 and e != -1) else "[]"
    try:
        arr = json.loads(raw)
    except Exception:
        arr = []

    arr = [normalize_page_item(x) for x in arr][: req.num_pages]
    return arr

def generate_b64image_with_openai(prompt: str, model: str = "dall-e-3", size_str: str = "1024x1024"):
    resp = client.images.generate(
        model=model,
        prompt=str(prompt)[:2000],
        size=size_str,
        response_format="b64_json",
    )
    d0 = resp.data[0]
    b64 = getattr(d0, "b64_json", None)
    return b64

def save_cardnews(email: str, req: dict):
    """
    req: {
      "title": "카드뉴스 제목",
      "zip_b64": "base64(zip bytes)"
    }
    """
    _ensure_db()
    title = req.get("title") or "무제 카드뉴스"
    zip_b64 = req.get("zip_b64")
    if not zip_b64:
        raise ValueError("zip_b64가 필요합니다.")

    # 파일 저장
    user_dir = os.path.join(BASE_DIR, email, "cardnews")
    os.makedirs(user_dir, exist_ok=True)
    fname = f"cardnews_{int(datetime.now().timestamp())}.zip"
    save_path = os.path.join(user_dir, fname)
    with open(save_path, "wb") as f:
        f.write(base64.b64decode(zip_b64))

    # DB insert
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO cardnews (email, title, zip_path) VALUES (?, ?, ?)", (email, title, save_path))
    conn.commit()
    conn.close()

def get_history(email: str):
    """
    반환 형식:
    [
      {"id": 1, "title": "...", "created_at": "...", "zip_b64": "..."},
      ...
    ]
    ※ zip 파일 내용을 base64로 함께 내려줘서 프론트가 곧바로 다운로드 버튼 생성 가능
    """
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, title, zip_path, created_at FROM cardnews WHERE email=? ORDER BY created_at DESC", (email,))
    rows = cur.fetchall()
    conn.close()

    items = []
    for rid, title, zip_path, created_at in rows:
        try:
            with open(zip_path, "rb") as f:
                zb64 = base64.b64encode(f.read()).decode()
        except Exception:
            zb64 = ""
        items.append(
            {
                "id": rid,
                "title": title,
                "created_at": created_at,
                "zip_b64": zb64,
            }
        )
    return items
