import google.generativeai as genai

# ⚠️ 여기에 아까 사용하신 API 키를 넣어주세요
GEMINI_API_KEY = "AIzaSyAXVoIE7fgX2M2Ufw0K8lgyOV4GaDcfmDI"

genai.configure(api_key=GEMINI_API_KEY, transport='rest')

print("========================================")
print("🔍 내 키로 사용 가능한 모델 목록 조회 중...")
print("========================================")

try:
    available_models = []
    # 구글 서버에 직접 모델 목록 요청
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ 사용 가능: {m.name}")
            available_models.append(m.name)

    print("========================================")
    
    if not available_models:
        print("❌ 사용 가능한 모델이 하나도 없습니다.")
        print("👉 원인: API 키가 'Generative Language API' 서비스에 연결되지 않았거나, 무료 사용량이 만료되었습니다.")
    else:
        # 가장 추천하는 모델 찾기
        best_model = available_models[0]
        # 보통 models/gemini-pro 형태인데, models/를 빼고 써야 할 때도 있음
        clean_name = best_model.replace("models/", "")
        
        print(f"🎉 해결책: namanerecipe.py의 model 변수를 아래 이름으로 바꾸세요!")
        print(f"\nmodel = genai.GenerativeModel('{clean_name}')\n")

except Exception as e:
    print(f"❌ 연결 에러: {e}")