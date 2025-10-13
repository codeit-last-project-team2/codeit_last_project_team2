# utils/openai_utils.py
import base64, io, json, re, time, os
from typing import Any, Dict, List, Tuple, Optional

from openai import OpenAI, BadRequestError
try:
    from openai import APIConnectionError, RateLimitError, APIStatusError
except Exception:
    APIConnectionError = RateLimitError = APIStatusError = Exception

from dotenv import load_dotenv, find_dotenv
from PIL import Image

load_dotenv(find_dotenv())

# 필요 시 프로젝트 지정:
# client = OpenAI(project=os.getenv("OPENAI_PROJECT"))
client = OpenAI()


# -------------------- 공통 유틸 --------------------
def _retry(fn, *, retries: int = 3, base_delay: float = 0.6):
    for i in range(retries):
        try:
            return fn()
        except (APIConnectionError, RateLimitError):
            if i == retries - 1:
                raise
            time.sleep(base_delay * (2 ** i))
        except APIStatusError as e:
            status = getattr(e, "status_code", None) or getattr(e, "status", None)
            try:
                code = int(status) if status is not None else None
            except Exception:
                code = None
            if code and 500 <= code < 600:
                if i == retries - 1:
                    raise
                time.sleep(base_delay * (2 ** i))
            else:
                raise


def _extract_text(resp: Any) -> str:
    """Responses API 응답에서 텍스트를 최대한 끌어온다."""
    # 0) 최신 SDK 편의 필드
    raw = getattr(resp, "output_text", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()

    # 1) 객체를 dict로
    data: Dict[str, Any] = {}
    try:
        data = json.loads(resp.model_dump_json())
    except Exception:
        try:
            data = json.loads(resp.to_json())
        except Exception:
            data = {}

    # 2) 표준 경로들 먼저 시도
    chunks: List[str] = []
    for item in (data.get("output") or []):
        for c in (item.get("content") or []):
            if not isinstance(c, dict):
                continue
            t = c.get("text")
            if isinstance(t, dict) and isinstance(t.get("value"), str):
                chunks.append(t["value"])
            elif isinstance(t, str):
                chunks.append(t)
            elif isinstance(c.get("value"), str):
                chunks.append(c["value"])
    if chunks:
        return "\n".join(chunks).strip()

    for msg in (data.get("messages") or []):
        if msg.get("role") == "assistant":
            parts: List[str] = []
            for c in (msg.get("content") or []):
                if isinstance(c, dict) and c.get("type") in ("text", "output_text"):
                    t = c.get("text")
                    if isinstance(t, dict) and isinstance(t.get("value"), str):
                        parts.append(t["value"])
                    elif isinstance(t, str):
                        parts.append(t)
            if parts:
                return "\n".join(parts).strip()

    # 3) 재귀 탐색(안 보이는 위치의 value/text 문자열까지 긁어오기)
    def _dfs(v):
        out = []
        if isinstance(v, dict):
            for k, val in v.items():
                if k in ("value", "text", "output_text") and isinstance(val, str) and val.strip():
                    out.append(val)
                elif isinstance(val, dict) and isinstance(val.get("value"), str):
                    out.append(val["value"])
                out.extend(_dfs(val))
        elif isinstance(v, list):
            for x in v:
                out.extend(_dfs(x))
        return out

    deep = [s for s in _dfs(data) if isinstance(s, str) and s.strip()]
    if deep:
        return "\n".join(deep).strip()

    # 4) 정말 없으면 디버깅용으로 전체 JSON을 문자열로 반환(프론트 raw_output 확인용)
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return ""


def _img_to_png_bytes(image_bytes: bytes, *, max_side: int = 2048) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as im:
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > max_side:
            r = max_side / float(max(w, h))
            im = im.resize((int(w * r), int(h * r)))
        out = io.BytesIO()
        im.save(out, format="PNG", optimize=True)
        return out.getvalue()


def _responses_create_compat(**kwargs):
    """
    Responses.create 호출 시 모델/SDK가 temperature/top_p/response_format을
    지원하지 않으면 해당 파라미터를 제거하고 1회 재호출한다.
    - TypeError: SDK 레벨에서 인자를 아예 받을 수 없을 때(지금 케이스)
    - BadRequestError: 서버가 'Unsupported parameter'로 거절할 때
    """
    # 1) 먼저 한 번 시도
    try:
        return client.responses.create(**kwargs)

    # (A) SDK 함수 시그니처가 인자를 못 받을 때: TypeError
    except TypeError as e:
        msg = str(e)
        changed = False
        if "response_format" in msg:
            kwargs.pop("response_format", None); changed = True
        if "temperature" in msg:
            kwargs.pop("temperature", None); changed = True
        if "top_p" in msg:
            kwargs.pop("top_p", None); changed = True
        if changed:
            return client.responses.create(**kwargs)
        raise

    # (B) 서버가 인자를 거절할 때: 400 BadRequest
    except BadRequestError as e:
        msg = str(e)
        changed = False
        if ("Unsupported parameter: 'response_format'" in msg) or ("param': 'response_format'" in msg):
            kwargs.pop("response_format", None); changed = True
        if ("Unsupported parameter: 'temperature'" in msg) or ("param': 'temperature'" in msg):
            kwargs.pop("temperature", None); changed = True
        if ("Unsupported parameter: 'top_p'" in msg) or ("param': 'top_p'" in msg):
            kwargs.pop("top_p", None); changed = True
        if changed:
            return client.responses.create(**kwargs)
        raise



# -------------------- OpenAI 호출 --------------------
def call_openai_model(
    model: str,
    prompt: str,
    *,
    max_tokens: int = 300,
    temperature: Optional[float] = 0.8,
    top_p: Optional[float] = 1.0,
    force_json: bool = False,
) -> Tuple[str, Any]:
    def _do():
        req: Dict[str, Any] = {
            "model": model,
            "input": prompt,
            "max_output_tokens": max_tokens,
        }
        if temperature is not None:
            req["temperature"] = temperature
        if top_p is not None:
            req["top_p"] = top_p
        if force_json:
            req["response_format"] = {"type": "json_object"}
        resp = _responses_create_compat(**req)
        return _extract_text(resp), resp
    return _retry(_do)


def call_openai_with_image(
    model: str,
    text_prompt: str,
    image_bytes: bytes,
    *,
    max_tokens: int = 400,
    temperature: Optional[float] = 0.8,
    top_p: Optional[float] = 1.0,
    force_json: bool = False,
) -> Tuple[str, Any]:
    png_bytes = _img_to_png_bytes(image_bytes)
    img_b64 = base64.b64encode(png_bytes).decode("utf-8")
    input_content = [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": text_prompt},
                {"type": "input_image", "image_url": f"data:image/png;base64,{img_b64}"},
            ],
        }
    ]
    def _do():
        req: Dict[str, Any] = {
            "model": model,
            "input": input_content,
            "max_output_tokens": max_tokens,
        }
        if temperature is not None:
            req["temperature"] = temperature
        if top_p is not None:
            req["top_p"] = top_p
        if force_json:
            req["response_format"] = {"type": "json_object"}
        resp = _responses_create_compat(**req)
        return _extract_text(resp), resp
    return _retry(_do)


# -------------------- 출력 파싱 --------------------
def parse_copies(raw_output: str) -> List[str]:
    if not raw_output:
        return []

    s = raw_output.strip()

    # 1) ```json ... ``` 코드펜스 안 JSON 우선
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S | re.I)
    if m:
        candidate = m.group(1).strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict) and isinstance(data.get("copies"), list):
                arr = [str(x).strip() for x in data["copies"] if isinstance(x, (str, int, float))]
                arr = [x for x in arr if x]
                if arr:
                    return arr
        except Exception:
            pass

    # 2) 본문 안의 가장 바깥 JSON 블록 추출 시도
    if "{" in s and "}" in s:
        i, j = s.find("{"), s.rfind("}")
        if j > i:
            candidate = s[i:j+1]
            try:
                data = json.loads(candidate)
                if isinstance(data, dict) and isinstance(data.get("copies"), list):
                    arr = [str(x).strip() for x in data["copies"] if isinstance(x, (str, int, float))]
                    arr = [x for x in arr if x]
                    if arr:
                        return arr
            except Exception:
                pass

    # 3) 원래의 폴백 규칙
    parts = re.split(r"\n{2,}|\n+|•|–|-|\d+[.)]", s)
    copies = [p.strip(" -•\t\"'") for p in parts if p and p.strip()]
    copies = [c for c in copies if len(c) > 1 and not c.lower().startswith(("note:", "주의", "info:"))]
    return copies