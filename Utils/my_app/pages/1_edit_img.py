import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps
import io

st.title("이미지 후처리 확장판")

# 1. 이미지 업로드
if 'uploaded_img' not in st.session_state:
    st.session_state.uploaded_img = None

uploaded_file = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.session_state.uploaded_img = Image.open(uploaded_file).convert("RGB")

# 세션에 저장된 이미지 사용
if st.session_state.uploaded_img is not None:
    img = st.session_state.uploaded_img
    st.image(img, caption="업로드 이미지", use_container_width=True)

    width, height = img.size

    # 2. 후처리 옵션
    st.subheader("후처리 옵션")

    # 텍스트 추가 옵션
    add_text = st.checkbox("이미지에 텍스트 추가")
    if add_text:
        text_input = st.text_input("텍스트 입력")
        font_size = st.slider("폰트 크기", 20, 150, 60)
        text_color = st.color_picker("텍스트 색상", "#ffffff")
        text_x = st.slider("텍스트 X 위치", 0, width, 50)
        text_y = st.slider("텍스트 Y 위치", 0, height, 50)
    else:
        text_input, font_size, text_color, text_x, text_y = "", 60, "#ffffff", 50, 50

    # 밝기/대비/채도/선명도
    adjust_brightness = st.checkbox("밝기 조절")
    brightness_factor = st.slider("밝기 값", 0.1, 2.0, 1.0)

    adjust_contrast = st.checkbox("대비 조절")
    contrast_factor = st.slider("대비 값", 0.5, 2.0, 1.0)

    adjust_color = st.checkbox("채도 조절")
    color_factor = st.slider("채도 값", 0.0, 2.0, 1.0)

    adjust_sharpness = st.checkbox("선명도 조절")
    sharpness_factor = st.slider("선명도 값", 0.5, 3.0, 1.0)

    # 흑백 변환
    apply_grayscale = st.checkbox("흑백 변환")

    # 투명도 조절
    adjust_alpha = st.checkbox("투명도 조절")
    alpha_value = st.slider("투명도 (0=투명, 255=불투명)", 0, 255, 255)

    # 블러
    apply_blur = st.checkbox("블러 적용")
    blur_radius = st.slider("블러 강도", 0, 10, 0)

    # 필터 효과
    st.subheader("필터 효과")
    apply_emboss = st.checkbox("엠보스(Emboss)")
    apply_edges = st.checkbox("윤곽선(Find Edges)")
    apply_contour = st.checkbox("컨투어(Contour)")
    apply_invert = st.checkbox("색상 반전(Invert)")
    apply_sepia = st.checkbox("세피아 효과")

    # 기하학적 변형
    st.subheader("기하학적 변형")
    rotate_angle = st.slider("회전 각도", 0, 360, 0)
    flip_horizontal = st.checkbox("좌우 반전")
    flip_vertical = st.checkbox("상하 반전")

    # 리사이즈
    st.subheader("리사이즈")
    resize_width = st.number_input("새 가로 크기", min_value=1, value=width)
    resize_height = st.number_input("새 세로 크기", min_value=1, value=height)

    # 후처리 실행 버튼
    if st.button("후처리 적용"):
        processed_img = img.copy()

        # 텍스트 추가
        if add_text and text_input:
            draw = ImageDraw.Draw(processed_img)
            try:
                font = ImageFont.truetype("font/NanumGothic.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()
            draw.text((text_x, text_y), text_input, fill=text_color, font=font)

        # 밝기, 대비, 채도, 선명도
        if adjust_brightness:
            processed_img = ImageEnhance.Brightness(processed_img).enhance(brightness_factor)
        if adjust_contrast:
            processed_img = ImageEnhance.Contrast(processed_img).enhance(contrast_factor)
        if adjust_color:
            processed_img = ImageEnhance.Color(processed_img).enhance(color_factor)
        if adjust_sharpness:
            processed_img = ImageEnhance.Sharpness(processed_img).enhance(sharpness_factor)

        # 흑백 변환
        if apply_grayscale:
            processed_img = processed_img.convert("L").convert("RGB")

        # 투명도
        if adjust_alpha:
            processed_img.putalpha(alpha_value)

        # 블러
        if apply_blur and blur_radius > 0:
            processed_img = processed_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        # 필터 효과
        if apply_emboss:
            processed_img = processed_img.filter(ImageFilter.EMBOSS)
        if apply_edges:
            processed_img = processed_img.filter(ImageFilter.FIND_EDGES)
        if apply_contour:
            processed_img = processed_img.filter(ImageFilter.CONTOUR)
        if apply_invert:
            processed_img = ImageOps.invert(processed_img)
        if apply_sepia:
            sepia_img = processed_img.convert("RGB")
            pixels = sepia_img.load()
            for y in range(sepia_img.height):
                for x in range(sepia_img.width):
                    r, g, b = pixels[x, y]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    pixels[x, y] = (min(255, tr), min(255, tg), min(255, tb))
            processed_img = sepia_img

        # 기하학적 변형
        if rotate_angle != 0:
            processed_img = processed_img.rotate(rotate_angle, expand=True)
        if flip_horizontal:
            processed_img = ImageOps.mirror(processed_img)
        if flip_vertical:
            processed_img = ImageOps.flip(processed_img)

        # 리사이즈
        if resize_width != width or resize_height != height:
            processed_img = processed_img.resize((resize_width, resize_height))

        # 결과 출력
        st.image(processed_img, caption="후처리 결과", use_container_width=True)

        # 다운로드
        buf = io.BytesIO()
        processed_img.save(buf, format="PNG")
        st.download_button("이미지 다운로드", buf, file_name="processed.png", mime="image/png")
