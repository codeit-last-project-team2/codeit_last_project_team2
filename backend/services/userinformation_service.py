from backend.models.user_information_model import UserInformation, StoresRequest, StoreInfoRequest
import os, sqlite3, json



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
        

def upload_store(user_info: UserInformation):
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
        user_info.email,
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

def store_names(req:StoresRequest):
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT store_name FROM user_information WHERE email = ?", (req.user_email,))

    stores = cur.fetchall()
    stores = [row[0] for row in stores] 
    conn.commit()
    conn.close()
        
    return stores

def store_info(req: StoreInfoRequest):
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_information WHERE email = ? and store_name = ?", (req.user_email, req.store_name))

    row = cur.fetchone()
    conn.close()

    result = dict(row)
    
    return result

def update_store(user_info: UserInformation):
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
        user_info.email,
        user_info.store_name   
    ))

    conn.commit()
    conn.close()

def delete_store(req: StoreInfoRequest):
    if not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        _make_db()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM user_information
        WHERE email = ? AND store_name = ?
    """, (req.user_email, req.store_name))

    conn.commit()
    conn.close()