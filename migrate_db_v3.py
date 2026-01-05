# migrate_db_v3.py
import sqlite3

DB_FILE = 'namane_app.db'

def add_features():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("🚧 3차 DB 공사(즐겨찾기 & 폴더) 시작...")

    try:
        # 1. 즐겨찾기 컬럼 (0:해제, 1:설정)
        cursor.execute("ALTER TABLE recipes ADD COLUMN is_favorite INTEGER DEFAULT 0")
        print("✅ 'is_favorite' 추가 성공!")
    except:
        print("ℹ️ 'is_favorite' 이미 있음 (패스)")

    try:
        # 2. 폴더명 컬럼 (기본값: '기본 폴더')
        cursor.execute("ALTER TABLE recipes ADD COLUMN folder_name TEXT DEFAULT '기본 폴더'")
        print("✅ 'folder_name' 추가 성공!")
    except:
        print("ℹ️ 'folder_name' 이미 있음 (패스)")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_features()