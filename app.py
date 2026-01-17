import streamlit as st
import os

# --- [핵심] 만능 API 키 로더 ---
def load_api_key():
    api_key = None
    
    # 1. Streamlit Secrets (로컬 .streamlit/secrets.toml 또는 Cloud Secrets) 확인
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
        elif "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    except FileNotFoundError:
        pass # secrets 파일이 없으면 무시하고 넘어감
    except Exception:
        pass
        
    # 2. 시스템 환경 변수 (OS Environment Variable) 확인
    if not api_key:
        if os.getenv("GOOGLE_API_KEY"):
            api_key = os.getenv("GOOGLE_API_KEY")
        elif os.getenv("GEMINI_API_KEY"):
            api_key = os.getenv("GEMINI_API_KEY")
            
    return api_key

# --- 메인 실행부 ---
st.title("🔑 API Key Setup Check")

# 키 로드 시도
gemini_key = load_api_key()

if gemini_key:
    st.success("✅ API Key가 시스템(Secrets 또는 환경변수)에서 감지되었습니다!")
    # 여기에 마스킹된 키 보여주기 (확인용)
    st.code(f"{gemini_key[:5]}**********{gemini_key[-3:]}", language="text")
else:
    st.warning("⚠️ 시스템에 등록된 API Key가 없습니다. 직접 입력해주세요.")
    # 3. 최후의 수단: 화면에서 직접 입력받기
    gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    if not gemini_key:
        st.stop() # 키가 없으면 여기서 코드 중단

# --- 이후 Gemini 호출 로직 ---
import google.generativeai as genai
try:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Hi")
    st.info(f"🤖 테스트 응답 성공: {response.text}")
except Exception as e:
    st.error(f"❌ 연결 실패: {e}")
