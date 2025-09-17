import os
import json
import re
import requests
from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# -----------------------------
# OpenAI API Key (직접 선언)
# -----------------------------
OPENAI_API_KEY = ""
client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# Streamlit 기본 설정
# -----------------------------
st.set_page_config(page_title="포스터 광고 생성", page_icon="🖼️", layout="wide")

# -----------------------------
# Helper Functions
# -----------------------------
def parse_json_block(text: str) -> dict:
    try:
        m = re.search(r"\{.*\}", text, flags=re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}

def fit_text_to_width(text, font_path, max_width, font_size, min_size=20):
    while font_size > min_size:
        font = ImageFont.truetype(font_path, font_size)
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font
        font_size -= 2
    return ImageFont.truetype(font_path, min_size)

def draw_multiline_text(draw, xy, text, font_path, fill, outline,
                        stroke=3, max_width=None, start_size=80, min_size=20):
    if not text:
        return [], 0, start_size

    x, y = xy
    lines = []
    font = ImageFont.truetype(font_path, start_size)

    if max_width:
        words = text.split()
        line = ""
        for w in words:
            test_line = line + (" " if line else "") + w
            bbox = font.getbbox(test_line)
            w_width = bbox[2] - bbox[0]
            if w_width <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
    else:
        lines = text.split("\n")

    total_height = 0
    max_line_width = 0

    for line in lines:
        font = fit_text_to_width(line, font_path, max_width, start_size, min_size)
        _, _, w, h = font.getbbox(line)
        max_line_width = max(max_line_width, w)

        if stroke > 0:
            for dx in range(-stroke, stroke + 1):
                for dy in range(-stroke, stroke + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x+dx, y+dy), line, font=font, fill=outline)

        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + 12
        total_height += font.size + 12

    return lines, total_height, font.size

# -----------------------------
# 설명
# -----------------------------
st.title("🖼️ 포스터 광고 생성")

st.markdown("""
이 페이지에서는 **광고 포스터**를 자동으로 생성합니다.
""")

# -----------------------------
# 입력 UI (세션 유지용 key 추가)
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.text_input("상품명", key="product", placeholder="수제 햄버거")
    st.text_input("이벤트", key="event", placeholder="50% 할인 행사")
    st.text_input("날짜", key="date", placeholder="2025년 9월 20일")
    st.text_input("장소", key="location", placeholder="서울 강남역 매장")
    st.text_input("분위기/스타일", key="vibe", placeholder="따뜻한, 가족, 피크닉")

    st.selectbox("제목 위치 선택", ["top", "center", "bottom"], index=0, key="position")
    st.selectbox("텍스트 생성 모델 선택", ["gpt-4o", "gpt-5", "gpt-5-mini"], index=0, key="gpt_model")
    st.selectbox("이미지 크기", ["1024x1024", "1024x1792", "1792x1024"], index=0, key="dalle_size")

    go = st.button("🎨 포스터 생성", type="primary")

with col2:
    if "poster_img" not in st.session_state:
        st.session_state.poster_img = None
    result_area = st.empty()

# -----------------------------
# 실행
# -----------------------------
if go:
    # 공란일 경우 기본 문구로 대체
    product  = st.session_state.product or "상품명 미정"
    event    = st.session_state.event or "이벤트 미정"
    date     = st.session_state.date or "날짜 미정"
    location = st.session_state.location or "장소 미정"
    vibe     = st.session_state.vibe or "분위기 미정"

    with st.spinner("카피라이팅 생성 중..."):
        prompt = f"""
        - 상품: {product}
        - 이벤트: {event}
        - 날짜: {date}
        - 장소: {location}
        - 분위기: {vibe}

        출력 JSON:
        {{
          "TITLE_KO": "한 줄 광고 제목",
          "BODY_KO": "짧은 설명 문구",
          "DALLE_PROMPT_EN": "영어 프롬프트 (no text)"
        }}
        """
        res = client.chat.completions.create(
            model=st.session_state.gpt_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        data = parse_json_block(res.choices[0].message.content)

    title = data.get("TITLE_KO", "")
    body  = data.get("BODY_KO", "")
    dalle_prompt = data.get("DALLE_PROMPT_EN", "")

    with st.expander("생성된 DALL·E 프롬프트 보기"):
        st.code(dalle_prompt)

    with st.spinner("포스터 배경 생성 중..."):
        resp = client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt,
            size=st.session_state.dalle_size,
        )
        img_url = resp.data[0].url
        img = Image.open(BytesIO(requests.get(img_url).content)).convert("RGBA")

    FONT_PATH = "font/NanumGothic.ttf"
    margin = 60
    max_width = img.width - margin * 2

    if st.session_state.position == "top":
        title_y = 60
    elif st.session_state.position == "center":
        title_y = img.height // 3
    elif st.session_state.position == "bottom":
        title_y = img.height - 400
    else:
        title_y = 60

    draw = ImageDraw.Draw(img)
    lines_t, title_height, title_font_size = draw_multiline_text(
        draw, (margin, title_y), title, FONT_PATH,
        (255,255,255,255), (0,0,0,255),
        stroke=4, max_width=max_width, start_size=80
    )

    body_y = title_y + title_height + 30
    lines_b, body_height, body_font_size = draw_multiline_text(
        draw, (margin, body_y), body, FONT_PATH,
        (255,255,0,255), (0,0,0,255),
        stroke=3, max_width=max_width, start_size=50
    )

    while body_y + body_height > img.height - 60:
        img = Image.open(BytesIO(requests.get(img_url).content)).convert("RGBA")
        draw = ImageDraw.Draw(img)

        title_font_size = max(20, title_font_size - 4)
        body_font_size = max(16, body_font_size - 4)

        lines_t, title_height, _ = draw_multiline_text(
            draw, (margin, title_y), title, FONT_PATH,
            (255,255,255,255), (0,0,0,255),
            stroke=4, max_width=max_width, start_size=title_font_size
        )
        body_y = title_y + title_height + 30
        lines_b, body_height, _ = draw_multiline_text(
            draw, (margin, body_y), body, FONT_PATH,
            (255,255,0,255), (0,0,0,255),
            stroke=3, max_width=max_width, start_size=body_font_size
        )

        if title_font_size <= 20 and body_font_size <= 16:
            break

    # 최종 결과를 세션에 저장 (버튼 눌렀을 때만 갱신)
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.session_state.poster_img = buf.getvalue()

# -----------------------------
# 항상 마지막에 세션 이미지 표시
# -----------------------------
if st.session_state.poster_img:
    result_area.image(st.session_state.poster_img, caption="최종 포스터", use_container_width=True)
    st.download_button("📥 다운로드", data=st.session_state.poster_img,
                       file_name="poster.png", mime="image/png")
