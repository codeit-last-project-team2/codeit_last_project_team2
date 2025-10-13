from openai import OpenAI
from github import Github
from pathlib import Path
import os, json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GITHUB_TOKEN = os.getenv("GITHUB_HOMEPAGE_TOKEN")
ORG_NAME = "codeit-last-project-team2"
REPO_NAME = "homepage"

def _extract_text(resp) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    parts = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            if getattr(c, "type", "") == "output_text":
                parts.append(getattr(c, "text", "") or "")
    return "".join(parts)

def generate_html(input_json):
    system_prompt = f"""
    당신은 단일 파일 웹페이지 생성기다. 입력 JSON을 바탕으로
    - 한 개의 .html 파일(내장 CSS/JS 포함, 외부 의존성 없음)을 생성한다.
    - 접근성(A11y), 반응형, 시맨틱 마크업
    - 전화/주문/결제/다운로드/양식 제출/전화번호 자동링크 등 **상호작용 금지**
    - 내비게이션은 동일 문서 내 앵커 스크롤만 허용
    - 이미지/아이콘은 data URI(SVG)만 사용
    - 다크 모드 토글 포함(로컬스토리지 저장)
    - Lighthouse 기준: 성능/접근성/베스트프랙티스/SEO 90+ 목표
    - 한국어 문구 기본
    - 코드 주석 최소화(핵심 블록만), 인라인 <style>, <script> 사용
    - 외부 폰트/라이브러리/애널리틱스 금지

    [출력 형식(엄격)]
    - 출력은 **오직 유효한 HTML 원문**이어야 하며, 다음을 절대 사용하지 말 것:
    1) Markdown 코드블록(예: ```html … ```), 2) JSON, 3) 큰따옴표로 감싼 문자열, 4) Base64, 5) 주석으로 전체 감싸기.
    - 문서는 반드시 **<!doctype html>로 시작**하여 **</html>로 종료**해야 한다. 앞뒤에 공백/문자/따옴표 금지.

    [요구사항]
    1) 상호작용 금지: 전화연결, 주문/결제, 예약, 제출/업로드, 파일 다운로드, 외부 링크 금지.
    2) 내장 기능만: 카테고리 필터, FAQ 토글, 검색(클라이언트 필터) 등 표시 전용.
    3) 색/타입스케일/간격 토큰 사용: --brand, --brand-2, --accent, --line, --radius, --shadow.
    4) 반응형: 1120px 컨테이너, 960/560 브레이크포인트.
    5) 접근성: aria-label/role/summary, 키보드 포커스 스타일, prefers-reduced-motion 고려.
    6) SEO: <title>, meta description, og:title/description/type, h1은 1개.
    7) 성능: 이미지 lazy, CSS/JS 최소화, 중복 스타일 제거.

    [출력 규칙]
    - 입력 JSON의 site.type에 따라 섹션 구성 분기:
    - "info": 공지/가이드/자료/FAQ
    - "brand": 스토리/가치/타임라인/팀/FAQ
    - "event": 히어로+카운트다운(표시 전용)/하이라이트/일정/혜택/FAQ
    - "portfolio": 필터+그리드/케이스스터디/프로세스/후기/FAQ/팀
    - site.blocks가 주어지면 위 기본 구성을 **우선 재배치**한다.
    - 모든 링크 href="#"는 aria-disabled 처리, 외부 이동 금지.
    - 전화/이메일 자동 탐지 방지: <meta name="format-detection" content="telephone=no,email=no,address=no">
    - 다크모드 토글 버튼 제공(🌓), 로컬스토리지 key="theme".

    [검증 체크리스트(코드 생성 직후 자체 점검)]
    - [ ] 외부 리소스 0개
    - [ ] 전화/주문/다운로드/폼 없음
    - [ ] <h1> 1개 / 섹션에 id 부여 / 헤더 내 내비게이션 앵커
    - [ ] data URI 이미지만 사용
    - [ ] 560px 이하/960px 이하 레이아웃 정상
    - [ ] 색 대비(본문 대비비 4.5:1 근사) 확인
    """
    json_str = json.dumps(input_json, ensure_ascii=False, indent=2)

    response = client.responses.create(
        model="gpt-5",
        input=json_str,
        instructions=system_prompt,
    )

    html = _extract_text(response).strip()
    html = html.replace("```html", "").replace("```", "").strip()
    return html

def githubpage_upload(html, email):
    g = Github(GITHUB_TOKEN)
    org = g.get_organization(ORG_NAME)
    repo = org.get_repo(REPO_NAME)

    path = f"users/{email}/index.html"
    message = f"Add homepage for {email}"

    if html.startswith('"') and html.endswith('"'):
        html = html[1:-1]
        html = html.replace('\\"', '"').replace("\\n", "\n")

    try:
        file = repo.get_contents(path, ref="main")
        repo.update_file(file.path, message, html, file.sha, branch="main")
    except:
        repo.create_file(path, message, html, branch="main")

    return f"https://{ORG_NAME}.github.io/{REPO_NAME}/users/{email}/"
