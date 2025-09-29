import sys, os

# 프로젝트 루트 경로 잡기
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import streamlit as st
import io
import base64
import zipfile
from datetime import datetime
from typing import List, Tuple, Optional, Callable
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from openai import OpenAI
import requests
import os, json
from dotenv import load_dotenv

import numpy as np

from backend.services.cardnews_service import hex_to_rgb
# def hex_to_rgb(h: str) -> Tuple[int, int, int]:
#     h = h.strip()
#     if h.startswith("#") and len(h) == 7:
#         return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
#     return (20, 20, 20)

BACKEND_URL = "http://127.0.0.1:8000"

# -----------------------------
# 세션 값 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ====== 공통 유틸 ======
def use_openai() -> bool:
    try: 
        OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    except:
        return False
    
    if OPENAI_KEY is None:
        return False
    else:
        return True
    

def draw_round_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill):
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(xy, radius=radius, fill=fill)
    else:
        draw.rectangle(xy, fill=fill)

def wrap_text_by_width(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    lines: List[str] = []
    if not text:
        return [""]
    for raw_line in text.split("\n"):
        line = ""
        for ch in raw_line:
            test_line = line + ch
            try:
                if draw.textlength(test_line, font=font) <= max_width:
                    line = test_line
                else:
                    if line:
                        lines.append(line)
                    line = ch
            except AttributeError:
                if draw.textsize(test_line, font=font)[0] <= max_width:
                    line = test_line
                else:
                    if line:
                        lines.append(line)
                    line = ch
        if line:
            lines.append(line)
    return lines

def render_title_body_on_image(
    img: Image.Image,
    text: str,
    title_loader: Callable[[int], ImageFont.FreeTypeFont],
    body_loader: Callable[[int], ImageFont.FreeTypeFont],
    base_font_size: int,
    title_scale: float,
    title_color=(10, 10, 10),
    body_color=(20, 20, 20),
    align: str = "중앙",
    h_anchor: str = "중앙",
    v_pos_pct: int = 50,
    padding_pct: int = 7,
    shadow: bool = True,
    shadow_opacity: int = 170,
    box_bg: bool = False,
    box_opacity: int = 110,
    box_color=(255, 255, 255),
    box_radius: int = 18,
    box_inner_pad_pct: float = 1.6,
    watermark: str = "",
    line_spacing_ratio: float = 1.25
):
    canvas = img.convert("RGBA")
    W, H = canvas.size
    pad = int(min(W, H) * (padding_pct / 100.0))
    draw = ImageDraw.Draw(canvas, "RGBA")

    if "\n" in text:
        title_raw, body_raw = text.split("\n", 1)
    else:
        title_raw, body_raw = text, ""

    band_full = W - pad * 2
    anchor_x = {"왼쪽": pad + band_full * 0.25, "중앙": pad + band_full * 0.50, "오른쪽": pad + band_full * 0.75}.get(h_anchor, pad + band_full * 0.50)
    band_left = int(max(pad, anchor_x - band_full * 0.5))
    band_right = int(min(W - pad, anchor_x + band_full * 0.5))
    band_width = band_right - band_left

    tfont = title_loader(int(base_font_size * max(0.5, title_scale)))
    bfont = body_loader(base_font_size)

    def _wrap(tf, bf):
        t_lines = wrap_text_by_width(title_raw, draw, tf, band_width) if title_raw else []
        b_lines = wrap_text_by_width(body_raw, draw, bf, band_width) if body_raw else []
        try:
            t_bbox = draw.textbbox((0, 0), text="가", font=tf) if tf else (0, 0, 0, 0)
            b_bbox = draw.textbbox((0, 0), text="가", font=bf) if bf else (0, 0, 0, 0)
            th = t_bbox[3] - t_bbox[1] if tf else 0
            bh = b_bbox[3] - b_bbox[1] if bf else 0
        except AttributeError:
            th = tf.size * 1.2 if tf else 0
            bh = bf.size * 1.2 if bf else 0

        gap = int(min(th or bh or 0, bh or th or 0) * 0.6) if (t_lines and b_lines) else 0
        total_h = int(len(t_lines) * th * line_spacing_ratio + gap + len(b_lines) * bh * line_spacing_ratio)
        return t_lines, b_lines, th, bh, gap, total_h

    t_lines, b_lines, th, bh, gap, total_h = _wrap(tfont, bfont)
    avail_h = max(0, (H - pad * 2) - total_h)
    y = pad + int(avail_h * (v_pos_pct / 100.0))

    if box_bg and total_h > 0:
        inner = int(min(W, H) * (box_inner_pad_pct / 100.0))
        box_xy = [band_left - inner, max(0, y - inner), band_right + inner, min(H, y + total_h + inner)]
        rgba = (*box_color, int(box_opacity))
        draw_round_rect(draw, box_xy, radius=max(0, int(box_radius)), fill=rgba)

    def _draw_lines(lines, fnt, color, sy):
        yy = sy
        for line in lines:
            tw = int(draw.textlength(line, font=fnt))
            if align == "중앙":
                x = int(anchor_x - tw / 2)
            elif align == "우측":
                x = band_right - tw
            else:
                x = band_left
            x = max(pad, min(W - pad - tw, x))
            if shadow:
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                sh = ImageDraw.Draw(overlay, "RGBA")
                sh.text((x + 2, yy + 2), line, font=fnt, fill=(0, 0, 0, int(shadow_opacity)))
                canvas_alpha = Image.alpha_composite(canvas, overlay)
                canvas.paste(canvas_alpha, (0, 0))
            draw.text((x, yy), line, font=fnt, fill=(color[0], color[1], color[2], 255))
            try:
                bbox = draw.textbbox((0, 0), text="가", font=fnt)
                yy += int((bbox[3] - bbox[1]) * line_spacing_ratio)
            except AttributeError:
                yy += int(fnt.size * 1.2 * line_spacing_ratio)
        return yy

    cur = y
    cur = _draw_lines(t_lines, tfont, title_color, cur)
    if t_lines and b_lines:
        cur += gap
    _draw_lines(b_lines, bfont, body_color, cur)

    if watermark:
        wm_font = bfont
        tw = int(draw.textlength(watermark, font=wm_font))
        tx = W - pad - tw
        ty = H - pad - (wm_font.getbbox("가")[3] - wm_font.getbbox("가")[1])
        draw.text((tx, ty), watermark, font=wm_font, fill=(0, 0, 0, 90))

    return canvas
def render_text_on_image(
    img: Image.Image,
    text: str,
    font_loader: Callable[[int], ImageFont.FreeTypeFont],
    base_font_size: int = 64,
    text_color=(20, 20, 20),
    align: str = "중앙",
    h_anchor: str = "중앙",
    v_pos_pct: int = 50,
    padding_pct: int = 7,
    shadow: bool = True,
    shadow_opacity: int = 170,
    box_bg: bool = False,
    box_opacity: int = 110,
    box_color=(255, 255, 255),
    box_radius: int = 18,
    box_inner_pad_pct: float = 1.6,
    auto_fit: bool = True,
    watermark: str = "",
    line_spacing_ratio: float = 1.25
):
    canvas = img.convert("RGBA")
    W, H = canvas.size
    pad = int(min(W, H) * (padding_pct / 100.0))
    draw = ImageDraw.Draw(canvas, "RGBA")

    band_full = W - pad * 2
    anchor_x = {"왼쪽": pad + band_full * 0.25, "중앙": pad + band_full * 0.50, "오른쪽": pad + band_full * 0.75}.get(h_anchor, pad + band_full * 0.50)
    band_left = int(max(pad, anchor_x - band_full * 0.5))
    band_right = int(min(W - pad, anchor_x + band_full * 0.5))
    band_width = band_right - band_left

    f = font_loader(base_font_size)
    if auto_fit:
        for fs in range(base_font_size, 17, -2):
            f = font_loader(fs)
            lines = wrap_text_by_width(text, draw, f, band_width)
            try:
                bbox = draw.textbbox((0, 0), text="가", font=f)
                line_h = bbox[3] - bbox[1]
            except AttributeError:
                line_h = f.size * 1.2
            total_h = int(len(lines) * line_h * line_spacing_ratio)
            if total_h <= (H - pad * 2):
                break

    lines = wrap_text_by_width(text, draw, f, band_width) if text else [""]
    try:
        bbox = draw.textbbox((0, 0), text="가", font=f)
        line_h = bbox[3] - bbox[1]
    except AttributeError:
        line_h = f.size * 1.2

    total_h = int(len(lines) * line_h * line_spacing_ratio)
    avail_h = max(0, (H - pad * 2) - total_h)
    y = pad + int(avail_h * (v_pos_pct / 100.0))

    if box_bg and total_h > 0:
        inner = int(min(W, H) * (box_inner_pad_pct / 100.0))
        box_xy = [band_left - inner, max(0, y - inner), band_right + inner, min(H, y + total_h + inner)]
        rgba = (*box_color, int(box_opacity))
        draw_round_rect(draw, box_xy, radius=max(0, int(box_radius)), fill=rgba)

    for idx, line in enumerate(lines):
        tw = int(draw.textlength(line, font=f))
        if align == "중앙":
            x = int(anchor_x - tw / 2)
        elif align == "우측":
            x = band_right - tw
        else:
            x = band_left
        x = max(pad, min(W - pad - tw, x))
        yy = y + int(idx * line_h * line_spacing_ratio)
        if shadow:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sh = ImageDraw.Draw(overlay, "RGBA")
            sh.text((x + 2, yy + 2), line, font=f, fill=(0, 0, 0, int(shadow_opacity)))
            canvas = Image.alpha_composite(canvas, overlay)
            draw = ImageDraw.Draw(canvas, "RGBA")
        draw.text((x, yy), line, font=f, fill=(text_color[0], text_color[1], text_color[2], 255))

    if watermark:
        wm = font_loader(base_font_size)
        tw = int(draw.textlength(watermark, font=wm))
        tx = W - pad - tw
        ty = H - pad - (wm.getbbox("가")[3] - wm.getbbox("가")[1])
        draw.text((tx, ty), watermark, font=wm, fill=(0, 0, 0, 90))

    return canvas

# ====== 파일/내보내기 ======
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

def export_pdf(images: List[Image.Image]) -> bytes:
    mem = io.BytesIO()
    rgb = [im.convert("RGB") if im.mode != "RGB" else im for im in images]
    rgb[0].save(mem, format="PDF", save_all=True, append_images=rgb[1:])
    mem.seek(0)
    return mem.read()

    
# ====== 배경 생성 ======
def make_solid_bg(size: Tuple[int, int], color: Tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", size, color)

def make_vertical_gradient(size: Tuple[int, int], start: Tuple[int, int, int], end: Tuple[int, int, int]) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (w, h), start)
    top = Image.new("RGB", (w, h), end)
    mask = Image.linear_gradient("L").resize((1, h)).resize((w, h))
    return Image.composite(top, base, mask)

# ====== 오버레이 처리 ======
def remove_white_bg(im: Image.Image, thresh: int = 245) -> Image.Image:
    """흰 배경을 투명 처리(thresh 이상을 투명)."""
    arr = np.array(im.convert("RGBA"))
    r, g, b, a = arr.T
    white = (r >= thresh) & (g >= thresh) & (b >= thresh)
    arr[..., 3][white] = 0
    return Image.fromarray(arr)

def place_overlay(canvas: Image.Image, overlay: Image.Image,
                  scale_pct: int, center_x_pct: int, center_y_pct: int,
                  opacity: int = 100, shadow: bool = True, blur: int = 10, sh_opacity: int = 120, dx: int = 6, dy: int = 6) -> Image.Image:
    can = canvas.convert("RGBA")
    W, H = can.size
    ov = overlay.convert("RGBA")

    # 크기 계산: 짧은 변 기준
    base = min(W, H)
    target_w = int(base * (scale_pct / 100.0))
    ratio = ov.width / max(1, ov.height)
    if ratio >= 1:
        new_w = target_w
        new_h = int(target_w / ratio)
    else:
        new_h = target_w
        new_w = int(target_w * ratio)
    ov = ov.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)

    # 투명도 적용
    if opacity < 100:
        alpha = ov.split()[-1]
        alpha = alpha.point(lambda p: int(p * (opacity / 100.0)))
        ov.putalpha(alpha)

    # 위치
    cx = int(W * (center_x_pct / 100.0))
    cy = int(H * (center_y_pct / 100.0))
    x = cx - ov.width // 2
    y = cy - ov.height // 2

    # 섀도우
    if shadow:
        shadow_img = Image.new("RGBA", can.size, (0, 0, 0, 0))
        sh_layer = Image.new("RGBA", ov.size, (0, 0, 0, 0))
        sh_layer.putalpha(ov.split()[-1])
        sh_alpha = sh_layer.split()[-1].point(lambda p: int(p * (sh_opacity / 255.0)))
        sh_layer.putalpha(sh_alpha)
        sh_blur = sh_layer.filter(ImageFilter.GaussianBlur(radius=max(0, blur)))
        shadow_img.paste(sh_blur, (x + dx, y + dy), sh_blur)
        can = Image.alpha_composite(can, shadow_img)

    # 합성
    can.paste(ov, (x, y), ov)
    return can


# ====== 폰트 로더 ======
def make_font_loader(uploaded_file=None) -> Callable[[int], ImageFont.FreeTypeFont]:
    """
    업로드 파일이 있으면 해당 바이트로, 없으면 시스템 한글 폰트 후보로 로더를 만든다.
    반환: size -> ImageFont
    """
    if uploaded_file is not None:
        data = uploaded_file.getvalue()

        def loader(sz: int) -> ImageFont.FreeTypeFont:
            return ImageFont.truetype(io.BytesIO(data), size=sz)

        return loader

    candidates = []
    if os.name == "nt":  # Windows
        candidates = [
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/NanumGothicBold.ttf",
            "C:/Windows/Fonts/NanumGothic.ttf",
        ]
    else:  # macOS/Linux
        candidates = [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/Library/Fonts/AppleSDGothicNeo.ttc",
            "/System/Library/Fonts/AppleSDGothicNeo.dfont",
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        ]

    for p in candidates:
        if os.path.exists(p):
            def loader(sz: int, path=p) -> ImageFont.FreeTypeFont:
                return ImageFont.truetype(path, size=sz)

            return loader

    def fallback(sz: int) -> ImageFont.FreeTypeFont:
        return ImageFont.load_default()

    return fallback

# ====== 페이지 설정 ======
st.set_page_config(page_title="Card News Studio", layout="wide")
st.title("🗂️ 카드 뉴스 스튜디오")
st.caption("주제 → 텍스트 생성/편집 → 심플 배경 → (선택) 오버레이 → 텍스트 오버레이 → 다운로드")

# ====== 세션 상태 초기화 ======
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
        "image_prompts": [],
        # 배경
        "bg_method": "그라디언트",
        "bg_color": (245, 246, 250),
        "grad_start": (245, 246, 250),
        "grad_end": (218, 224, 238),
        "img_size": (1080, 1080),
        # 텍스트/위치
        "padding_pct": 7,
        "text_align": "중앙", # 줄 정렬: 좌측/중앙/우측
        "h_anchor": "중앙", # 블록 가로 위치: 왼쪽/중앙/오른쪽
        # 새로 추가: 수직 위치 프리셋 + 오프셋
        "v_preset": "중앙", # 상단/중앙/하단
        "v_offset": 0, # -40 ~ +40 (%)
        "shadow": True,
        "shadow_opacity": 170,
        # 텍스트 박스(가독성 배경)
        "box_bg": False, # 사용 여부
        "box_opacity": 110, # 0~255
        "box_color_hex": "#FFFFFF", # 박스 색
        "box_radius": 18, # 둥근 모서리(px)
        "box_inner_pad_pct": 1.6, # 내부여백(%)
        "base_font_size": 64,
        "auto_fit": True,
        "watermark": "",
        # 제목/본문 분리
        "split_style": True,
        "title_scale": 1.4,
        "title_color_hex": "#111111",
        "body_color_hex": "#141414",
        # 오버레이 설정
        "overlay_use": False,
        "overlay_source": "업로드", # 업로드 / OpenAI(DALL·E 3)
        "overlay_scale_pct": 35,
        "overlay_x_pct": 80,
        "overlay_y_pct": 20,
        "overlay_opacity": 85,
        "overlay_shadow": True,
        "overlay_shadow_blur": 12,
        "overlay_shadow_opacity": 120,
        "overlay_shadow_dx": 6,
        "overlay_shadow_dy": 6,
        "overlay_white_to_alpha": True,
        "overlay_white_thresh": 245,
        "image_model": "dall-e-3",
        # 추가: 행간 조절
        "line_spacing": 1.25,
    }

# ====== 사이드바: 전역 옵션 ======
st.sidebar.header("설정")
st.sidebar.caption(f"OpenAI 텍스트/이미지: {'활성화' if use_openai() else '비활성화'}")

# 세션 상태에서 값 불러오기
initial_state = st.session_state.project
num_pages = st.sidebar.slider("카드 장수", 3, 7, value=initial_state["num_pages"])
topic = st.sidebar.text_input("주제", value=initial_state["topic"], placeholder="예: 초보를 위한 ETF 가이드")
purpose = st.sidebar.selectbox("용도", ["정보 공유", "행사", "광고", "공지", "채용"],
                             index=["정보 공유", "행사", "광고", "공지", "채용"].index(initial_state["purpose"]))
must_include = st.sidebar.text_area("필수로 들어갈 내용", value=initial_state["must_include"])
audience = st.sidebar.text_input("대상", value=initial_state["audience"])
tone = st.sidebar.text_input("톤&매너", value=initial_state["tone"])
lang = st.sidebar.selectbox("언어", ["ko", "en"], index=0 if initial_state["lang"] == "ko" else 1)

# 세션 상태 업데이트
st.session_state.project.update({
    "num_pages": num_pages,
    "topic": topic,
    "purpose": purpose,
    "must_include": must_include,
    "audience": audience,
    "tone": tone,
    "lang": lang
})

# ====== 1) 텍스트 생성 & 편집 ======
st.subheader("1) 텍스트 생성 & 편집")
c1, c2 = st.columns([1, 1])
with c1:
    if st.button("✍️ 페이지별 텍스트 생성", type="primary"):
        with st.spinner("텍스트 생성 중..."):
            cardnewstextreq = {
                'num_pages':num_pages, 
                'topic':topic, 
                'purpose':purpose,
                'must':must_include,
                'audience':audience,
                'tone':tone,
                'lang':lang
            }

            res = requests.post(f"{BACKEND_URL}/cardnews/generate/text", json=cardnewstextreq, headers=headers)
            if res.status_code != 200:
                st.error(f"텍스트 생성 실패: {res.text}")
            else:
                texts = res.json() 
            
            st.session_state.project["page_texts"] = texts
            st.session_state.project["image_prompts"] = [f"{topic}, {purpose}, 핵심: " + t.split("\n")[0][:50] for t in texts]

with c2:
    if st.session_state.project["page_texts"]:
        st.success("생성 완료. 아래에서 직접 수정하세요.")

if not st.session_state.project["page_texts"]:
    st.info("왼쪽에서 정보 입력 후, \"페이지별 텍스트 생성\"을 눌러주세요.")
else:
    edited = []
    for i in range(num_pages):
        default = st.session_state.project["page_texts"][i] if i < len(st.session_state.project["page_texts"]) else ""
        edited.append(st.text_area(f"페이지 {i + 1} 텍스트", value=default, height=140, key=f"text_{i}"))
    st.session_state.project["page_texts"] = edited


# ====== 2) 배경 생성 ======
st.subheader("2) 배경 생성")
bg_a, bg_b, bg_c = st.columns([1.2, 1, 1])
with bg_a:
    # 수정된 코드: index 계산 로직을 더 안전하게 변경
    size_preset_options = ["정사각(1080x1080)", "세로(1080x1920)", "가로(1920x1080)", "사용자 지정"]
    current_size_str = f"({initial_state['img_size'][0]}x{initial_state['img_size'][1]})"
    current_size_preset = next((s for s in size_preset_options if current_size_str in s), "사용자 지정")
    
    size_preset = st.selectbox("이미지 크기", size_preset_options,
                               index=size_preset_options.index(current_size_preset))
    if size_preset == "정사각(1080x1080)":
        img_size = (1080, 1080)
    elif size_preset == "세로(1080x1920)":
        img_size = (1080, 1920)
    elif size_preset == "가로(1920x1080)":
        img_size = (1920, 1080)
    else:
        cw = st.number_input("가로(px)", 600, 4096, value=initial_state["img_size"][0])
        ch = st.number_input("세로(px)", 600, 4096, value=initial_state["img_size"][1])
        img_size = (int(cw), int(ch))
    st.session_state.project["img_size"] = img_size

with bg_b:
    bg_method = st.radio("배경 방식", ["단색", "그라디언트", "이미지 업로드"],
                         index=["단색", "그라디언트", "이미지 업로드"].index(initial_state["bg_method"]))
    st.session_state.project["bg_method"] = bg_method
    up_bg = None
    if bg_method == "단색":
        color = st.color_picker("배경 색상", "#F5F6FA")
        st.session_state.project["bg_color"] = hex_to_rgb(color)
    elif bg_method == "그라디언트":
        c1 = st.color_picker("시작 색", "#F5F6FA")
        c2 = st.color_picker("끝 색", "#DAE0EE")
        st.session_state.project["grad_start"] = hex_to_rgb(c1)
        st.session_state.project["grad_end"] = hex_to_rgb(c2)
    else:
        up_bg = st.file_uploader("배경 이미지 업로드", type=["png", "jpg", "jpeg", "webp"])

with bg_c:
    if st.button("🖼️ 배경 만들기/적용"):
        if not st.session_state.project["page_texts"]:
            st.warning("먼저 텍스트를 생성/편집하세요.")
        else:
            base_images = []
            with st.spinner("배경 적용 중..."):
                for _ in range(num_pages):
                    if bg_method == "단색":
                        base_images.append(make_solid_bg(img_size, st.session_state.project["bg_color"]))
                    elif bg_method == "그라디언트":
                        start = st.session_state.project["grad_start"]
                        end = st.session_state.project["grad_end"]
                        if start == end:
                            end = tuple(max(0, min(255, c - 24)) for c in start)
                        base_images.append(make_vertical_gradient(img_size, start, end))
                    else:
                        if up_bg is not None:
                            im = Image.open(up_bg).convert("RGBA").resize(img_size)
                            base_images.append(im)
                        else:
                            base_images.append(make_vertical_gradient(img_size, st.session_state.project["grad_start"], st.session_state.project["grad_end"]))
            st.session_state.project["base_images"] = base_images
            st.success("배경 적용 완료")

# 미리보기: 배경
if st.session_state.project["base_images"]:
    st.markdown("**배경 미리보기**")
    cols = st.columns(min(4, len(st.session_state.project["base_images"])) or 1)
    for i, im in enumerate(st.session_state.project["base_images"]):
        with cols[i % len(cols)]:
            st.image(im, caption=f"페이지 {i + 1}")

# ====== 2.5) 오버레이 (선택) ======
st.subheader("2.5) 오버레이(선택)")
ov_a, ov_b, ov_c = st.columns([1.2, 1, 1])
with ov_a:
    overlay_use = st.toggle("이미지 오버레이 사용", value=initial_state.get("overlay_use", False))
    st.session_state.project["overlay_use"] = overlay_use
    if overlay_use:
        overlay_source = st.selectbox("오버레이 소스", ["업로드", "OpenAI(DALL·E 3)"],
                                     index=["업로드", "OpenAI(DALL·E 3)"].index(initial_state.get("overlay_source", "업로드")))
        st.session_state.project["overlay_source"] = overlay_source
        if overlay_source == "업로드":
            up_overlays = st.file_uploader("오버레이 이미지 업로드(여러 장 가능, PNG 권장)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
            if up_overlays:
                st.session_state.project["overlay_images"] = [Image.open(f).convert("RGBA") for f in up_overlays]
        else:
            st.caption(f"OpenAI 이미지 생성: {'활성화' if use_openai() else '비활성화(미사용)'}")
            if st.button("🎨 DALL·E 3로 오버레이 생성"):
                if not use_openai():
                    st.warning("st.secrets에 OPENAI_API_KEY가 필요합니다.")
                elif not st.session_state.project["page_texts"]:
                    st.warning("먼저 텍스트를 생성/편집하세요.")
                else:
                    imgs = []
                    with st.spinner("오버레이 생성 중..."):
                    
                        for i, txt in enumerate(st.session_state.project["page_texts"]):
                            
                            temp_txt = txt.split('\\n')[0][:60]
                            size = [1024, 1024]
                            prompt = f"{topic}, {purpose}, 핵심: {temp_txt}"
                       
                            b64img_res = requests.post(f"{BACKEND_URL}/cardnews/generate/b64img", params={'prompt':prompt}, headers=headers)
                            
                            if b64img_res.status_code != 200:
                                st.error(f"이미지 생성 실패: {res.text}")
                            else:
                                b64img = b64img_res.json()
                            
                            img = Image.open(io.BytesIO(base64.b64decode(b64img)))
                            img = img.convert("RGBA").resize(size)

                            imgs.append(img)
                    st.session_state.project["overlay_images"] = imgs
                    st.success("오버레이 생성 완료")
with ov_b:
    if overlay_use:
        st.markdown("**오버레이 배치**")
        scale = st.slider("크기(짧은 변 대비 %)", 5, 100, value=int(initial_state.get("overlay_scale_pct", 50)))
        x_pct = st.slider("가로 위치(%)", 0, 100, value=int(initial_state.get("overlay_x_pct", 50)))
        y_pct = st.slider("세로 위치(%)", 0, 100, value=int(initial_state.get("overlay_y_pct", 50)))
        opacity = st.slider("투명도(%)", 0, 100, value=int(initial_state.get("overlay_opacity", 50)))
        st.session_state.project.update({
            "overlay_scale_pct": scale, "overlay_x_pct": x_pct, "overlay_y_pct": y_pct, "overlay_opacity": opacity
        })

with ov_c:
    if overlay_use:
        st.markdown("**오버레이 효과**")
        ov_shadow = st.toggle("드롭 섀도우", value=initial_state.get("overlay_shadow", True))
        ov_blur = st.slider("섀도우 블러", 0, 50, value=int(initial_state.get("overlay_shadow_blur", 12)))
        ov_sopa = st.slider("섀도우 불투명도(0~255)", 0, 255, value=int(initial_state.get("overlay_shadow_opacity", 120)))
        ov_dx = st.slider("섀도우 X 오프셋", -30, 30, value=int(initial_state.get("overlay_shadow_dx", 6)))
        ov_dy = st.slider("섀도우 Y 오프셋", -30, 30, value=int(initial_state.get("overlay_shadow_dy", 6)))
        white2alpha = st.toggle("흰 배경을 투명 처리", value=initial_state.get("overlay_white_to_alpha", True))
        white_thresh = st.slider("화이트 임계값", 200, 255, value=int(initial_state.get("overlay_white_thresh", 245)))
        st.session_state.project.update({
            "overlay_shadow": ov_shadow, "overlay_shadow_blur": ov_blur, "overlay_shadow_opacity": ov_sopa,
            "overlay_shadow_dx": ov_dx, "overlay_shadow_dy": ov_dy,
            "overlay_white_to_alpha": white2alpha, "overlay_white_thresh": white_thresh
        })


if overlay_use and st.session_state.project["overlay_images"] and st.session_state.project["base_images"]:
    st.markdown("---")
    st.subheader("오버레이 미리보기")
    
    # 여러 개의 이미지를 나란히 표시하기 위해 컬럼을 생성
    num_images = min(len(st.session_state.project["page_texts"]), len(st.session_state.project["overlay_images"]))
    cols = st.columns(num_images if num_images > 0 else 1)

    for i in range(num_images):
        with cols[i % len(cols)]:
            st.caption(f"페이지 {i + 1} 미리보기")
            
            # 첫 번째 페이지를 기준으로 미리보기 이미지를 생성합니다.
            base_img = st.session_state.project["base_images"][i].copy()
            ov_img = st.session_state.project["overlay_images"][i].copy()
            
            # 흰 배경 투명화 옵션 적용
            if st.session_state.project["overlay_white_to_alpha"]:
                ov_img = remove_white_bg(ov_img, st.session_state.project["overlay_white_thresh"])
            
            final_img_preview = place_overlay(
                canvas=base_img, 
                overlay=ov_img, 
                scale_pct=st.session_state.project["overlay_scale_pct"], 
                center_x_pct=st.session_state.project["overlay_x_pct"], 
                center_y_pct=st.session_state.project["overlay_y_pct"], 
                opacity=st.session_state.project["overlay_opacity"], 
                shadow=st.session_state.project["overlay_shadow"], 
                blur=st.session_state.project["overlay_shadow_blur"], 
                sh_opacity=st.session_state.project["overlay_shadow_opacity"], 
                dx=st.session_state.project["overlay_shadow_dx"], 
                dy=st.session_state.project["overlay_shadow_dy"]
            )
            # 이미지 크기 조절 옵션을 추가하여 컨테이너에 맞게 표시
            st.image(final_img_preview, use_container_width=True)
# ====== 3) 폰트 & 텍스트 오버레이 ======
st.subheader("3) 폰트 선택 & 텍스트 오버레이")
fon_a, fon_b, fon_c, fon_d = st.columns([1.4, 1, 1, 1])

with fon_a:
    body_font_file = st.file_uploader("본문 폰트 업로드(TTF/OTF/TTC)", type=["ttf", "otf", "ttc"])
    if body_font_file:
        st.session_state["body_font_file_obj"] = body_font_file

    # 🔧 step=1로 +/- 클릭 감도 보장
    base_font_size = st.number_input("기본 폰트 크기(pt)", 18, 160, value=initial_state["base_font_size"], step=1)
    auto_fit = st.toggle("박스에 맞게 자동 축소", value=initial_state["auto_fit"])

    body_color_hex = st.color_picker("본문 색", value=initial_state.get("body_color_hex", "#141414"))
    body_color = hex_to_rgb(body_color_hex)

    # ✅ 위젯 값 → 세션 반영 (핵심 수정)
    st.session_state.project.update({
        "body_color_hex": body_color_hex,
        "base_font_size": int(base_font_size),
        "auto_fit": bool(auto_fit),
    })

with fon_b:
    text_align = st.selectbox("줄 정렬", ["중앙", "좌측", "우측"],
                             index=["중앙", "좌측", "우측"].index(initial_state["text_align"]))
    h_anchor = st.radio("텍스트 위치(가로)", ["왼쪽", "중앙", "오른쪽"],
                        index=["왼쪽", "중앙", "오른쪽"].index(initial_state.get("h_anchor", "중앙")))
    v_preset = st.radio("수직 위치 프리셋", ["상단", "중앙", "하단"],
                        index=["상단", "중앙", "하단"].index(initial_state.get("v_preset", "중앙")))
    v_offset = st.slider("세밀 조정(%)", -40, 40, value=int(initial_state.get("v_offset", 0)))
    line_spacing = st.slider("행간(줄 간격) 조절", 1.0, 3.0, value=initial_state.get("line_spacing", 1.25), step=0.05)
    st.session_state.project.update({
        "text_align": text_align, "h_anchor": h_anchor, "v_preset": v_preset, "v_offset": v_offset,
        "line_spacing": float(line_spacing)
    })
    padding_pct = st.slider("여백(%)", 2, 15, value=initial_state["padding_pct"])
    st.session_state.project["padding_pct"] = padding_pct
with fon_c:
    box_bg = st.toggle("텍스트 박스 사용", value=initial_state["box_bg"])
    box_color_hex = st.color_picker("텍스트 박스 색", value=initial_state.get("box_color_hex", "#FFFFFF"))
    box_opacity = st.slider("박스 투명도(0~255)", 0, 255, value=initial_state["box_opacity"]) if box_bg else initial_state["box_opacity"]
    box_radius = st.slider("박스 라운드(px)", 0, 64, value=int(initial_state.get("box_radius", 18))) if box_bg else initial_state.get("box_radius", 18)
    box_inner_pad_pct = st.slider("박스 내부 여백(%)", 0.0, 5.0, value=float(initial_state.get("box_inner_pad_pct", 1.6))) if box_bg else initial_state.get("box_inner_pad_pct", 1.6)
    st.session_state.project.update({
        "box_bg": box_bg, "box_color_hex": box_color_hex, "box_opacity": box_opacity,
        "box_radius": box_radius, "box_inner_pad_pct": float(box_inner_pad_pct)
    })
with fon_d:
    st.markdown("**제목/본문 스타일**")
    split_style = st.toggle("제목/본문 스타일 분리", value=initial_state.get("split_style", True))

    title_font_file = st.file_uploader("제목 폰트 업로드(선택)", type=["ttf", "otf", "ttc"])
    if title_font_file:
        st.session_state["title_font_file_obj"] = title_font_file

    # ✨ 새로 추가: 폰트 크기 모드
    font_size_mode = st.radio(
        "폰트 크기 모드",
        ["연동(기본×배수)", "개별 설정"],
        index=0 if initial_state.get("font_size_mode", "연동(기본×배수)") == "연동(기본×배수)" else 1,
        horizontal=True,
    )
    st.session_state.project["font_size_mode"] = font_size_mode

    if font_size_mode == "개별 설정":
        # 개별 사이즈 (± 버튼 잘 먹히도록 step=1)
        title_font_size = st.number_input(
            "제목 폰트 크기(pt)", 18, 200,
            value=int(initial_state.get("title_font_size", int(initial_state["base_font_size"] * initial_state.get("title_scale", 1.4)))),
            step=1
        )
        body_font_size = st.number_input(
            "본문 폰트 크기(pt)", 18, 200,
            value=int(initial_state.get("body_font_size", initial_state["base_font_size"])),
            step=1
        )
        st.session_state.project.update({
            "title_font_size": int(title_font_size),
            "body_font_size": int(body_font_size),
        })
        # 연동 배수는 숨김(내부 값은 유지)
        title_scale = float(initial_state.get("title_scale", 1.4))
        st.session_state.project["title_scale"] = title_scale
    else:
        # 연동 모드: 기존처럼 배수로 조절
        title_scale = st.slider("제목 크기 배수", 1.0, 2.5, value=float(initial_state.get("title_scale", 1.4)))
        st.session_state.project["title_scale"] = float(title_scale)

    title_color_hex = st.color_picker("제목 색", value=initial_state.get("title_color_hex", "#111111"))
    watermark = st.text_input("워터마크(선택)", value=initial_state["watermark"], placeholder="예: @brand")
    shadow = st.toggle("텍스트 그림자", value=initial_state["shadow"])
    shadow_opacity = st.slider("그림자 농도", 0, 255, value=initial_state["shadow_opacity"]) if shadow else initial_state["shadow_opacity"]

    st.session_state.project.update({
        "split_style": split_style,
        "title_color_hex": title_color_hex,
        "watermark": watermark,
        "shadow": shadow,
        "shadow_opacity": shadow_opacity,
    })

    # (선택) 라이브 미리보기
    live_apply = st.toggle("실시간 적용(변경 시 자동 렌더)", value=st.session_state.get("live_apply", False))
    st.session_state["live_apply"] = live_apply

    apply_now = st.button("🖋️ 텍스트 오버레이 적용")

if apply_now or st.session_state.get("live_apply", False):
    if not st.session_state.project["page_texts"]:
        st.warning("먼저 텍스트를 생성/편집하세요.")
    elif not st.session_state.project["base_images"]:
        st.warning("먼저 배경을 생성/적용하세요.")
    else:
        base_map = {"상단": 10, "중앙": 50, "하단": 90}
        base_v = base_map.get(st.session_state.project.get("v_preset", "중앙"), 50)
        final_v = max(0, min(100, base_v + int(st.session_state.project.get("v_offset", 0))))

        body_loader_func = make_font_loader(st.session_state.get("body_font_file_obj"))
        title_loader_func = make_font_loader(st.session_state.get("title_font_file_obj") or st.session_state.get("body_font_file_obj"))

        title_color = hex_to_rgb(st.session_state.project.get("title_color_hex", "#111111"))
        body_color = hex_to_rgb(st.session_state.project.get("body_color_hex", "#141414"))
        align = st.session_state.project["text_align"]
        h_anchor = st.session_state.project["h_anchor"]
        pad_pct = st.session_state.project["padding_pct"]

        # ✅ 폰트 크기 실제 적용 (연동/개별)
        if st.session_state.project.get("font_size_mode", "연동(기본×배수)") == "개별 설정":
            b_size = int(st.session_state.project.get("body_font_size", st.session_state.project["base_font_size"]))
            t_size = int(st.session_state.project.get("title_font_size", int(b_size * st.session_state.project.get("title_scale", 1.4))))
            eff_title_scale = max(0.1, t_size / max(1, b_size))
        else:
            b_size = int(st.session_state.project["base_font_size"])
            eff_title_scale = float(st.session_state.project.get("title_scale", 1.4))

        box_bg = st.session_state.project["box_bg"]
        box_color = hex_to_rgb(st.session_state.project.get("box_color_hex", "#FFFFFF"))
        box_opacity = int(st.session_state.project["box_opacity"])
        box_radius = int(st.session_state.project.get("box_radius", 18))
        box_inner_pad_pct = float(st.session_state.project.get("box_inner_pad_pct", 1.6))
        line_spacing_ratio = st.session_state.project.get("line_spacing", 1.25)

        ov_use = st.session_state.project.get("overlay_use", False)
        ov_imgs = st.session_state.project.get("overlay_images", [])
        ov_scale = int(st.session_state.project.get("overlay_scale_pct", 35))
        ov_x = int(st.session_state.project.get("overlay_x_pct", 80))
        ov_y = int(st.session_state.project.get("overlay_y_pct", 20))
        ov_opacity = int(st.session_state.project.get("overlay_opacity", 85))
        ov_shadow = st.session_state.project.get("overlay_shadow", True)
        ov_blur = int(st.session_state.project.get("overlay_shadow_blur", 12))
        ov_sopa = int(st.session_state.project.get("overlay_shadow_opacity", 120))
        ov_dx = int(st.session_state.project.get("overlay_shadow_dx", 6))
        ov_dy = int(st.session_state.project.get("overlay_shadow_dy", 6))
        ov_w2a = st.session_state.project.get("overlay_white_to_alpha", True)
        ov_thresh = int(st.session_state.project.get("overlay_white_thresh", 245))

        final_images = []
        with st.spinner("렌더링 중..."):
            for i, (bg, text) in enumerate(zip(st.session_state.project["base_images"], st.session_state.project["page_texts"])):                
                stage = bg.convert("RGBA")

                # 오버레이
                if ov_use and (ov_imgs or st.session_state.project.get("overlay_source") == "OpenAI(DALL·E 3)"):
                    ov = ov_imgs[i] if i < len(ov_imgs) else (ov_imgs[0] if ov_imgs else None)
                    if ov is not None:
                        if ov_w2a:
                            ov = remove_white_bg(ov, ov_thresh)
                        stage = place_overlay(stage, ov, ov_scale, ov_x, ov_y,
                                              opacity=ov_opacity, shadow=ov_shadow,
                                              blur=ov_blur, sh_opacity=ov_sopa, dx=ov_dx, dy=ov_dy)

                # 텍스트
                if st.session_state.project.get("split_style", True):
                    out = render_title_body_on_image(
                        img=stage, text=text,
                        title_loader=title_loader_func, body_loader=body_loader_func,
                        base_font_size=b_size,              # ← 본문 기준 크기
                        title_scale=float(eff_title_scale), # ← 제목은 배수로 환산 적용
                        title_color=title_color, body_color=body_color,
                        align=align, h_anchor=h_anchor, v_pos_pct=final_v,
                        padding_pct=pad_pct, shadow=st.session_state.project["shadow"],
                        shadow_opacity=st.session_state.project["shadow_opacity"],
                        box_bg=box_bg, box_opacity=box_opacity, box_color=box_color,
                        box_radius=box_radius, box_inner_pad_pct=box_inner_pad_pct,
                        watermark=st.session_state.project["watermark"],
                        line_spacing_ratio=line_spacing_ratio
                    )
                else:
                    out = render_text_on_image(
                        img=stage, text=text,
                        font_loader=body_loader_func,
                        base_font_size=b_size,              # ← 개별/연동 결과 반영
                        text_color=body_color, align=align, h_anchor=h_anchor, v_pos_pct=final_v,
                        padding_pct=pad_pct, shadow=st.session_state.project["shadow"],
                        shadow_opacity=st.session_state.project["shadow_opacity"],
                        box_bg=box_bg, box_opacity=box_opacity, box_color=box_color,
                        box_radius=box_radius, box_inner_pad_pct=box_inner_pad_pct,
                        auto_fit=st.session_state.project["auto_fit"],
                        watermark=st.session_state.project["watermark"],
                        line_spacing_ratio=line_spacing_ratio
                    )
                final_images.append(out)

        st.session_state.project["final_images"] = final_images
        st.success("오버레이 적용 완료")

# 결과 미리보기
if st.session_state.project["final_images"]:
    st.markdown("**최종 미리보기**")
    cols = st.columns(min(4, len(st.session_state.project["final_images"])) or 1)
    for i, im in enumerate(st.session_state.project["final_images"]):
        with cols[i % len(cols)]:
            st.image(im, caption=f"페이지 {i + 1}")

# ====== 4) 다운로드 ======
st.subheader("4) 다운로드")
if st.session_state.project["final_images"]:
    cdl1, cdl2, cdl3 = st.columns(3)
    with cdl1:
        zbytes = export_zip(st.session_state.project["final_images"])
        st.download_button("📦 PNG ZIP 다운로드", zbytes, file_name=f"card_news_{datetime.now().strftime('%Y%m%d_%H%M')}.zip")
    with cdl2:
        try:
            pbytes = export_pdf(st.session_state.project["final_images"])
            st.download_button("📄 PDF 다운로드", pbytes, file_name=f"card_news_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        except Exception:
            st.info("PDF 변환에 실패했습니다. ZIP으로 다운로드해 주세요.")
    with cdl3:
        idx = st.number_input("개별 저장 페이지", 1, len(st.session_state.project["final_images"]), value=1)
        st.download_button("🖼️ 선택 페이지 PNG 저장",
                           pil_to_png_bytes(st.session_state.project["final_images"][idx - 1]),
                           file_name=f"card_{idx:02d}.png")
else:
    st.info("최종 이미지가 없습니다. 텍스트 오버레이를 먼저 적용하세요.")