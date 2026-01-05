import streamlit as st
import database as db
import re
import time
import datetime
import extra_streamlit_components as stx

# ==========================================
# 🍪 쿠키 관리자 설정
# ==========================================
def get_cookie_manager(key="init"): 
    return stx.CookieManager(key=key)

# ==========================================
# 🛠️ 인증 관련 유틸리티
# ==========================================
def init_session_state():
    if 'is_logged_in' not in st.session_state: st.session_state['is_logged_in'] = False
    if 'user_id' not in st.session_state: st.session_state['user_id'] = None
    if 'user_name' not in st.session_state: st.session_state['user_name'] = None
    if 'auth_mode' not in st.session_state: st.session_state['auth_mode'] = '로그인'
    
    # 중복확인 및 기타
    if 'is_id_checked' not in st.session_state: st.session_state['is_id_checked'] = False
    if 'checked_id_value' not in st.session_state: st.session_state['checked_id_value'] = ""

    # 회원가입 성공 상태 관리
    if 'signup_success' not in st.session_state: st.session_state['signup_success'] = False
    if 'new_user_info' not in st.session_state: st.session_state['new_user_info'] = {}

def clear_recipe_data():
    keys = ['generated_data', 'current_url', 'current_source', 'edit_mode_id']
    for k in keys:
        if k in st.session_state: del st.session_state[k]

def validate_password(password):
    if len(password) < 8: return False, "8자리 이상이어야 합니다."
    if not re.search(r"[a-zA-Z]", password): return False, "영문자가 포함되어야 합니다."
    if not re.search(r"\d", password): return False, "숫자가 포함되어야 합니다."
    return True, "사용 가능한 비밀번호입니다."

# ==========================================
# 🚀 자동 로그인 로직
# ==========================================
def try_auto_login(cookie_manager):
    if st.session_state['is_logged_in']: return

    time.sleep(0.1) 
    token = cookie_manager.get(cookie="lincook_auth_token")
    
    if token:
        user = db.get_user_by_token(token)
        if user:
            st.session_state['is_logged_in'] = True
            st.session_state['user_id'] = user['id']
            st.session_state['user_name'] = user['nickname']
            return True
    return False

# ==========================================
# 🖥️ 화면 UI
# ==========================================

def login_ui():
    st.header("🔐 링쿡 시작하기")
    
    cookie_manager = get_cookie_manager()
    try_auto_login(cookie_manager)
    
    if st.session_state['is_logged_in']:
        st.rerun()

    tab_login, tab_signup, tab_find = st.tabs(["로그인", "회원가입", "계정 찾기"])

    # --- [탭 1] 로그인 ---
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            submit = st.form_submit_button("로그인", type="primary", use_container_width=True)
            
            if submit:
                user = db.check_login(username, password)
                if user:
                    clear_recipe_data()
                    st.session_state['is_logged_in'] = True
                    st.session_state['user_id'] = user['id']
                    st.session_state['user_name'] = user['nickname']
                    
                    token = db.update_auth_token(user['id'])
                    cookie_manager.set("lincook_auth_token", token, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    
                    st.success(f"{user['nickname']}님 환영합니다! 👋")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")

        st.markdown("---")
        st.caption("SNS 계정으로 간편 로그인 (준비 중)")
        c_kakao, c_google = st.columns(2)
        with c_kakao: st.button("🟡 카카오 로그인", use_container_width=True, disabled=True)
        with c_google: st.button("⚪ 구글 로그인", use_container_width=True, disabled=True)

    # --- [탭 2] 회원가입 ---
    with tab_signup:
        if st.session_state['signup_success']:
            new_info = st.session_state['new_user_info']
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f"""
                <div style='text-align: center;'>
                    <h2 style='color: #FF4B4B;'>🎉 회원가입 완료!</h2>
                    <p style='font-size: 16px; color: gray;'>
                        이제 <b>{new_info.get('nickname')}</b>님만의<br>
                        특별한 레시피북을 완성해보세요.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                st.divider()
                col_auto, col_go_login = st.columns(2)
                with col_auto:
                    if st.button("🚀 이 아이디로 로그인", type="primary", use_container_width=True):
                        user = db.check_login(new_info['username'], new_info['password'])
                        if user:
                            clear_recipe_data()
                            st.session_state['is_logged_in'] = True
                            st.session_state['user_id'] = user['id']
                            st.session_state['user_name'] = user['nickname']
                            token = db.update_auth_token(user['id'])
                            cookie_manager.set("lincook_auth_token", token, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                            st.session_state['signup_success'] = False
                            st.session_state['new_user_info'] = {}
                            st.rerun()
                with col_go_login:
                    if st.button("로그인 페이지로 이동", use_container_width=True):
                        st.session_state['signup_success'] = False
                        st.session_state['new_user_info'] = {}
                        st.rerun()

        else:
            st.caption("📝 필수 정보")
            c_id, c_chk = st.columns([3, 1], vertical_alignment="bottom")
            with c_id: new_user = st.text_input("아이디 (4자 이상)", key="signup_id")
            with c_chk: 
                if st.button("중복확인"):
                    if len(new_user) < 4: st.error("너무 짧아요")
                    elif db.is_username_taken(new_user): st.error("사용 중")
                    else: 
                        st.success("가능")
                        st.session_state['is_id_checked'] = True
                        st.session_state['checked_id_value'] = new_user

            if st.session_state['is_id_checked'] and new_user != st.session_state['checked_id_value']:
                 st.warning("아이디가 바뀌었습니다. 다시 중복확인 해주세요.")
                 st.session_state['is_id_checked'] = False

            new_pw = st.text_input("비밀번호 (8자 이상, 영문+숫자)", type="password")
            
            # [수정됨] 비밀번호 에러 메시지가 들어갈 공간을 미리 확보!
            pw_error_placeholder = st.empty()
            
            new_pw_chk = st.text_input("비밀번호 확인", type="password")
            
            # [변경] 이메일 입력 UI
            st.markdown("📧 이메일 (ID/PW 찾기에 사용)")
            c_mail_id, c_at, c_mail_domain = st.columns([3, 0.3, 4], vertical_alignment="bottom")
            
            with c_mail_id:
                email_id_input = st.text_input("이메일 아이디", placeholder="ex) lincook")
            with c_at:
                st.markdown("<h5>@</h5>", unsafe_allow_html=True)
            with c_mail_domain:
                domain_options = ["직접 입력", "naver.com", "gmail.com", "daum.net", "kakao.com", "icloud.com"]
                selected_domain = st.selectbox("도메인 선택", domain_options)
            
            if selected_domain == "직접 입력":
                email_domain_input = st.text_input("도메인 직접 입력", placeholder="ex) company.com")
            else:
                email_domain_input = selected_domain

            new_nickname = st.text_input("닉네임")
            
            with st.expander("🔽 선택 정보 입력 (생년월일, 성별, 주소)"):
                c_birth, c_gender = st.columns(2)
                with c_birth:
                    new_birth = st.date_input("생년월일", value=datetime.date(2000, 1, 1), min_value=datetime.date(1900, 1, 1))
                with c_gender:
                    new_gender = st.radio("성별", ["선택 안 함", "남성", "여성"], horizontal=True)
                new_address = st.text_input("주소")

            agree = st.checkbox("(필수) 이용약관 및 개인정보 처리방침에 동의합니다.")

            if st.button("회원가입 완료", type="primary", use_container_width=True):
                # 1. 검증 로직 실행
                pw_valid, pw_msg = validate_password(new_pw)
                
                # 이메일 조합
                full_email = f"{email_id_input}@{email_domain_input}"

                has_error = False

                # [수정됨] 에러 메시지 처리 순서 중요!
                
                # 1. 비밀번호 유효성 검사 실패 시 -> 아까 만든 placeholder에 표시
                if not pw_valid:
                    pw_error_placeholder.error(pw_msg)
                    has_error = True
                
                # 2. 다른 필수 항목 검사
                if not st.session_state['is_id_checked'] or new_user != st.session_state['checked_id_value']:
                    st.error("아이디 중복확인을 해주세요.")
                    has_error = True
                elif not (new_pw and new_nickname and email_id_input and email_domain_input):
                    st.error("필수 정보를 입력해주세요.")
                    has_error = True
                elif not agree:
                    st.error("약관에 동의해주세요.")
                    has_error = True
                elif new_pw != new_pw_chk:
                    st.error("비밀번호가 일치하지 않습니다.")
                    has_error = True
                elif db.is_nickname_taken(new_nickname):
                    # database.py가 업데이트 되었다면 이 부분 에러 없이 작동합니다!
                    st.error("이미 사용 중인 닉네임입니다.")
                    has_error = True

                # 에러가 하나도 없을 때만 가입 진행
                if not has_error:
                    birth_str = new_birth.strftime("%Y-%m-%d")
                    # add_user 함수도 database.py에 잘 정의되어 있어야 함
                    if db.add_user(new_user, new_pw, new_nickname, "", birth_str, full_email, new_address, new_gender):
                        st.session_state['signup_success'] = True
                        st.session_state['new_user_info'] = {
                            'username': new_user,
                            'password': new_pw,
                            'nickname': new_nickname
                        }
                        st.session_state['is_id_checked'] = False
                        st.rerun()
                    else:
                        st.error("가입 중 오류가 발생했습니다.")

    # --- [탭 3] 계정 찾기 ---
    with tab_find:
        find_mode = st.radio("메뉴 선택", ["아이디 찾기", "비밀번호 재설정"], horizontal=True)
        st.divider()
        
        if find_mode == "아이디 찾기":
            f_email = st.text_input("가입한 이메일 입력")
            if st.button("아이디 찾기"):
                found_id = db.find_username_by_email(f_email)
                if found_id: st.success(f"회원님의 아이디는 **{found_id}** 입니다.")
                else: st.error("해당 이메일로 가입된 계정이 없습니다.")
        
        elif find_mode == "비밀번호 재설정":
            st.caption("아이디와 이메일이 일치해야 합니다.")
            r_id = st.text_input("아이디")
            r_email = st.text_input("이메일")
            r_new_pw = st.text_input("새로운 비밀번호", type="password")
            
            if st.button("비밀번호 변경"):
                if db.reset_password(r_id, r_email, r_new_pw):
                    st.success("비밀번호가 변경되었습니다! 로그인해주세요.")
                else:
                    st.error("정보가 일치하지 않습니다.")

def logout_ui():
    cookie_manager = get_cookie_manager()
    if st.sidebar.button("🚪 로그아웃"):
        if st.session_state['user_id']:
            db.delete_auth_token(st.session_state['user_id']) 
            cookie_manager.delete("lincook_auth_token") 
        
        clear_recipe_data()
        st.session_state['is_logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['user_name'] = None
        st.rerun()