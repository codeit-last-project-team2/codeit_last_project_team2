# backend/services/poster_service.py
import os, sqlite3, requests, re, json
from io import BytesIO
from datetime import datetime
from openai import OpenAI
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont
from backend.models.poster_text_model import PosterTextResponse
from backend.models.poster_image_model import PosterImageRequest

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 경로 설정
FONT_DIR = "data/fonts"
DEFAULT_FONT = "NanumGothic.ttf"
BASE_DIR = os.path.join("data", "user_info")
DB_PATH = os.path.join(BASE_DIR, "database.db")


# ---------------------------------------------------------
# JSON 파서
# ---------------------------------------------------------
def parse_json_block(text: str):
    try:
        m = re.search(r"\{.*\}", text, flags=re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


# ---------------------------------------------------------
# 텍스트 생성
# ---------------------------------------------------------
def generate_text(req) -> PosterTextResponse:
    store_name = getattr(req, "store_name", "")
    category = getattr(req, "category", "")
    address = getattr(req, "address", "")
    phone = getattr(req, "phone", "")
    ad_type = getattr(req, "ad_type", "브랜드")

    # 광고 유형별 세부 정보 구성
    if ad_type == "브랜드":
        content_desc = f"브랜드 소개: {getattr(req, 'brand_desc', '브랜드 설명 없음')}"
    elif ad_type == "제품":
        content_desc = f"제품명: {getattr(req, 'product_name', '제품명 미정')}, 특징: {getattr(req, 'product_feature', '특징 미정')}"
    else:
        period = getattr(req, 'event_period', [])
        period_text = f"{period[0]} ~ {period[1]}" if isinstance(period, list) and len(period) == 2 else "이벤트 기간 미정"
        content_desc = f"이벤트: {getattr(req, 'event_desc', '이벤트 내용 없음')} ({period_text})"

    vibe = getattr(req, "vibe", "분위기 미정")

    # 프롬프트 생성
    prompt = f"""
    당신은 소상공인 광고 전문가입니다.
    아래 정보를 바탕으로 감성적이면서도 직관적인 광고 문구를 만들어주세요.

    [매장 정보]
    - 상호명: {store_name}
    - 업종: {category}
    - 위치: {address}
    - 연락처: {phone}

    [광고 정보]
    - 광고 유형: {ad_type}
    - {content_desc}
    - 광고 분위기: {vibe}

    결과는 아래 JSON 형태로만 출력하세요:
    {{
        "TITLE_KO": "한 줄 광고 제목",
        "BODY_KO": "짧은 설명 문구",
        "DALLE_PROMPT_EN": "영어 이미지 프롬프트 (no text)"
    }}
    """

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    data = parse_json_block(res.choices[0].message.content)
    return PosterTextResponse(
        title=data.get("TITLE_KO", "제목 미정"),
        body=data.get("BODY_KO", "본문 미정"),
        dalle_prompt=data.get("DALLE_PROMPT_EN", "A promotional poster without text"),
    )


# ---------------------------------------------------------
# 색상 hex → RGBA 변환 유틸
# ---------------------------------------------------------
def _hex_to_rgba(hex_color: str, alpha: int = 255):
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c*2 for c in hex_color])
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b, alpha)
    except Exception:
        return (255, 255, 255, alpha)


# ---------------------------------------------------------
# 이미지 생성
# ---------------------------------------------------------
def generate_image(req: PosterImageRequest, email: str):
    # ✅ 폰트 경로 처리
    font_name = getattr(req, "font_name", DEFAULT_FONT)
    font_path = os.path.join(FONT_DIR, font_name)
    if not os.path.exists(font_path):
        font_path = os.path.join(FONT_DIR, DEFAULT_FONT)

    # ✅ 이미지 생성
    resp = client.images.generate(
        model="dall-e-3",
        prompt=req.dalle_prompt,
        size=req.dalle_size,
    )
    img_url = resp.data[0].url
    img = Image.open(BytesIO(requests.get(img_url).content)).convert("RGBA")

    draw = ImageDraw.Draw(img)

    # ✅ 선택한 폰트로 텍스트 그리기
    font_title = ImageFont.truetype(font_path, req.title_font_size)
    font_body = ImageFont.truetype(font_path, req.body_font_size)

    title_fill = _hex_to_rgba(req.title_color)
    body_fill = _hex_to_rgba(req.body_color)
    stroke_title = _hex_to_rgba(req.stroke_color_title)
    stroke_body = _hex_to_rgba(req.stroke_color_body)

    y_title = {"top": 60, "center": img.height // 3}.get(req.position, img.height - 400)

    # ✅ 텍스트 줄바꿈
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
        if line:
            lines.append(line)
        return lines

    max_width = img.width - 120
    y = y_title

    for line in wrap_text(req.title, font_title, max_width):
        draw.text((60, y), line, font=font_title, fill=title_fill,
                  stroke_width=req.stroke_width_title, stroke_fill=stroke_title)
        y += req.title_font_size + 10

    for line in wrap_text(req.body, font_body, max_width):
        draw.text((60, y), line, font=font_body, fill=body_fill,
                  stroke_width=req.stroke_width_body, stroke_fill=stroke_body)
        y += req.body_font_size + 5

    # ✅ 파일 저장
    data_dir = os.path.join(BASE_DIR, email, "poster_img")
    os.makedirs(data_dir, exist_ok=True)
    filename = f"poster_{int(datetime.now().timestamp())}.png"
    save_path = os.path.join(data_dir, filename)
    img.save(save_path)

    # ✅ DB 저장
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS poster (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            text TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("INSERT INTO poster (email, text, image_path) VALUES (?, ?, ?)",
                (email, f"{req.title}\n{req.body}", save_path))
    conn.commit()
    conn.close()

    # ✅ 응답 (이미지 바이너리 반환)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


# ---------------------------------------------------------
# 히스토리 조회
# ---------------------------------------------------------
def get_history(email: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, text, image_path, created_at 
        FROM poster 
        WHERE email = ? 
        ORDER BY created_at DESC
    """, (email,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "text": r[1],
            "image_path": r[2],
            "created_at": r[3]
        }
        for r in rows
    ]
