from backend.models.homepage_model import HomepageRequest, GithubUploadRequest
from openai import OpenAI
from github import Github
from pathlib import Path
import os

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

def get_sample_html(sample_id):
    return Path(f"data/sample_page/sample{sample_id}.html").read_text(encoding="utf-8")

def generate_html(req: HomepageRequest, temperature: float = 0.8):
    sample_html_text = get_sample_html(req.sample_id or '1')
    menu_text = "\n".join([f"- {m['name']} ({m['price']}): {m.get('feature', '')}" for m in req.menus])

    system_prompt = """
    당신은 웹디자이너 겸 카피라이터입니다.
    아래 매장 정보를 바탕으로 브랜드 홈페이지를 한 파일로 완성하세요.
    결과는 완전한 HTML로만 반환해야 합니다.
    """

    input_prompt = f"""
    [매장 정보]
    - 상호명: {req.store_name}
    - 업종: {req.category_main or req.category_sub or req.category}
    - 위치: {req.address}
    - 연락처: {req.phone}
    - 이메일: {req.email}

    [홈페이지 정보]
    - 목적: {req.ad_purpose or req.purpose or '가게 홍보'}
    - 톤앤매너: {req.tone or req.style or '따뜻하고 친근한'}
    - 메뉴:
    {menu_text}
    - 분위기: {req.mood or '기본'}
    - 참고 템플릿:
    {sample_html_text}
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        temperature=temperature,
        input=input_prompt,
        instructions=system_prompt,
    )

    html = _extract_text(response).strip()
    html = html.replace("```html", "").replace("```", "").strip()
    return html

def githubpage_upload(req: GithubUploadRequest):
    g = Github(GITHUB_TOKEN)
    org = g.get_organization(ORG_NAME)
    repo = org.get_repo(REPO_NAME)

    path = f"users/{req.email}/{req.store_name}/index.html"
    message = f"Add homepage for {req.email}/{req.store_name}"

    try:
        file = repo.get_contents(path, ref="main")
        repo.update_file(file.path, message, req.html, file.sha, branch="main")
    except:
        repo.create_file(path, message, req.html, branch="main")

    return f"https://{ORG_NAME}.github.io/{REPO_NAME}/users/{req.email}/{req.store_name}/"
