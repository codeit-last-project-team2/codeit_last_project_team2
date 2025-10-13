from backend.models.mascot_model import MascotRequest, MascotHistoryItem
from openai import OpenAI
import os, sqlite3

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_PATH = os.path.join("data", "user_info", "database.db")
os.makedirs("data", exist_ok=True)

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

def generate_mascot_url_candidates(req: MascotRequest, num:int=3):
    prompt = f"""
    브랜드 마스코트를 제작합니다.
    아래 정보를 참고하여 브랜드 이미지에 어울리는 캐릭터를 설계해주세요.

    [매장 정보]
    - 매장명: {req.store_name}
    - 업종: {req.category or '업종 미정'}

    [디자인 요구사항]
    - 대표 색상: {req.main_color}
    - 키워드: {req.keyword}
    - 캐릭터 성격: {req.mascot_personality}
    - 출력 스타일: {req.output_style}
    - 추가 요구사항: {req.additional_requirements or '없음'}

    조건:
    - 배경은 반드시 흰색
    - 로고나 글씨 포함 금지
    - 단일 캐릭터만 생성
    """

    urls = []
    for _ in range(num):
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        urls.append(result.data[0].url)
    return urls

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
            "created_at": r[4],
        }
        for r in rows
    ]
