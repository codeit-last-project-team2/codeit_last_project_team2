from backend.models.homepage_model import GithubUploadRequest
from backend.models.homepage_model import HomepageRequest

from openai import OpenAI

from github import Github

from pathlib import Path

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

def get_sample_html(sample_id):
    if sample_id == '1':
        sample_html_text = Path("Data\sample_page\sample1.html").read_text(encoding="utf-8")

    return sample_html_text


def generate_html(req: HomepageRequest, temperature: float = 0.8) -> str:
    sample_html_text = get_sample_html(req.sample_id)
    system_prompt = f"""
브랜드를 홍보하기 위한 페이지를 제작하려합니다. 다음의 조건을 엄수하고, 브랜드 정보와 참고 HTML 템플릿을 바탕으로 브랜딩 페이지를 한 파일로 완성하세요.

[조건]
1. 결과는 index.html로 저장할 수 있도록 완전한 HTML코드이어야 합니다. 코드 외의 내용은 반환하지 마세요.
2. HTML, CSS, JS가 한 문서에 포함되어야 합니다.
3. 업종에 따라서 강조해야할 포인트를 생각하고, 그에 따라서 구조를 작성해주세요.
    예) 
    요식업 - 메뉴 강조,
    서비스업 - 서비스 항목과 후기 강조, 
    쇼핑몰 - 상품 목록과 할인 배너 강조
4. 과장/허위의 텍스트를 금지하며, [정보]의 내용 범위를 넘는 정보 생성 금지.
"""
    input_prompt = f"""
[참고 템플릿]
{sample_html_text}

[정보]
    - 상호명: {req.store_name}
    - e-mail: {req.email}
    - 업종 대분류: {req.category_main}
    - 업종 소분류: {req.category_sub}
    - 메뉴: {req.menus}
    - 타켓층: {req.targets}
    - 주요 판매 포인트: {req.selling_points}
    - 광고 목적: {req.ad_purpose}
    - 분위기: {req.mood}
    - 위치: {req.address} 
    - 이벤트: {req.event}
    - 홈페이지 분위기: {req.tone}
"""

    response = client.responses.create(
        model="gpt-4.1",
        temperature=temperature,
        input=input_prompt,
        instructions=system_prompt
    )

    html = _extract_text(response).strip()
    html = html.replace("```html", "").replace("```", "").strip()
    return html


def githubpage_upload(req: GithubUploadRequest):
    # --- GitHub 연결 ---
    g = Github(GITHUB_TOKEN)
    org = g.get_organization(ORG_NAME)
    repo = org.get_repo(REPO_NAME)

    path = f"users/{req.email}/{req.store_name}/index.html"
    message = f"Add homepage for {req.email}/{req.store_name}"

    # --- 파일 업로드 (있으면 update, 없으면 create) ---
    try:
        file = repo.get_contents(path, ref="main")
        repo.update_file(file.path, message, req.html, file.sha, branch="main")
    except:
        repo.create_file(path, message, req.html, branch="main")

    homepage_url = f"https://{ORG_NAME}.github.io/{REPO_NAME}/users/{req.email}/{req.store_name}/"

    return homepage_url