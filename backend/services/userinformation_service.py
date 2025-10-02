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
        email, store_name, category_main, category_sub, call_number, address
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        email,
        user_info.store_name,
        user_info.category_main,
        user_info.category_sub,
        user_info.call_number,
        user_info.address,
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
    WHERE email = ? AND store_name = ?
    """, (
        user_info.category_main,
        user_info.category_sub,
        user_info.call_number,
        user_info.address,
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

def drop_table_if_has_column(table_name, column_name, db_path=DB_PATH):
    # 1. DB 파일이 존재하는지 확인
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 2. 테이블 존재 여부 확인
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
    if cur.fetchone() is None:
        conn.close()
        return

    # 3. 컬럼 존재 여부 확인
    cur.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cur.fetchall()]

    if column_name in columns:
        cur.execute(f"DROP TABLE {table_name};")
        conn.commit()

    conn.close()

drop_table_if_has_column("user_information", "menus")