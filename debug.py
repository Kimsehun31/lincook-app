import youtube_transcript_api
import os

print("\n" + "="*50)
print("🕵️‍♂️ 범인 색출 시작...")
print("="*50)

# 1. 파이썬이 'youtube_transcript_api'를 어디서 가져왔는지 위치 출력
try:
    location = youtube_transcript_api.__file__
    print(f"📂 라이브러리 위치: {location}")
    
    # 만약 위치가 'coding' 폴더 안이라면 그게 범인입니다!
    if "coding" in location and "site-packages" not in location:
        print("🚨 [검거 완료] 범인을 찾았습니다!")
        print("👉 이 파일이 진짜 라이브러리인 척을 하고 있습니다. 삭제하거나 이름을 바꾸세요.")
    else:
        print("✅ 위치는 정상적인 것 같습니다 (라이브러리 폴더).")

except Exception as e:
    print(f"❓ 위치 확인 불가: {e}")

print("-" * 30)

# 2. 그 안에 진짜 기능이 있는지 확인
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    print("✅ YouTubeTranscriptApi 클래스 불러오기 성공")
    
    if hasattr(YouTubeTranscriptApi, 'get_transcript'):
        print("✅ get_transcript 기능도 있음 (정상)")
    else:
        print("❌ get_transcript 기능이 없음 (비정상)")
        print(f"📜 현재 가진 기능들: {dir(YouTubeTranscriptApi)}")
        
except ImportError:
    print("❌ YouTubeTranscriptApi 클래스 자체를 못 찾음")

print("="*50 + "\n")