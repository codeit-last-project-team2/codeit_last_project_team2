# 업로드된 이미지(바이트) + 옵션을 받아 OpenAI Vision/Responses API에 질의 → raw_output + 파싱된 문구 반환. 
# 이미지 전송 방식은 사용 중인 OpenAI SDK 버전에 따라 약간 조정 필요 (아래 구현은 표준적 형태 예시).

# backend/models/image_text_model.py
# 업로드된 이미지(바이트) + 옵션을 받아 OpenAI Vision/Responses API에 질의 → raw_output + 파싱된 문구 반환.

from utils.openai_utils import call_openai_with_image, parse_copies

def _max_tokens(length: str, model: str) -> int:
    is_gpt5 = model.startswith("gpt-5")
    if length == "long":
        return 1300 if is_gpt5 else 900
    elif length == "medium":
        return 900 if is_gpt5 else 600
    else:
        return 600 if is_gpt5 else 350

def _make_prompt(tone: str, length: str, num_copies: int) -> str:
    if length == "long":
        length_rule = "각 문구는 4~5문장, 최소 80자 이상으로 작성"
        length_ko   = "길게"
    elif length == "medium":
        length_rule = "각 문구는 2~3문장, 최소 50자 이상으로 작성"
        length_ko   = "중간"
    else:
        length_rule = "각 문구는 1~2문장, 20~40자 내외로 간결하게 작성"
        length_ko   = "짧게"

    tone_rule = (
        "아래 톤앤매너를 모두 반영하되, 과장하거나 상충되지 않게 자연스럽게 조합"
        if ("," in tone or "/" in tone or (" " in tone and len(tone) > 8))
        else "아래 톤앤매너를 반영"
    )

    return (
        "당신은 전문 광고 카피라이터입니다.\n"
        "아래 이미지의 내용을 분석해 어울리는 광고 문구를 생성하세요.\n"
        "※ 반드시 **아래 JSON 포맷만** 반환하세요. 코드블록/불릿/설명/번호 금지.\n"
        '출력 형식: {"copies": ["문구1","문구2", ...]}\n'
        f"- 톤앤매너: {tone}\n"
        f"- 길이: {length_ko}\n"
        f"- 개수: 정확히 {num_copies}개\n"
        f"- 길이 규칙: {length_rule}\n"
        "- 각 문구는 한 줄, 큰따옴표 안에만 작성\n"
    )


def generate_ad_from_image(image_bytes: bytes, tone: str, length: str, num_copies: int, model: str):
    prompt = _make_prompt(tone, length, num_copies)

    max_tok = _max_tokens(length, model)
    raw, _ = call_openai_with_image(
        model=model,
        text_prompt=prompt,
        image_bytes=image_bytes,
        max_tokens=max_tok,
        temperature=None,
        top_p=None,
        force_json=False,
    )
    copies = parse_copies(raw)

    need_retry_for_incomplete = isinstance(raw, str) and ("incomplete_details" in raw and "max_output_tokens" in raw)
    if need_retry_for_incomplete or len(copies) < num_copies:
        prompt2 = prompt + "\n중요: 반드시 JSON만 반환하세요."
        max_tok2 = int(max_tok * 1.6)
        raw2, _ = call_openai_with_image(
            model=model,
            text_prompt=prompt2,
            image_bytes=image_bytes,
            max_tokens=max_tok2,
            temperature=None,
            top_p=None,
            force_json=False,
        )
        copies2 = parse_copies(raw2)
        if need_retry_for_incomplete or len(copies2) >= len(copies):
            raw, copies = raw2, copies2

    if len(copies) > num_copies:
        copies = copies[:num_copies]

    return {"raw_output": raw, "copies": copies}