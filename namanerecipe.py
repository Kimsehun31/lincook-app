import re
import requests
import yt_dlp
import google.generativeai as genai
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# ==========================================
# 🔑 설정 (API 키 입력)
# ==========================================
GEMINI_API_KEY = 'AIzaSyAXVoIE7fgX2M2Ufw0K8lgyOV4GaDcfmDI'  # 여기에 키를 붙여넣으세요!

# Gemini 모델 설정
# Gemini 모델 설정 (transport='rest' 추가가 핵심!)
from google.generativeai.types import HarmCategory, HarmBlockThreshold

genai.configure(api_key=GEMINI_API_KEY, transport='rest')
# 가장 안정적인 gemini-pro 모델 사용
model = genai.GenerativeModel('gemini-2.5-flash')

# ==========================================
# 1. 🕵️‍♂️ 수거반 (Extractor) - 유튜브 & 블로그
# ==========================================

def get_youtube_data(url):
    """
    1순위: 자막 추출 시도
    2순위: 실패 시 영상 제목 + 설명(더보기) 추출 (yt-dlp 사용)
    """
    video_id = extract_video_id(url)
    data = ""
    source_type = ""

    # 1. 자막 시도
    print("   ↳ 1차 시도: 자막 추출 중...")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        formatter = TextFormatter()
        data = formatter.format_transcript(transcript)
        source_type = "유튜브 자막"
        print("   ✅ 자막 추출 성공!")
        return data, source_type
    except Exception as e:
        print(f"   ❌ 자막 추출 실패 ({e})")
        print("   ↳ 2차 시도: 영상 설명(더보기) 추출 중...")

    # 2. 설명(메타데이터) 시도 - yt-dlp 이용
    try:
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '제목 없음')
            description = info.get('description', '')
            data = f"영상 제목: {title}\n\n영상 설명:\n{description}"
            source_type = "유튜브 영상 설명"
            print("   ✅ 영상 설명 추출 성공!")
            return data, source_type
    except Exception as e:
        return None, f"모든 추출 실패: {e}"

def get_blog_content(url):
    """블로그 본문 추출"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
            return soup.get_text(), "블로그 글"
        return None, f"접속 오류 ({response.status_code})"
    except Exception as e:
        return None, f"크롤링 에러 ({e})"

def extract_video_id(url):
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

# ==========================================
# 2. 👨‍🍳 주방장 (Gemini AI Processor)
# ==========================================

def cook_recipe(raw_text, source_type):
    """Gemini에게 요리법 정리를 시킵니다."""
    
    prompt = f"""
    당신은 요리 레시피 전문 에디터입니다. 
    아래 제공된 텍스트({source_type})를 분석해서 사용자가 보기 편한 '요리 카드'를 만들어주세요.

    [텍스트 내용]
    {raw_text[:5000]} (생략)

    [작성 규칙]
    1. 재료는 무조건 **'2인분 기준'**으로 환산해서 적어주세요.
    2. 말투는 **'~한다', '~임'** 같은 깔끔한 문어체로 작성하세요.
    3. 잡담은 제거하고 요리법과 팁만 남기세요.
    4. 영상 설명만 있어서 정보가 부족하면 "영상 설명 기반으로 재구성했습니다"라고 적어주세요.

    [출력 양식]
    # (요리 이름) 🍳

    ## 🛒 재료 (2인분)
    - (재료명): (수량)

    ## 👩‍🍳 조리 순서
    1. 
    2. 
    3. 

    ## 💡 팁
    - (팁 내용)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI 요리사 연결 실패: {e}"

# ==========================================
# 🚀 메인 실행
# ==========================================
def main():
    print("\n🥘 Namanerecipe : 나만의 레시피 변환기")
    print("========================================")
    url = input("🔗 링크 입력: ").strip()
    
    if not url: return

    # 1. 수거 단계
    video_id = extract_video_id(url)
    if video_id:
        print(f"🎥 유튜브 감지! (ID: {video_id})")
        raw_text, source_type = get_youtube_data(url)
    else:
        print("📝 블로그 감지!")
        raw_text, source_type = get_blog_content(url)

    # 2. 요리 단계 (AI 호출)
    if raw_text:
        print(f"\n✅ {source_type} 확보 완료! AI 요리사가 요리 중입니다...🍳")
        recipe_card = cook_recipe(raw_text, source_type)
        
        print("\n" + "="*40)
        print(recipe_card)
        print("="*40)
        
        # 파일 저장
        with open("final_recipe.md", "w", encoding="utf-8") as f:
            f.write(recipe_card)
        print("\n💾 'final_recipe.md' 파일로 저장되었습니다.")
    else:
        print(f"❌ 실패: {source_type}")

if __name__ == "__main__":
    main()