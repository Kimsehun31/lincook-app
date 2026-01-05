import sqlite3
import datetime

DB_NAME = "lincook.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# ==========================================
# 1. 초기화 함수 (테이블이 없으면 생성)
# ==========================================
def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # users 테이블 (token 컬럼 추가됨!)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT,
            email TEXT,
            address TEXT,
            birthdate TEXT,
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

init_db()

# ==========================================
# 2. 사용자 관련 함수
# ==========================================

def create_user(username, password, nickname, email, address, birthdate):
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # token은 처음엔 NULL
        c.execute('INSERT INTO users (username, password, nickname, email, address, birthdate, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (username, password, nickname, email, address, birthdate, now))
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
    return user

def is_username_taken(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username=?', (username,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_user_info(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        # DB 컬럼 순서에 맞춰 매핑 (id, username, password, nickname, email, address, birthdate, token, created_at)
        return {
            "id": row[0], "username": row[1], "nickname": row[3],
            "email": row[4], "address": row[5], "birthdate": row[6], "created_at": row[8]
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

# 👇 [추가된 함수] 자동 로그인을 위한 토큰 관련 함수들
def update_user_token(user_id, token):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET token=? WHERE id=?', (token, user_id))
    conn.commit()
    conn.close()

def get_user_by_token(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE token=?', (token,))
    user = c.fetchone()
    conn.close()
    return user

# ==========================================
# 3. 레시피 관련 함수 (기존과 동일)
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

def is_nickname_taken(nickname):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE nickname=?', (nickname,))
    result = c.fetchone()
    conn.close()
    return result is not None