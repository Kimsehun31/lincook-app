from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# 테스트할 영상 ID (원하는 영상의 ID로 바꾸세요)
# 예: https://www.youtube.com/watch?v=D-qRiMK5w90 -> 'D-qRiMK5w90'
video_id = 'D-qRiMK5w90' 

try:
    # 1. 자막 가져오기 (한국어 우선, 없으면 영어)
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
    
    # 2. 보기 좋게 텍스트로 변환
    formatter = TextFormatter()
    text_formatted = formatter.format_transcript(transcript)
    
    print("=== 자막 추출 성공! ===")
    print(text_formatted[:500]) # 너무 기니까 앞부분 500자만 출력
    print("... (생략)")

    # 3. 파일로 저장하기 (선택 사항)
    with open('transcript.txt', 'w', encoding='utf-8') as f:
        f.write(text_formatted)
        print("✅ 'transcript.txt' 파일로 저장되었습니다.")

except Exception as e:
    print(f"❌ 에러 발생: {e}")