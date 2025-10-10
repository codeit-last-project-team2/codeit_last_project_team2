import sys, os
import io
import base64
import zipfile
from datetime import datetime
from typing import List, Tuple

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np
import glob

# -----------------------------
# 프로젝트 루트 잡기
# -----------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.services.cardnews_service import hex_to_rgb

# -----------------------------
# 백엔드 URL
# -----------------------------
BACKEND_URL = "http://127.0.0.1:8000"

# -----------------------------
# 로그인 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(page_title="Card News Studio", layout="wide")
st.title("🗂️ 카드 뉴스 스튜디오")
st.caption("주제 → 텍스트 생성/편집 → 배경 → 오버레이 → 폰트 → 합성 → 다운로드")

# -----------------------------
# 세션 상태 초기화
# -----------------------------
if "project" not in st.session_state:
    st.session_state.project = {
        "num_pages": 3,
        "topic": "",
        "purpose": "정보 공유",
        "must_include": "",
        "audience": "일반 대중",
        "tone": "친근하고 명확한",
        "lang": "ko",

        "page_texts": [],
        "base_images": [],
        "overlay_images": [],
        "final_images": [],

        "img_size": (1080, 1080),
        "bg_method": "그라디언트",
        "bg_color": (245, 246, 250),
        "grad_start": (245, 246, 250),
        "grad_end": (218, 224, 238),

        "font_path": None,
        "font_size": 48,
        "font_color": (20, 20, 20),  # ✅ 추가: 폰트 색상 기본값
        "overlay_opacity": 100,
    }

proj = st.session_state.project

# -----------------------------
# 유틸 함수
# -----------------------------
def pil_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def export_zip(images: List[Image.Image]) -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, im in enumerate(images, start=1):
            zf.writestr(f"card_{i:02d}.png", pil_to_png_bytes(im))
    mem.seek(0)
    return mem.read()

def place_overlay(canvas: Image.Image, overlay: Image.Image,
                  opacity: int = 100) -> Image.Image:
    can = canvas.convert("RGBA")
    W, H = can.size
    ov = overlay.convert("RGBA")

    target_area = int(W * H * 0.8)
    ratio = ov.width / max(1, ov.height)
    new_w = int((target_area * ratio) ** 0.5)
    new_h = max(1, int(new_w / ratio))
    ov = ov.resize((new_w, new_h), Image.LANCZOS)

    if opacity < 100:
        alpha = ov.split()[-1]
        alpha = alpha.point(lambda p: int(p * (opacity / 100.0)))
        ov.putalpha(alpha)

    x = W // 2 - ov.width // 2
    y = H // 2 - ov.height // 2
    can.paste(ov, (x, y), ov)
    return can

def wrap_text_simple(text: str, width: int = 22) -> str:
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= width and ch == " ":
            lines.append(cur.rstrip())
            cur = ""
    if cur:
        lines.append(cur)
    return "\n".join(lines)

def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# -----------------------------
# 0) 기본 정보 입력
# -----------------------------
st.markdown("### 📋 0) 기본 정보 입력")
col1, col2 = st.columns(2)
with col1:
    proj["topic"] = st.text_input("주제", value=proj["topic"], placeholder="예: 초보를 위한 ETF 가이드")
    proj["purpose"] = st.selectbox("용도", ["정보 공유", "행사", "광고", "공지", "채용"],
                                   index=["정보 공유", "행사", "광고", "공지", "채용"].index(proj["purpose"]))
    proj["must_include"] = st.text_area("필수 포함 문구", value=proj["must_include"])
with col2:
    proj["audience"] = st.text_input("대상", value=proj["audience"])
    proj["tone"] = st.text_input("톤&매너", value=proj["tone"])
    proj["lang"] = st.selectbox("언어", ["ko", "en"], index=0 if proj["lang"] == "ko" else 1)
    proj["num_pages"] = st.slider("페이지 수", 3, 7, value=proj["num_pages"])

# -----------------------------
# 1) 텍스트 생성
# -----------------------------
st.markdown("### 📝 1) 텍스트 생성 & 편집")
if st.button("✍️ 페이지별 텍스트 생성", type="primary"):
    req_body = {
        "num_pages": proj["num_pages"],
        "topic": proj["topic"],
        "purpose": proj["purpose"],
        "must": proj["must_include"],
        "audience": proj["audience"],
        "tone": proj["tone"],
        "lang": proj["lang"],
    }
    res = requests.post(f"{BACKEND_URL}/cardnews/generate/text", json=req_body, headers=headers)
    if res.status_code == 200:
        proj["page_texts"] = res.json()
        st.success("텍스트 생성 완료 ✅")
    else:
        st.error(f"실패: {res.text}")

for i in range(proj["num_pages"]):
    default = proj["page_texts"][i] if i < len(proj["page_texts"]) else ""
    proj["page_texts"][i:i+1] = [st.text_area(f"페이지 {i+1}", value=default, height=120)]

# -----------------------------
# 2) 배경 생성
# -----------------------------
st.markdown("### 🖼️ 2) 배경 생성")
bg_method = st.radio("배경 방식", ["단색", "그라디언트", "이미지 업로드"],
                     index=["단색", "그라디언트", "이미지 업로드"].index(proj["bg_method"]))
proj["bg_method"] = bg_method

if bg_method == "단색":
    color = st.color_picker("배경 색상", "#F5F6FA")
    proj["bg_color"] = hex_to_rgb(color)
elif bg_method == "그라디언트":
    c1 = st.color_picker("시작 색", "#F5F6FA")
    c2 = st.color_picker("끝 색", "#DAE0EE")
    proj["grad_start"] = hex_to_rgb(c1)
    proj["grad_end"] = hex_to_rgb(c2)
else:
    up_bg = st.file_uploader("배경 이미지 업로드", type=["png", "jpg", "jpeg", "webp"])

if st.button("🖼️ 배경 만들기/적용"):
    new_bases = []
    for _ in range(proj["num_pages"]):
        if bg_method == "단색":
            new_bases.append(Image.new("RGB", proj["img_size"], proj["bg_color"]))
        elif bg_method == "그라디언트":
            base = Image.new("RGB", proj["img_size"], proj["grad_start"])
            top = Image.new("RGB", proj["img_size"], proj["grad_end"])
            mask = Image.linear_gradient("L").resize((1, proj["img_size"][1])).resize(proj["img_size"])
            grad = Image.composite(top, base, mask)
            new_bases.append(grad)
        else:
            if up_bg:
                im = Image.open(up_bg).convert("RGBA").resize(proj["img_size"])
                new_bases.append(im)
            else:
                new_bases.append(Image.new("RGB", proj["img_size"], proj["grad_start"]))
    proj["base_images"] = new_bases
    st.success("배경 적용 완료 ✅")

    if proj["base_images"]:
        st.markdown("**배경 미리보기**")
        cols = st.columns(min(4, len(proj["base_images"])) or 1)
        for i, im in enumerate(proj["base_images"]):
            with cols[i % len(cols)]:
                st.image(im.convert("RGB"), caption=f"페이지 {i+1}", width="stretch")

# -----------------------------
# 3) 오버레이
# -----------------------------
st.markdown("### 🎨 3) 오버레이")
use_overlay = st.checkbox("오버레이 사용", value=len(proj.get("overlay_images", [])) > 0)

if use_overlay:
    src = st.radio("소스", ["업로드", "DALL·E 3"])
    if src == "업로드":
        files = st.file_uploader("오버레이 업로드", type=["png", "jpg"], accept_multiple_files=True)
        if files:
            proj["overlay_images"] = [Image.open(f).convert("RGBA") for f in files]
            st.success("오버레이 업로드 완료 ✅")
    else:
        if st.button("🎨 DALL·E 3로 오버레이 생성"):
            imgs = []
            for i, txt in enumerate(proj["page_texts"]):
                title = txt.split("\n")[0][:60] if txt else proj["topic"]
                r = requests.post(f"{BACKEND_URL}/cardnews/generate/b64img",
                                  params={"prompt": f"{proj['topic']} / 핵심: {title}"},
                                  headers=headers)
                if r.status_code == 200:
                    b64_str = r.json()
                    img = Image.open(io.BytesIO(base64.b64decode(b64_str))).convert("RGBA")
                    imgs.append(img)
            proj["overlay_images"] = imgs
            st.success("오버레이 생성 완료 ✅")

    proj["overlay_opacity"] = st.slider("오버레이 투명도 (%)", 0, 100, proj["overlay_opacity"])

    if proj.get("overlay_images") and proj.get("base_images"):
        st.markdown("**배경 + 오버레이 적용 미리보기**")
        cols = st.columns(min(4, len(proj["base_images"])) or 1)
        for i, bg in enumerate(proj["base_images"]):
            with cols[i % len(cols)]:
                ov = proj["overlay_images"][i % len(proj["overlay_images"])]
                preview = place_overlay(bg, ov, opacity=proj["overlay_opacity"])
                st.image(preview, caption=f"페이지 {i+1}", width="stretch")

# -----------------------------
# 4) 텍스트 폰트
# -----------------------------
st.markdown("### 🔤 4) 텍스트 폰트 설정")

font_files = glob.glob("data/fonts/*.ttf") + glob.glob("data/fonts/*.otf")
font_names = [os.path.basename(f) for f in font_files]
if font_files:
    selected_font = st.selectbox("폰트 선택", font_names)
    proj["font_path"] = font_files[font_names.index(selected_font)]
else:
    proj["font_path"] = None

proj["font_size"] = st.slider("폰트 크기", 20, 100, proj["font_size"])

# ✅ 폰트 색상 선택 추가
font_color_hex = st.color_picker("폰트 색상", "#141414")
proj["font_color"] = hex_to_rgb(font_color_hex)

# ✅ 폰트 미리보기
if proj["font_path"]:
    try:
        font = load_font(proj["font_path"], proj["font_size"])
        preview_img = Image.new("RGB", (600, 120), "white")
        d = ImageDraw.Draw(preview_img)
        d.text((20, 40), "폰트 미리보기 ABC 가나다", font=font, fill=proj["font_color"])
        st.image(preview_img, caption="폰트 미리보기", width="stretch")
    except Exception as e:
        st.warning(f"폰트 로드 실패: {e}")

# -----------------------------
# 5) 합성 (중앙 + 폰트 색상)
# -----------------------------
st.markdown("### ✒️ 5) 합성")
if st.button("합성 실행"):
    finals = []
    for i, bg in enumerate(proj["base_images"]):
        im = bg.copy().convert("RGBA")
        text = proj["page_texts"][i] if i < len(proj["page_texts"]) else ""

        if use_overlay and proj.get("overlay_images"):
            ov = proj["overlay_images"][i % len(proj["overlay_images"])]
            im = place_overlay(im, ov, opacity=proj["overlay_opacity"])

        font = load_font(proj["font_path"], proj["font_size"])
        wrapped = wrap_text_simple(text)
        draw = ImageDraw.Draw(im)
        text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        W, H = im.size
        x = (W - text_w) / 2
        y = (H - text_h) / 2
        draw.multiline_text((x, y), wrapped, fill=proj["font_color"],
                            font=font, align="center", spacing=8)

        finals.append(im.convert("RGB"))
    proj["final_images"] = finals
    st.success("합성 완료 ✅")

if proj.get("final_images"):
    st.markdown("**최종 미리보기**")
    cols = st.columns(min(4, len(proj["final_images"])) or 1)
    for i, im in enumerate(proj["final_images"]):
        with cols[i % len(cols)]:
            st.image(im, caption=f"페이지 {i+1}", width="stretch")

# -----------------------------
# 6) 다운로드
# -----------------------------
st.markdown("### 💾 6) 다운로드")
if proj.get("final_images"):
    zbytes = export_zip(proj["final_images"])
    st.download_button("📦 PNG ZIP 다운로드", zbytes,
                       file_name=f"cardnews_{datetime.now().strftime('%Y%m%d_%H%M')}.zip")
else:
    st.info("최종 이미지가 없습니다. 합성을 실행하세요.")
