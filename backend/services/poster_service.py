# backend/services/poster_service.py
import os
import sqlite3
import requests
import re
import json
from io import BytesIO
from datetime import datetime
from openai import OpenAI
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont
from backend.models.poster_text_model import PosterTextRequest, PosterTextResponse
from backend.models.poster_image_model import PosterImageRequest

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 경로 설정
FONT_PATH = "data/font/NanumGothic.ttf"
DATA_DIR = os.path.join("data", "images")
DB_PATH = os.path.join(DATA_DIR, "adgen.db")
os.makedirs(DATA_DIR, exist_ok=True)

# JSON 파서
def parse_json_block(text: str):
    try:
        m = re.search(r"\{.*\}", text, flags=re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}

# 텍스트 생성
def generate_text(req: PosterTextRequest) -> PosterTextResponse:
    prompt = f"""
    - 상품: {req.product}
    - 이벤트: {req.event}
    - 날짜: {req.date}
    - 장소: {req.location}
    - 분위기: {req.vibe}

    출력 JSON:
    {{
        "TITLE_KO": "한 줄 광고 제목",
        "BODY_KO": "짧은 설명 문구",
        "DALLE_PROMPT_EN": "영어 프롬프트 (no text)"
    }}
    """
    res = client.chat.completions.create(
        model=req.gpt_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    data = parse_json_block(res.choices[0].message.content)
    return PosterTextResponse(
        title=data.get("TITLE_KO", "제목 미정"),
        body=data.get("BODY_KO", "본문 미정"),
        dalle_prompt=data.get("DALLE_PROMPT_EN", "A promotional poster without text"),
    )

# 이미지 생성
def generate_image(req: PosterImageRequest, email: str):
    resp = client.images.generate(
        model="dall-e-3",
        prompt=req.dalle_prompt,
        size=req.dalle_size,
    )
    img_url = resp.data[0].url
    img = Image.open(BytesIO(requests.get(img_url).content)).convert("RGBA")

    # 텍스트 합성
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype(FONT_PATH, 80)
    font_body = ImageFont.truetype(FONT_PATH, 50)

    if req.position == "top":
        y_title = 60
    elif req.position == "center":
        y_title = img.height // 3
    else:
        y_title = img.height - 400

    # 제목/본문 자동 줄바꿈
    def wrap_text(text, font, max_width):
        words = text.split()
        lines, line = [], ""
        for w in words:
            test = f"{line} {w}".strip()
            if draw.textlength(test, font=font) <= max_width:
                line = test
            else:
                lines.append(line)
                line = w
        if line: lines.append(line)
        return lines

    title_lines = wrap_text(req.title, font_title, img.width - 120)
    body_lines = wrap_text(req.body, font_body, img.width - 120)

    y = y_title
    for line in title_lines:
        draw.text((60, y), line, font=font_title, fill=(255,255,255,255),
                  stroke_width=3, stroke_fill=(0,0,0,255))
        y += font_title.size + 10
    for line in body_lines:
        draw.text((60, y), line, font=font_body, fill=(255,255,0,255),
                  stroke_width=2, stroke_fill=(0,0,0,255))
        y += font_body.size + 5

    # 저장
    filename = f"poster_{int(datetime.now().timestamp())}.png"
    save_path = os.path.join(DATA_DIR, filename)
    img.save(save_path)

    # DB 저장
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            text TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    cur.execute("INSERT INTO ads (email, text, image_url) VALUES (?, ?, ?)",
                (email, f"{req.title}\n{req.body}", f"/images/{filename}"))
    conn.commit()
    conn.close()

    # 응답
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# 히스토리 조회
def get_history(email: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, text, image_url, created_at FROM ads WHERE email = ? ORDER BY created_at DESC", (email,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "text": r[1], "image_url": r[2], "created_at": r[3]} for r in rows]