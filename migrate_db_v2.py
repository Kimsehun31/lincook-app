# migrate_db_v2.py
import sqlite3

DB_FILE = 'namane_app.db'

def add_image_column():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("🚧 2차 DB 공사(사진 저장소) 시작...")

    try:
        # BLOB은 바이너리(사진, 파일 등) 데이터를 저장하는 타입입니다.
        cursor.execute("ALTER TABLE recipes ADD COLUMN image_data BLOB")
        print("✅ 'image_data' 컬럼 추가 성공!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ 이미 사진 저장 공간이 있습니다. (패스)")
        else:
            print(f"❌ 에러 발생: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_image_column()