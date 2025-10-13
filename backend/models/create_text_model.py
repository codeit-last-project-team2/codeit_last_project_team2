# 텍스트 입력(브랜드/상품/톤/길이/개수/모델)을 받아 OpenAI에 질의 → 모델 원문(raw_output)과 파싱된 문구 목록 반환. 재시도 로직 포함.

# backend/models/create_text_model.py
from utils.openai_utils import call_openai_model, parse_copies

def _max_tokens(length: str, model: str) -> int:
    """
    gpt-5 계열은 동일 길이라도 여유 있게 준다.
    JSON 오버헤드 + 한국어 기준 토큰 여유 반영.
    """
    is_gpt5 = model.startswith("gpt-5")
    if length == "long":
        return 1100 if is_gpt5 else 700
    else:
        return 600 if is_gpt5 else 300

def _make_prompt(product: str, tone: str, length: str, num_copies: int) -> str:
    # 길이 규칙을 문장/자수로 명시
    if length == "long":
        length_rule = "각 문구는 3~4문장, 최소 60자 이상으로 작성"
    else:
        length_rule = "각 문구는 1~2문장, 20~40자 내외로 간결하게 작성"

    # 멀티톤일 때 모두 반영하도록 명시
    tone_rule = (
        "아래 톤앤매너를 모두 반영하되, 과장하거나 상충되지 않게 자연스럽게 조합"
        if ("," in tone or "/" in tone or " " in tone and len(tone) > 8)
        else "아래 톤앤매너를 반영"
    )

    return (
        "당신은 전문 광고 카피라이터입니다.\n"
        "아래 **JSON 포맷만** 반환하세요. 코드블록/설명/불릿/번호 금지.\n"
        '출력 형식: {"copies": ["문구1","문구2", ...]}\n'
        f"- 상품명: {product}\n"
        f"- 톤앤매너: {tone}\n"
        f"- 길이: {'길게' if length == 'long' else '짧게'}\n"
        f"- 개수: 정확히 {num_copies}개\n"
    )

def generate_ad_copies(product: str, tone: str, length: str, num_copies: int, model: str):
    """
    Returns dict: { "raw_output": str, "copies": [str, ...] }
    """
    prompt = _make_prompt(product, tone, length, num_copies)

    # 1차 시도
    max_tok = _max_tokens(length, model)
    raw, _ = call_openai_model(
        model=model,
        prompt=prompt,
        max_tokens=max_tok,
        temperature=None,  # gpt-5 일부 모델은 미지원
        top_p=None,        # gpt-5 일부 모델은 미지원
        force_json=False,  # SDK가 response_format 미지원일 수 있어 프롬프트로만 강제
    )
    copies = parse_copies(raw)

    # incomplete 디텍트: 응답 JSON 안에 max_output_tokens 사유가 보이면 토큰 증가 후 재시도
    need_retry_for_incomplete = isinstance(raw, str) and ("incomplete_details" in raw and "max_output_tokens" in raw)

    if need_retry_for_incomplete or len(copies) < num_copies:
        prompt2 = _make_prompt(product, tone, length, num_copies) + "\n중요: JSON만 반환하세요."
        max_tok2 = int(max_tok * 1.8)  # 토큰 여유 크게
        raw2, _ = call_openai_model(
            model=model,
            prompt=prompt2,
            max_tokens=max_tok2,
            temperature=None,
            top_p=None,
            force_json=False,
        )
        copies2 = parse_copies(raw2)

        # 더 나아진 결과로 교체
        if need_retry_for_incomplete or len(copies2) >= len(copies):
            raw, copies = raw2, copies2

    # 개수 초과 시 자르기
    if len(copies) > num_copies:
        copies = copies[:num_copies]

    return {"raw_output": raw, "copies": copies}