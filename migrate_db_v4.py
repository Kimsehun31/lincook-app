# migrate_db_v4.py
import sqlite3

DB_FILE = 'namane_app.db'

def update_users_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("🚧 4차 DB 공사 (회원기능 강화) 시작...")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN gender TEXT")
        print("✅ 'gender' 컬럼 추가 성공!")
    except: print("ℹ️ 'gender' 이미 있음")

    try:
        # 자동 로그인을 위한 토큰 저장소
        cursor.execute("ALTER TABLE users ADD COLUMN auth_token TEXT")
        print("✅ 'auth_token' 컬럼 추가 성공!")
    except: print("ℹ️ 'auth_token' 이미 있음")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_users_table()
