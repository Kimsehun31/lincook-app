import sqlite3
import datetime
import uuid

DB_NAME = "lincook.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# ==========================================
# 1. 초기화 함수 (테이블 생성)
# ==========================================
def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # users 테이블 (성별, 토큰 등 모든 필드 포함)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT,
            email TEXT,
            address TEXT,
            birthdate TEXT,
            gender TEXT,
            profile_image TEXT,
            token TEXT, 
            created_at TEXT
        )
    ''')
    
    # recipes 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT,
            source_url TEXT,
            source_type TEXT,
            cuisine_type TEXT,
            dish_type TEXT,
            ingredients TEXT,
            folder_name TEXT DEFAULT '기본 폴더',
            is_favorite INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# 앱 시작 시 DB 체크
init_db()

# ==========================================
# 2. 사용자 관련 함수 (auth.py와 짝맞춤)
# ==========================================

# [수정됨] auth.py에서 호출하는 add_user 함수 (인자 8개)
def add_user(username, password, nickname, profile_image, birthdate, email, address, gender):
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''INSERT INTO users 
                     (username, password, nickname, profile_image, birthdate, email, address, gender, created_at) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (username, password, nickname, profile_image, birthdate, email, address, gender, now))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_login(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        # 딕셔너리로 변환해서 반환 (auth.py가 편하게 쓰도록)
        return {
            "id": user[0], "username": user[1], "nickname": user[3]
        }
    return None

def is_username_taken(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username=?', (username,))
    result = c.fetchone()
    conn.close()
    return result is not None

def is_nickname_taken(nickname):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE nickname=?', (nickname,))
    result = c.fetchone()
    conn.close()
    return result is not None

# [추가됨] 아이디 찾기 기능
def find_username_by_email(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE email=?', (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# [추가됨] 비밀번호 재설정 기능
def reset_password(username, email, new_password):
    conn = get_connection()
    c = conn.cursor()
    # 아이디와 이메일이 모두 일치하는지 확인
    c.execute('SELECT 1 FROM users WHERE username=? AND email=?', (username, email))
    if not c.fetchone():
        conn.close()
        return False
    
    c.execute('UPDATE users SET password=? WHERE username=?', (new_password, username))
    conn.commit()
    conn.close()
    return True

# ==========================================
# 3. 토큰 & 자동 로그인 관련
# ==========================================

def update_auth_token(user_id):
    conn = get_connection()
    c = conn.cursor()
    new_token = str(uuid.uuid4()) # 랜덤 토큰 생성
    c.execute('UPDATE users SET token=? WHERE id=?', (new_token, user_id))
    conn.commit()
    conn.close()
    return new_token

def get_user_by_token(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE token=?', (token,))
    user = c.fetchone()
    conn.close()
    if user:
        return {
            "id": user[0], "username": user[1], "nickname": user[3]
        }
    return None

def delete_auth_token(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET token=NULL WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def get_user_info(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        # users 테이블 컬럼 순서: id, username, password, nickname, email, address, birthdate, gender, profile_image, token, created_at
        return {
            "id": row[0], "username": row[1], "nickname": row[3],
            "email": row[4], "address": row[5], "birthdate": row[6],
            "gender": row[7], "created_at": row[10]
        }
    return None

def update_user_profile(user_id, nickname, email, address, birthdate):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET nickname=?, email=?, address=?, birthdate=? WHERE id=?', 
              (nickname, email, address, birthdate, user_id))
    conn.commit()
    conn.close()

def delete_user_account(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM recipes WHERE user_id=?', (user_id,))
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

# ==========================================
# 4. 레시피 관련 함수 (기존 유지)
# ==========================================

def add_recipe(user_id, title, content, source_url, source_type, cuisine_type, dish_type, ingredients):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO recipes 
                 (user_id, title, content, source_url, source_type, cuisine_type, dish_type, ingredients, created_at) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, title, content, source_url, source_type, cuisine_type, dish_type, ingredients, now))
    conn.commit()
    conn.close()

def get_user_recipes(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM recipes WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def toggle_favorite(recipe_id, user_id, current_status):
    conn = get_connection()
    c = conn.cursor()
    new_status = 1 if current_status == 0 else 0
    c.execute('UPDATE recipes SET is_favorite=? WHERE id=? AND user_id=?', (new_status, recipe_id, user_id))
    conn.commit()
    conn.close()

def update_recipe(recipe_id, user_id, title, content, cuisine, dish, ingredients, folder):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''UPDATE recipes SET title=?, content=?, cuisine_type=?, dish_type=?, ingredients=?, folder_name=? 
                 WHERE id=? AND user_id=?''', 
              (title, content, cuisine, dish, ingredients, folder, recipe_id, user_id))
    conn.commit()
    conn.close()

def delete_recipe(recipe_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM recipes WHERE id=? AND user_id=?', (recipe_id, user_id))
    conn.commit()
    conn.close()

def delete_recipes_list(recipe_ids, user_id):
    if not recipe_ids: return
    conn = get_connection()
    c = conn.cursor()
    placeholders = ','.join('?' for _ in recipe_ids)
    sql = f'DELETE FROM recipes WHERE id IN ({placeholders}) AND user_id=?'
    c.execute(sql, recipe_ids + [user_id])
    conn.commit()
    conn.close()