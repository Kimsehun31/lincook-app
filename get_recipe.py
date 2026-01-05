import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

def extract_video_id(url):
    """
    유튜브 URL에서 영상 ID만 추출하는 함수
    (예: https://youtu.be/abc1234 -> abc1234)
    """
    # 정규표현식으로 ID 추출 (일반 링크, 단축 링크 모두 대응)
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def main():
    print("========================================")
    print("🎬 유튜브 레시피 자막 추출기")
    print("========================================")
    
    # 1. URL 입력 받기
    url = input("유튜브 영상 링크를 입력하세요: ").strip()
    
    video_id = extract_video_id(url)
    
    if not video_id:
        print("❌ 올바른 유튜브 링크가 아닙니다. 다시 확인해주세요.")
        return

    print(f"⏳ 영상 ID({video_id})에서 자막을 추출하는 중...")

    try:
        # 2. 자막 가져오기 (한국어 -> 영어 순으로 시도)
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        
        # 3. 텍스트로 변환
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript)
        
        # 4. 파일로 저장
        filename = "recipe_raw.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text_formatted)
            
        print("========================================")
        print(f"✅ 성공! '{filename}' 파일에 저장되었습니다.")
        print("📂 파일을 열어서 내용을 확인해보세요.")
        print("========================================")

    except Exception as e:
        print(f"❌ 실패: 자막을 가져오지 못했습니다.\n원인: {e}")

if __name__ == "__main__":
    main()