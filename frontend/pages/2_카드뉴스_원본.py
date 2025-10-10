import streamlit as st
import requests, io, base64, zipfile
from datetime import datetime
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from backend.services.cardnews_service import hex_to_rgb
import numpy as np

BACKEND_URL = "http://127.0.0.1:8000"

# -----------------------------
# 로그인 확인
# -----------------------------
if not st.session_state.get("token"):
    st.warning("⚠️ 로그인이 필요합니다. 홈에서 로그인하세요.")
    st.stop()
headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.set_page_config(page_title="Card News Studio", layout="wide")
st.title("🗂️ 카드 뉴스 스튜디오")

# -----------------------------
# 세션 상태 초기화
# -----------------------------
if "project" not in st.session_state:
    st.session_state.project = {
        "num_pages": 3, "topic": "", "purpose": "정보 공유",
        "must_include": "", "audience": "일반 대중", "tone": "친근하고 명확한", "lang": "ko",
        "page_texts": [], "base_images": [], "overlay_images": [], "final_images": [],
        # 오버레이 설정
        "overlay_scale": 50, "overlay_x": 50, "overlay_y": 50,
        "overlay_opacity": 100, "overlay_shadow": True, "overlay_white2alpha": True,
    }
proj = st.session_state.project

# -----------------------------
# 1. 기본 설정
# -----------------------------
st.header("📌 기본 설정")
proj["num_pages"] = st.slider("카드 장수", 3, 7, value=proj["num_pages"])
proj["topic"] = st.text_input("주제", proj["topic"])
proj["purpose"] = st.selectbox("용도", ["정보 공유","행사","광고","공지","채용"],
                              index=["정보 공유","행사","광고","공지","채용"].index(proj["purpose"]))
proj["must_include"] = st.text_area("필수 포함 내용", proj["must_include"])
proj["audience"] = st.text_input("대상", proj["audience"])
proj["tone"] = st.text_input("톤&매너", proj["tone"])
proj["lang"] = st.radio("언어", ["ko","en"], index=0 if proj["lang"]=="ko" else 1, horizontal=True)

st.markdown("---")

# -----------------------------
# 2. 텍스트 생성
# -----------------------------
st.header("✍️ 텍스트 생성 & 편집")
if st.button("텍스트 자동 생성"):
    with st.spinner("텍스트 생성 중..."):
        req = {
            "num_pages": proj["num_pages"],
            "topic": proj["topic"],
            "purpose": proj["purpose"],
            "must": proj["must_include"],
            "audience": proj["audience"],
            "tone": proj["tone"],
            "lang": proj["lang"],
        }
        res = requests.post(f"{BACKEND_URL}/cardnews/generate/text", json=req, headers=headers)
        if res.status_code == 200:
            proj["page_texts"] = res.json()
            st.success("텍스트 생성 완료 ✅")
        else:
            st.error(f"생성 실패: {res.text}")

if proj["page_texts"]:
    proj["page_texts"] = [
        st.text_area(f"페이지 {i+1}", value=proj["page_texts"][i], height=120, key=f"text_{i}")
        for i in range(proj["num_pages"])
    ]

st.markdown("---")

# -----------------------------
# 3. 배경 생성
# -----------------------------
st.header("🎨 배경 생성")
bg_method = st.radio("배경 방식", ["단색","그라디언트"], index=1)
if bg_method == "단색":
    color = st.color_picker("배경 색상", "#F5F6FA")
    proj["base_images"] = [Image.new("RGB",(1080,1080),hex_to_rgb(color)) for _ in range(proj["num_pages"])]
elif bg_method == "그라디언트":
    c1 = st.color_picker("시작 색","#F5F6FA"); c2 = st.color_picker("끝 색","#DAE0EE")
    start, end = hex_to_rgb(c1), hex_to_rgb(c2)
    base_images = []
    for _ in range(proj["num_pages"]):
        grad = Image.new("RGB",(1080,1080),start)
        for y in range(1080):
            ratio = y/1080
            r = int(start[0]*(1-ratio)+end[0]*ratio)
            g = int(start[1]*(1-ratio)+end[1]*ratio)
            b = int(start[2]*(1-ratio)+end[2]*ratio)
            for x in range(1080):
                grad.putpixel((x,y),(r,g,b))
        base_images.append(grad)
    proj["base_images"] = base_images

if proj["base_images"]: st.success("배경 생성 완료 ✅")

st.markdown("---")

# -----------------------------
# 4. 오버레이
# -----------------------------
st.header("🖼️ 오버레이")
use_overlay = st.checkbox("오버레이 사용")
if use_overlay:
    src = st.radio("오버레이 소스", ["업로드","DALL·E3"])
    if src == "업로드":
        files = st.file_uploader("이미지 업로드", type=["png","jpg"], accept_multiple_files=True)
        if files:
            proj["overlay_images"] = [Image.open(f).convert("RGBA") for f in files]
    else:
        if st.button("OpenAI로 오버레이 생성"):
            imgs=[]
            for t in proj["page_texts"]:
                p=t.split("\n")[0]
                res=requests.post(f"{BACKEND_URL}/cardnews/generate/b64img",
                                  params={"prompt":f"{proj['topic']} {p}"}, headers=headers)
                if res.status_code==200:
                    img=Image.open(io.BytesIO(base64.b64decode(res.json()))).convert("RGBA")
                    imgs.append(img)
            proj["overlay_images"]=imgs
            st.success("오버레이 생성 완료 ✅")

    # 오버레이 조정 옵션
    proj["overlay_scale"] = st.slider("크기 비율 (%)", 10, 100, proj["overlay_scale"])
    proj["overlay_x"] = st.slider("가로 위치 (%)", 0, 100, proj["overlay_x"])
    proj["overlay_y"] = st.slider("세로 위치 (%)", 0, 100, proj["overlay_y"])
    proj["overlay_opacity"] = st.slider("투명도 (%)", 0, 100, proj["overlay_opacity"])
    proj["overlay_shadow"] = st.checkbox("드롭 섀도우", proj["overlay_shadow"])
    proj["overlay_white2alpha"] = st.checkbox("흰 배경 투명화", proj["overlay_white2alpha"])

st.markdown("---")

# -----------------------------
# 5. 최종 합성
# -----------------------------
st.header("🖋️ 텍스트+오버레이 합성")
finals=[]
if proj["base_images"] and proj["page_texts"]:
    for i,bg in enumerate(proj["base_images"]):
        im = bg.convert("RGBA")
        d = ImageDraw.Draw(im)

        # 텍스트 중앙 정렬
        txt = proj["page_texts"][i]
        font = ImageFont.load_default()
        w,h = d.textsize(txt, font=font)
        d.text(((im.width-w)//2, (im.height-h)//2), txt, font=font, fill=(20,20,20))

        # 오버레이 합성
        if proj.get("overlay_images") and i<len(proj["overlay_images"]):
            ov = proj["overlay_images"][i].copy()

            # 흰 배경 투명화
            if proj["overlay_white2alpha"]:
                arr = np.array(ov)
                r,g,b,a = arr.T
                white = (r>240)&(g>240)&(b>240)
                arr[...,3][white]=0
                ov = Image.fromarray(arr)

            # 크기 조정
            scale = proj["overlay_scale"]/100.0
            new_w = int(ov.width*scale)
            new_h = int(ov.height*scale)
            ov = ov.resize((new_w,new_h), Image.LANCZOS)

            # 투명도 적용
            if proj["overlay_opacity"]<100:
                alpha = ov.split()[3].point(lambda p: p*proj["overlay_opacity"]/100)
                ov.putalpha(alpha)

            # 위치
            x = int(im.width*proj["overlay_x"]/100) - new_w//2
            y = int(im.height*proj["overlay_y"]/100) - new_h//2

            # 그림자
            if proj["overlay_shadow"]:
                shadow_layer = Image.new("RGBA", im.size, (0,0,0,0))
                sh = ov.copy().convert("L").point(lambda p: p>0 and 120)
                blur = sh.filter(ImageFilter.GaussianBlur(5))
                shadow_layer.paste((0,0,0,120),(x+5,y+5),blur)
                im = Image.alpha_composite(im, shadow_layer)

            im.paste(ov,(x,y),ov)

        finals.append(im)
    proj["final_images"]=finals
    st.success("최종 합성 완료 ✅")

if proj["final_images"]:
    for i,img in enumerate(proj["final_images"]):
        st.image(img, caption=f"페이지 {i+1}")

st.markdown("---")

# -----------------------------
# 6. 다운로드
# -----------------------------
st.header("⬇️ 다운로드")
if proj["final_images"]:
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w") as zf:
        for i,img in enumerate(proj["final_images"]):
            b=io.BytesIO(); img.save(b,"PNG")
            zf.writestr(f"page_{i+1}.png",b.getvalue())
    buf.seek(0)
    st.download_button("ZIP 다운로드",buf,file_name="cardnews.zip")
