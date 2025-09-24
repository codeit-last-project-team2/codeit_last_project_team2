from backend.models.homepage_model import HomepageRequest, GithubUploadRequest

from openai import OpenAI

from github import Github

import os

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# github 설정
GITHUB_TOKEN = os.getenv("GITHUB_HOMEPAGE_TOKEN")
ORG_NAME = "codeit-last-project-team2"
REPO_NAME = "homepage"

def _extract_text(resp) -> str:
    # 최신 SDK면 편의속성 사용
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    # 폴백: 저수준 구조에서 직접 추출
    parts = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            if getattr(c, "type", "") == "output_text":
                parts.append(getattr(c, "text", "") or "")
    return "".join(parts)

def generate_html(req: HomepageRequest, temperature: float = 0.8) -> str:
    
    prompt = f"""
브랜드를 홍보하기 위한 페이지를 제작하려합니다. 다음의 조건을 참고하여 코드를 작성해주세요.
[조건]
1. 결과는 index.html로 저장할 수 있도록 완전한 HTML코드이어야 합니다. 코드 외의 내용은 반환하지 마세요.
2. HTML, CSS, JS가 한 문서에 포함되어야 합니다.
3. 업종에 따라서 강조해야할 포인트를 생각하고, 그에 따라서 구조를 작성해주세요.
    예) 
    요식업 - 메뉴 강조,
    서비스업 - 서비스 항목과 후기 강조, 
    쇼핑몰 - 상품 목록과 할인 배너 강조
5. 반응형(모바일/PC 모두 지원)으로 작성해주세요.
6. 버튼 클릭 시 JavaScript alert를 띄우는 기능을 추가해주세요.

다음 정보를 바탕으로 index.html을 작성해주세요
    - 상호명: {req.store_name},
    - 업종 대분류: {req.category_main},
    - 업종 소분류: {req.category_sub},
    - 메뉴: {req.menus},
    - 타켓층: {req.targets},
    - 주요 판매 포인트: {req.selling_points},
    - 광고 목적: {req.ad_purpose},
    - 분위기: {req.mood}
    - 위치: {req.location} 
    - 이벤트: {req.event}
    - 홈페이지 분위기: {req.tone}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        temperature=temperature,
        input=prompt,
    )

    html = _extract_text(response).strip()
    html = html.replace("```html", "").replace("```", "").strip()
    return html


def githubpage_upload(req: GithubUploadRequest):
    # --- GitHub 연결 ---
    g = Github(GITHUB_TOKEN)
    org = g.get_organization(ORG_NAME)
    repo = org.get_repo(REPO_NAME)

    path = f"users/{req.store_id}/index.html"
    message = f"Add homepage for {req.store_id}"

    # --- 파일 업로드 (있으면 update, 없으면 create) ---
    try:
        file = repo.get_contents(path, ref="main")
        repo.update_file(file.path, message, req.html, file.sha, branch="main")
    except:
        repo.create_file(path, message, req.html, branch="main")

    homepage_url = f"https://{ORG_NAME}.github.io/{REPO_NAME}/users/{req.store_id}/"

    return homepage_url