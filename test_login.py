import streamlit as st
import auth

# 1. 세션 초기화
auth.init_session_state()

# 2. 로그인 상태 체크
if not st.session_state['is_logged_in']:
    # 로그인이 안 되어 있으면 -> 문지기(로그인 화면) 등장
    auth.login_ui()
else:
    # 로그인이 되어 있으면 -> 환영 메시지
    st.title(f"🎉 성공! {st.session_state['user_name']}님 접속 중")
    auth.logout_ui()