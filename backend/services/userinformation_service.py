from backend.models.user_information_model import UserInformation, StoreInfoRequest
import os, sqlite3, json, shutil

DATA_DIR = os.path.join("Data", "user_info")
DB_PATH = os.path.join(DATA_DIR, "database.db")

def _make_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(""" 
    CREATE TABLE IF NOT EXISTS user_information ( 
        email TEXT NOT NULL, 
        store_name TEXT NOT NULL, 
        category_main TEXT NOT NULL, 
        category_sub TEXT NOT NULL, 
        call_number TEXT NOT NULL, 
        address TEXT NOT NULL, 
        menus TEXT NOT NULL, 
        targets TEXT, 
        selling_points TEXT, 
        ad_purpose TEXT, 
        mood TEXT, 
        event TEXT, 
        tone TEXT, 
        PRIMARY KEY (email, store_name) 
    ) 
    """)
    conn.commit()
    conn.close()
        

def upload_store(user_info: UserInformation, email):
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO user_information (
        email, store_name, category_main, category_sub, call_number, address,
        menus, targets, selling_points, ad_purpose, mood, event, tone
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        email,
        user_info.store_name,
        user_info.category_main,
        user_info.category_sub,
        user_info.call_number,
        user_info.address,
        json.dumps([menu.model_dump() for menu in user_info.menus], ensure_ascii=False),
        json.dumps(user_info.targets, ensure_ascii=False) if user_info.targets else None,
        json.dumps(user_info.selling_points, ensure_ascii=False) if user_info.selling_points else None,
        user_info.ad_purpose,
        user_info.mood,
        user_info.event,
        user_info.tone,
    ))

    conn.commit()
    conn.close()

def store_names(email):
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT store_name FROM user_information WHERE email = ?", (email,))

    stores = cur.fetchall()
    stores = [row[0] for row in stores] 
    conn.commit()
    conn.close()
        
    return stores

def store_info(store_name, email):
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_information WHERE email = ? and store_name = ?", (email, store_name))

    row = cur.fetchone()
    conn.close()

    result = dict(row)
    
    return result

def update_store(user_info: UserInformation, email):
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    UPDATE user_information
    SET 
        category_main = ?,
        category_sub = ?,
        call_number = ?,
        address = ?,
        menus = ?,
        targets = ?,
        selling_points = ?,
        ad_purpose = ?,
        mood = ?,
        event = ?,
        tone = ?
    WHERE email = ? AND store_name = ?
    """, (
        user_info.category_main,
        user_info.category_sub,
        user_info.call_number,
        user_info.address,
        json.dumps([menu.model_dump() for menu in user_info.menus], ensure_ascii=False),
        json.dumps(user_info.targets, ensure_ascii=False) if user_info.targets else None,
        json.dumps(user_info.selling_points, ensure_ascii=False) if user_info.selling_points else None,
        user_info.ad_purpose,
        user_info.mood,
        user_info.event,
        user_info.tone,
        email,
        user_info.store_name   
    ))

    conn.commit()
    conn.close()

def delete_store(email, store_name):
    # 데이터베이스 내의 정보 삭제
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM user_information
        WHERE email = ? AND store_name = ?
    """, (email, store_name))

    conn.commit()
    conn.close()

    # 이미지 등 생성한 정보 삭제
    store_folder_path = os.path.join(DATA_DIR, email, store_name)

    if os.path.exists(store_folder_path):
        shutil.rmtree(store_folder_path)

def input_check(userinfo: UserInformation):
    missing_fields = []
    if not userinfo.store_name.strip():
        missing_fields.append("상호명")
    if not userinfo.category_main.strip():
        missing_fields.append("업종 대분류")
    if not userinfo.category_sub.strip():
        missing_fields.append("업종 소분류")
    if not userinfo.call_number.strip():
        missing_fields.append("연락처")
    if not userinfo.address.strip():
        missing_fields.append("주소")
    for menu_index, menu in enumerate(userinfo.menus, start=1):
        for key, key_ko in zip(['name', 'price'], ['메뉴명', '가격']):
            if not menu[key]:
                missing_fields.append(f"{menu_index}번 메뉴의 {key_ko}")
    
    return missing_fields