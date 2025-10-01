from backend.models.mascot_model import MascotRequest, MascotHistoryItem
from openai import OpenAI
import os, sqlite3

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# DB 파일 경로
DB_PATH = os.path.join("data", "user_info", "database.db")
os.makedirs("data", exist_ok=True)

# ---------- DB 초기화 ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mascot_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        store_name TEXT NOT NULL,
        keyword TEXT,
        mascot_personality TEXT,
        path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# ---------- 이미지 후보 생성 ----------
def generate_mascot_url_candidates(req: MascotRequest, num:int=3):
    prompt = f"""
    브랜드 홍보를 위한 마스코트를 제작할 것입니다.
    아래의 [조건]과 [참고]를 활용하여 마스코트 생성해주세요.

    [조건]
    1. 배경은 반드시 흰색입니다.
    2. 로고, 그림자, 배경을 포함하지 않습니다.
    3. 단 하나의 캐릭터를 생성합니다.

    [출력 형태 가이드]
    - "2d": 애니메이션이나 만화 같은 평면적인 느낌
    - "3d": 입체적인 질감과 깊이를 가진 스타일
    - "픽셀": 레트로 게임 느낌
    - "카툰": 과장된 표정과 색감을 가진 만화풍
    - "실사 일러스트": 반실사 느낌
    - "미니멀": 단순한 도형과 색감 위주
    - "심볼/아이콘": 간결하고 상징적
    - "수채화풍": 붓질과 번짐 효과
    - "사이버/메카닉": 금속/네온 미래풍

    [참고]
    - 대표 색상: {req.main_color}
    - 키워드: {req.keyword}
    - 캐릭터의 성격: {req.mascot_personality}
    - 브랜드 분위기: {req.mood}
    - 출력 형태: {req.output_style}
    - 추가 요구 사항: {req.additional_requirements}
    """

    urls = []
    for _ in range(num):
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        urls.append(result.data[0].url)
    return urls

# ---------- 히스토리 저장 ----------
def save_mascot_history(item: MascotHistoryItem):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO mascot_history (user_email, store_name, keyword, mascot_personality, path)
        VALUES (?, ?, ?, ?, ?)
    """, (item.user_email, item.store_name, item.keyword, item.mascot_personality, item.path))
    conn.commit()
    conn.close()

# ---------- 히스토리 조회 ----------
def get_mascot_history(user_email: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT store_name, keyword, mascot_personality, path, created_at
        FROM mascot_history
        WHERE user_email=?
        ORDER BY created_at DESC
    """, (user_email,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "store_name": r[0],
            "keyword": r[1],
            "mascot_personality": r[2],
            "path": r[3],
            "created_at": r[4]
        }
        for r in rows
    ]
