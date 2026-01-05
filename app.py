import streamlit as st
from streamlit_option_menu import option_menu
import auth
import database as db
import google.generativeai as genai
import re
import requests
import yt_dlp
import instaloader
import json
import time
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# ⭐ [추가] 앱이 켜질 때마다 DB 테이블이 있는지 확실하게 체크!
db.init_db()

# ==========================================
# 1. 기본 설정 및 API 연결
# ==========================================
st.set_page_config(
    page_title="링쿡(Lincook) - 스마트 셰프",
    page_icon="🍳",
    layout="wide"
)

# 비밀번호 관리 (secrets.toml)
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.error("secrets.toml에 API 키가 없습니다.")
        model = None
except Exception as e:
    st.warning("API 키 설정 중 오류가 발생했습니다. 로컬 환경인지 확인해주세요.")
    # 로컬 테스트용 (필요시 주석 해제하여 사용)
    # genai.configure(api_key="여기에_직접_키를_넣으세요")
    # model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# 🛒 장보기 계산기 함수
# ==========================================
def generate_shopping_list(selected_recipes):
    shopping_dict = {}
    for recipe in selected_recipes:
        ingredients = recipe.get('ingredients')
        if isinstance(ingredients, str):
            try: ingredients = json.loads(ingredients)
            except: continue 
        if ingredients:
            for ing in ingredients:
                if isinstance(ing, dict):
                    name = ing.get('name', '').strip()
                    amount = ing.get('amount', '').strip()
                    if name in shopping_dict: shopping_dict[name].append(amount)
                    else: shopping_dict[name] = [amount]
    final_list = []
    for name, amounts in shopping_dict.items():
        combined_amount = " + ".join(amounts)
        final_list.append(f"{name}: {combined_amount}")
    return final_list

# ==========================================
# 🖼️ 링크 미리보기 카드 함수 (수정됨!)
# ==========================================
def show_link_card(url):
    """
    URL을 입력받아 유튜브면 영상을, 그 외면 썸네일 카드를 보여줍니다.
    """
    if not url: return

    # 1. 유튜브 처리
    if "youtube.com" in url or "youtu.be" in url:
        st.video(url)
        return

    # 2. 일반 링크 (블로그/인스타) 썸네일 카드 만들기
    try:
        # 인스타그램은 보안 이슈로 버튼 처리
        if "instagram.com" in url:
            st.link_button("📸 인스타그램 원본 보기", url, use_container_width=True)
            return

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # 네이버 블로그 주소 처리 (PC/Mobile 구분)
        target_url = url
        if "blog.naver.com" in url:
            if "m.blog.naver.com" not in url:
                target_url = url.replace("blog.naver.com", "m.blog.naver.com")
        
        response = requests.get(target_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 메타 태그 추출
        og_image = soup.select_one('meta[property="og:image"]')
        og_title = soup.select_one('meta[property="og:title"]')
        og_desc = soup.select_one('meta[property="og:description"]')

        image_url = og_image['content'] if og_image else None
        title = og_title['content'] if og_title else "원본 링크 확인하기"
        desc = og_desc['content'] if og_desc else ""

        # 카드 UI 렌더링
        with st.container(border=True):
            if image_url:
                # [핵심 수정] 마크다운 대신 HTML <img> 태그 사용 (referrerpolicy="no-referrer" 추가)
                # 이렇게 해야 네이버가 이미지를 차단하지 않습니다.
                st.markdown(
                    f"""
                    <a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">
                        <img src="{image_url}" style="width: 100%; border-radius: 8px; margin-bottom: 10px;" referrerpolicy="no-referrer">
                    </a>
                    """, 
                    unsafe_allow_html=True
                )
            
            # 제목 (클릭 가능)
            st.markdown(f"**[{title}]({url})**")
            
            # 설명
            if desc:
                st.caption(desc[:80] + "..." if len(desc) > 80 else desc)
            else:
                st.caption(url)

    except Exception:
        # 에러 나면 깔끔한 버튼 보여주기
        st.link_button("👉 원본 링크 바로가기", url, use_container_width=True)


# ==========================================
# 🕵️‍♂️ 크롤링 및 AI 함수들
# ==========================================

def get_instagram_content(url):
    shortcode_match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    if not shortcode_match: return None, "올바른 인스타그램 주소가 아닙니다."
    shortcode = shortcode_match.group(1)
    try:
        L = instaloader.Instaloader()
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        return f"작성자: {post.owner_username}\n\n내용:\n{post.caption}", "인스타그램"
    except Exception as e:
        return None, f"인스타그램 접속 실패: {e}"

def extract_video_id(url):
    if "youtube.com" not in url and "youtu.be" not in url: return None
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

def get_youtube_data(url):
    video_id = extract_video_id(url)
    if not video_id: return None, "유튜브 ID 추출 실패"
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        formatter = TextFormatter()
        return formatter.format_transcript(transcript), "유튜브 자막"
    except Exception:
        try:
            ydl_opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                data = f"영상 제목: {info.get('title')}\n\n설명:\n{info.get('description')}"
                return data, "유튜브 영상 설명"
        except Exception as e:
            return None, f"추출 실패: {e}"

def get_blog_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        if "blog.naver.com" in url:
            # iframe 처리 (PC 주소일 경우)
            iframe = soup.select_one('iframe#mainFrame')
            if iframe:
                real_url = "https://blog.naver.com" + iframe['src']
                response = requests.get(real_url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
            
            main_content = soup.select_one('.se-main-container') or soup.select_one('#postViewArea')
            if main_content:
                for s in main_content(["script", "style"]): s.extract()
                return main_content.get_text(separator="\n"), "네이버 블로그"

        for script in soup(["script", "style", "nav", "header", "footer"]): script.extract()
        return soup.get_text(separator="\n"), "블로그 글"
    except Exception as e:
        return None, f"크롤링 에러: {e}"

import json

def cook_recipe(raw_text, source_type, model):
    try:
        prompt = f"""
        당신은 '링쿡(Lincook)'의 스마트 셰프입니다.
        아래 텍스트({source_type})를 분석해서 다음 정보를 JSON 형식으로 추출하세요.
        [분석할 텍스트] {raw_text[:15000]}
        [작성 규칙]
        1. title: 요리 제목 (명사형)
        2. markdown_content: 2인분 기준 상세 레시피 (마크다운)
        3. cuisine_type: 국적 (한식, 중식, 일식, 양식, 아시안, 퓨전, 기타)
        4. dish_type: 종류 (국/탕/찌개, 구이/스테이크, 볶음, 튀김, 찜/조림, 밥/면, 샐러드, 디저트, 기타)
        5. ingredients: [{{"name": "재료명", "amount": "수량"}}, ...] (수량은 분수, 영문단위 붙여쓰기)
        응답은 오직 JSON 형식으로만 주세요.
        """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        # [안전장치 1] 응답 텍스트에서 불필요한 마크다운 기호 제거 (가끔 AI가 ```json 을 붙여서 줌)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(clean_text)

    except Exception as e:
        # [안전장치 2] 에러가 발생하면 빨간 박스 대신 콘솔에 이유를 출력하고 None을 반환
        print(f"⚠️ 레시피 생성 중 오류 발생: {e}")
        return None

# 🔄 재료 대체 사전
INGREDIENT_SUBSTITUTES = {
    "대파": ["쪽파", "실파", "양파", "부추"], "쪽파": ["대파", "실파", "부추"], "양파": ["대파", "샬롯", "양배추"],
    "마늘": ["마늘가루", "다진마늘"], "다진마늘": ["통마늘", "마늘가루"], "청양고추": ["페페론치노", "홍고추"],
    "페페론치노": ["청양고추", "건고추"], "감자": ["고구마"], "고구마": ["감자"], "배추": ["양배추", "알배기배추"],
    "양배추": ["배추", "숙주"], "숙주": ["콩나물"], "콩나물": ["숙주"], "무": ["콜라비"],
    "돼지고기": ["소고기", "닭고기", "베이컨", "햄", "스팸"], "소고기": ["돼지고기"], "닭고기": ["돼지고기"],
    "베이컨": ["햄", "스팸"], "햄": ["베이컨", "스팸"], "스팸": ["햄", "참치캔"], "새우": ["오징어", "맛살"],
    "간장": ["진간장", "참치액", "굴소스"], "굴소스": ["간장", "치킨스톡"], "액젓": ["참치액", "국간장"],
    "설탕": ["올리고당", "꿀", "물엿", "매실청"], "식초": ["레몬즙"], "맛술": ["미림", "소주"],
    "식용유": ["포도씨유", "카놀라유"], "밀가루": ["부침가루", "전분"], "전분": ["밀가루", "찹쌀가루"]
}

def search_recipes_by_fridge(user_ingredients, all_recipes):
    results = []
    inputs = [i.strip() for i in user_ingredients.split(',') if i.strip()]
    if not inputs: return []

    for recipe in all_recipes:
        score = 0.0
        matched_details = [] 
        r_ingredients = recipe['ingredients'] 
        if isinstance(r_ingredients, str):
            try:
                if r_ingredients.startswith('['):
                     ing_list = json.loads(r_ingredients)
                     r_ingredients = [item['name'] for item in ing_list]
            except: pass
        if not r_ingredients: continue
        target_str = str(r_ingredients)

        for user_ing in inputs:
            if user_ing in target_str:
                score += 1.0
                matched_details.append(f"{user_ing}")
                continue 
            substitutes = INGREDIENT_SUBSTITUTES.get(user_ing, [])
            for sub in substitutes:
                if sub in target_str:
                    score += 0.5
                    matched_details.append(f"{sub}(대체 0.5)")
                    break 
        if score > 0:
            recipe['match_score'] = score
            recipe['matched_keywords'] = matched_details
            results.append(recipe)
            
    results.sort(key=lambda x: x['match_score'], reverse=True)
    return results

# ==========================================
# 🖥️ 화면 구성 (브랜드: Lincook)
# ==========================================
st.set_page_config(page_title="링쿡 - Lincook", page_icon="🔗", layout="wide")
auth.init_session_state()

# [UI 팁] Streamlit 기본 스타일 숨기기
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

if not st.session_state['is_logged_in']:
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.markdown("<br><br>", unsafe_allow_html=True) 
        st.title("🔗 링쿡 (Lincook)")
        st.markdown("### 링크 하나로 완성하는 나만의 주방\n유튜브, 인스타그램, 블로그에서 본 맛있는 요리들... 눈으로만 보지 말고 **링쿡** 하세요!")
        st.info("💡 지금 가입하고 나만의 레시피북을 만들어보세요!")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True): auth.login_ui()
else:
    with st.sidebar:
        st.title("🔗 Lincook")
        st.caption(f"Chef **{st.session_state['user_name']}**님의 주방")
        selected = option_menu(menu_title=None, options=["레시피 링쿡!", "나의 요리책", "냉장고를 부탁해", "주방 설정"], 
            icons=["magic", "book", "snow", "gear"], default_index=0,
            styles={"container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "#FF4B4B", "font-size": "20px"}, 
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin":"5px", "--hover-color": "#eee"},
                    "nav-link-selected": {"background-color": "#ffecec", "color": "#FF4B4B"}})
        st.divider()
        auth.logout_ui()
        st.divider() 

    # --- 메뉴 1: 레시피 생성 ---
    if selected == "레시피 링쿡!":
        st.header("🍳 레시피 링쿡 (Lin+Cook)")
        st.caption("링크를 넣으면 AI가 요리책을 만들어 드려요.")
        
        with st.container(border=True):
            with st.form("recipe_input_form"):
                url = st.text_input("🔗 레시피 링크 붙여넣기", placeholder="유튜브, 인스타그램, 블로그 주소...")
                submitted = st.form_submit_button("요리책 만들기 🚀", type="primary", use_container_width=True)

            if submitted:
                if not url: st.warning("링크를 입력해주세요!")
                else:
                    with st.spinner('👨‍🍳 링크를 분석해서 요리책을 쓰고 있어요...'):
                        video_id = extract_video_id(url)
                        if "instagram.com" in url:
                            st.toast("📸 인스타그램 감지")
                            raw_text, source_type = get_instagram_content(url)
                        elif video_id: 
                            st.toast("🎥 유튜브 감지")
                            raw_text, source_type = get_youtube_data(url)
                        else:
                            st.toast("📝 블로그 감지")
                            raw_text, source_type = get_blog_content(url)

                        if raw_text and "실패" not in str(source_type):
                            try:
                                recipe_data = cook_recipe(raw_text, source_type)
                                st.session_state['generated_data'] = recipe_data
                                st.session_state['current_url'] = url
                                st.session_state['current_source'] = source_type
                            except Exception as e: st.error(f"AI 분석 실패: {e}")
                        else: st.error(f"데이터를 가져올 수 없어요: {source_type}")

        if 'generated_data' in st.session_state:
            data = st.session_state['generated_data']
            st.divider()
            with st.container(border=True):
                c_head, c_btn = st.columns([4, 1])
                with c_head: st.subheader(f"✨ {data.get('title')}")
                st.markdown(f"**{data.get('cuisine_type')}** | **{data.get('dish_type')}**")
                
                # 저장 전 미리보기
                show_link_card(st.session_state.get('current_url'))
                st.divider()

                ing_display = data.get('ingredients')
                if isinstance(ing_display, list):
                    ing_text = ", ".join([f"{i['name']}({i['amount']})" for i in ing_display])
                    st.info(f"🥕 핵심 재료: {ing_text}")
                else: st.info(f"🥕 핵심 재료: {ing_display}")
                
                st.markdown(data.get('markdown_content'))
                st.divider()
                col_save, col_down = st.columns([1, 1])
                with col_save:
                    if st.button("📥 내 요리책에 저장", type="primary", use_container_width=True):
                        try:
                            # 1. 재료 데이터를 문자열로 변환
                            ing_str = json.dumps(data.get('ingredients'), ensure_ascii=False)
        
                            # 2. DB 저장 시도
                            db.add_recipe(st.session_state['user_id'], data.get('title'), data.get('markdown_content'),
                                st.session_state['current_url'], st.session_state['current_source'],
                                data.get('cuisine_type'), data.get('dish_type'), ing_str)
        
                            # 3. 성공 시 축하 효과  
                            st.balloons()
                            st.toast("저장되었습니다! 📚")
        
                        except Exception as e:
                            # 4. 실패 시 빨간 박스 대신 예쁜 경고창 출력
                            st.error("저장에 실패했습니다. 잠시 후 다시 시도해주세요.")
                            print(f"DB 저장 오류: {e}") # 개발자 확인용 (콘솔에만 출력됨)
                with col_down:
                     st.download_button("💾 파일로 저장", data.get('markdown_content'), "recipe.md", use_container_width=True)
                
    # --- 메뉴 2: 나의 요리책 ---
    elif selected == "나의 요리책":
        if 'edit_mode_id' not in st.session_state: st.session_state['edit_mode_id'] = None
        col_title, col_shop, col_del = st.columns([6, 1.2, 1])
        with col_title: st.header(f"📚 {st.session_state['user_name']}님의 주방")
        
        my_recipes = db.get_user_recipes(st.session_state['user_id'])
        checked_recipes = []
        if my_recipes:
            for r in my_recipes:
                if st.session_state.get(f"chk_fav_{r['id']}", False) or st.session_state.get(f"chk_folder_{r['id']}", False):
                    checked_recipes.append(r)

        with col_shop:
            if st.button("🛒 장보기", use_container_width=True):
                if not checked_recipes: st.toast("먼저 레시피를 선택해주세요!")
                else: st.session_state['show_shopping_list'] = True
        with col_del:
            if st.button("🗑 삭제", type="primary", use_container_width=True):
                if not checked_recipes: 
                    st.warning("삭제할 레시피를 선택해주세요!") # toast보다 warning이 더 잘 보임
                else:
                    try:
                        # 1. 삭제 시도
                        db.delete_recipes_list([r['id'] for r in checked_recipes], st.session_state['user_id'])
            
                        # 2. 성공 시 새로고침
                        st.toast("삭제되었습니다.")
                        time.sleep(1)
                        st.rerun()
            
                    except Exception as e:
                        # 3. 실패 시 빨간 박스 방지
                        st.error("삭제 중 오류가 발생했습니다.")
                        print(f"DB 삭제 오류: {e}")

        if st.session_state.get('show_shopping_list'):
            st.divider()
            c_head, c_close = st.columns([9, 1])
            with c_head: st.subheader("🛒 장보기 체크리스트 (자동 합산)")
            with c_close:
                if st.button("X", help="닫기"): st.session_state['show_shopping_list'] = False; st.rerun()
            shopping_items = generate_shopping_list(checked_recipes)
            if shopping_items:
                st.info("💡 같은 재료는 모아서 보여드려요.")
                for item in shopping_items: st.checkbox(item)
            else: st.warning("선택한 레시피에 재료 정보가 없거나, 구버전 데이터입니다.")

        st.divider()
        if not my_recipes: st.info("아직 저장된 레시피가 없어요. '레시피 링쿡!' 메뉴에서 추가해보세요.")
        else:
            favorites = [r for r in my_recipes if r['is_favorite'] == 1]
            if favorites:
                st.subheader("⭐ 즐겨찾기")
                for recipe in favorites:
                    with st.container(border=True):
                        c_chk, c_content = st.columns([0.5, 9.5])
                        with c_chk: st.checkbox("", key=f"chk_fav_{recipe['id']}")
                        with c_content:
                            is_editing = (st.session_state['edit_mode_id'] == f"top_{recipe['id']}")
                            if is_editing:
                                st.markdown(f"### ✏️ 수정: {recipe['title']}")
                                with st.form(f"top_edit_form_{recipe['id']}"):
                                    new_title = st.text_input("제목", value=recipe['title'])
                                    c1, c2 = st.columns(2)
                                    all_c = ["한식", "중식", "일식", "양식", "아시안", "퓨전", "기타"]
                                    all_d = ["국/탕/찌개", "구이/스테이크", "볶음", "튀김", "찜/조림", "밥/면", "샐러드", "디저트", "기타"]
                                    with c1: new_cuisine = st.selectbox("종류", all_c, index=all_c.index(recipe['cuisine_type']) if recipe['cuisine_type'] in all_c else 0)
                                    with c2: new_dish = st.selectbox("방식", all_d, index=all_d.index(recipe['dish_type']) if recipe['dish_type'] in all_d else 0)
                                    new_ingredients = st.text_input("재료", value=recipe['ingredients'])
                                    new_content = st.text_area("내용", value=recipe['content'], height=200)
                                    col_s, col_c = st.columns([1,1])
                                    with col_s:
                                        if st.form_submit_button("💾 저장", type="primary"):
                                            db.update_recipe(recipe['id'], st.session_state['user_id'], new_title, new_content, new_cuisine, new_dish, new_ingredients, recipe['folder_name'])
                                            st.session_state['edit_mode_id'] = None; st.rerun()
                                    with col_c:
                                        if st.form_submit_button("취소"): st.session_state['edit_mode_id'] = None; st.rerun()
                            else:
                                h, f, e = st.columns([6,1,1])
                                with h: st.markdown(f"#### {recipe['title']}")
                                with f:
                                    if st.button("★", key=f"top_fav_{recipe['id']}", help="즐겨찾기 해제"):
                                        db.toggle_favorite(recipe['id'], st.session_state['user_id'], 1); st.rerun()
                                with e:
                                    if st.button("✏️", key=f"top_edt_{recipe['id']}"): st.session_state['edit_mode_id'] = f"top_{recipe['id']}"; st.rerun()
                                st.caption(f"{recipe['cuisine_type']} | {recipe['dish_type']}")
                                
                                with st.expander("레시피 보기"):
                                    source_url = recipe.get('source_url') or recipe.get('link') or recipe.get('url')
                                    show_link_card(source_url)
                                    st.markdown(recipe['content'])
            st.divider()

            st.subheader("📂 레시피 서재")
            folder_list = [r['folder_name'] for r in my_recipes]
            all_folders = sorted(list(set(folder_list))) if folder_list else ["기본 폴더"]
            
            for folder in all_folders:
                f_recipes = [r for r in my_recipes if r['folder_name'] == folder]
                with st.expander(f"📂 {folder} ({len(f_recipes)})", expanded=(folder=="기본 폴더")):
                    for recipe in f_recipes:
                        with st.container(border=True):
                            c_chk, c_content = st.columns([0.5, 9.5])
                            with c_chk: st.checkbox("", key=f"chk_folder_{recipe['id']}")
                            with c_content:
                                is_editing = (st.session_state['edit_mode_id'] == recipe['id'])
                                if is_editing:
                                    st.markdown(f"### ✏️ 수정: {recipe['title']}")
                                    with st.form(f"edit_form_{recipe['id']}"):
                                        new_title = st.text_input("제목", value=recipe['title'])
                                        c_f1, c_f2 = st.columns([1,1])
                                        all_f = all_folders + ["+ 새 폴더"]
                                        with c_f1: sel_f = st.selectbox("폴더", all_f, index=all_folders.index(recipe['folder_name']) if recipe['folder_name'] in all_folders else 0)
                                        with c_f2: new_f_in = st.text_input("새 폴더명", disabled=(sel_f!="+ 새 폴더"))
                                        final_f = new_f_in if sel_f=="+ 새 폴더" and new_f_in else ("기본 폴더" if sel_f=="+ 새 폴더" else sel_f)
                                        new_content = st.text_area("내용", value=recipe['content'], height=200)
                                        col_s, col_c = st.columns([1,1])
                                        with col_s:
                                            if st.form_submit_button("💾 저장", type="primary"):
                                                db.update_recipe(recipe['id'], st.session_state['user_id'], new_title, new_content, recipe['cuisine_type'], recipe['dish_type'], recipe['ingredients'], final_f)
                                                st.session_state['edit_mode_id'] = None; st.rerun()
                                        with col_c:
                                            if st.form_submit_button("취소"): st.session_state['edit_mode_id'] = None; st.rerun()
                                else:
                                    h, f, e = st.columns([6,1,1])
                                    with h: st.markdown(f"#### {recipe['title']}")
                                    with f:
                                        fav_icon = "★" if recipe['is_favorite'] else "☆"
                                        if st.button(fav_icon, key=f"fav_{recipe['id']}"): db.toggle_favorite(recipe['id'], st.session_state['user_id'], recipe['is_favorite']); st.rerun()
                                    with e:
                                        if st.button("✏️", key=f"edt_{recipe['id']}"): st.session_state['edit_mode_id'] = recipe['id']; st.rerun()
                                    st.caption(f"{recipe['cuisine_type']} | {recipe['dish_type']}")
                                    
                                    with st.expander("내용 보기"):
                                        source_url = recipe.get('source_url') or recipe.get('link') or recipe.get('url')
                                        show_link_card(source_url)
                                        st.markdown(recipe['content'])
                                        if st.button("🗑 삭제", key=f"del_{recipe['id']}"):
                                            db.delete_recipe(recipe['id'], st.session_state['user_id']); st.rerun()

    # --- 메뉴 3: 냉장고를 부탁해 ---
    elif selected == "냉장고를 부탁해":
        st.header("❄️ 냉장고를 부탁해")
        st.caption("냉장고 속 재료를 입력하면, 만들 수 있는 요리를 찾아드려요.")
        with st.container(border=True):
            user_input = st.text_input("재료를 쉼표(,)로 구분해서 입력해주세요.", placeholder="예: 대파, 계란, 스팸")
            if user_input:
                my_recipes = db.get_user_recipes(st.session_state['user_id'])
                results = search_recipes_by_fridge(user_input, my_recipes)
                if results:
                    st.success(f"총 {len(results)}개의 요리를 찾았어요! 🍳")
                    st.divider()
                    for recipe in results:
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1.2])
                            with c1:
                                st.subheader(recipe['title'])
                                tags_html = ""
                                for k in recipe['matched_keywords']:
                                    color = "#FFF3CD" if "(대체" in k else "#D4EDDA"
                                    text_color = "#856404" if "(대체" in k else "#155724"
                                    tags_html += f"<span style='background-color:{color}; color:{text_color}; padding:2px 6px; border-radius:4px; font-size:0.8em; margin-right:4px;'>{k}</span>"
                                st.markdown(f"✅ 포함된 재료: {tags_html}", unsafe_allow_html=True)
                                st.caption(f"{recipe['cuisine_type']} | {recipe['ingredients']}")
                            with c2:
                                st.markdown(f"## ⭐ {recipe['match_score']}점")
                            with st.expander("레시피 바로 보기"):
                                st.markdown(recipe['content'])
                else: st.warning("😓 가지고 계신 재료로 만들 수 있는 저장된 레시피가 없어요.")

    # --- 메뉴 4: 주방 설정 ---
    elif selected == "주방 설정":
        st.header("⚙️ 주방 설정")
        user_info = db.get_user_info(st.session_state['user_id'])
        if user_info:
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image("https://cdn-icons-png.flaticon.com/512/2922/2922510.png", width=100)
                    st.markdown(f"### {user_info['nickname']}"); st.caption(f"Since {user_info['created_at'].split()[0]}")
                with c2:
                    st.subheader("내 정보 수정")
                    with st.form("profile_update"):
                        new_nick = st.text_input("닉네임", value=user_info['nickname'])
                        if st.form_submit_button("정보 업데이트", type="primary"):
                            db.update_user_profile(st.session_state['user_id'], new_nick, user_info['email'], user_info['address'], user_info['birthdate'])
                            st.session_state['user_name'] = new_nick; st.success("정보가 업데이트되었습니다."); time.sleep(1); st.rerun()
            st.markdown("---")
            with st.expander("회원 탈퇴"):
                with st.form("delete_account_form"):
                    del_pw = st.text_input("비밀번호 확인", type="password")
                    if st.form_submit_button("회원 탈퇴 진행"):
                        if db.check_login(user_info['username'], del_pw):
                            db.delete_user_account(user_info['id']); auth.clear_recipe_data()
                            st.session_state['is_logged_in'] = False; st.session_state['user_id'] = None; st.rerun()
                        else: st.error("비밀번호가 일치하지 않습니다.")