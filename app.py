# app.py 상단 수정 제안

# ... import 구문들 ...

# --- API 키 로드 함수 (수정됨) ---
def get_api_key():
    # 1. Streamlit Cloud의 비밀 저장소(Secrets)에서 먼저 찾음
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    # 2. 없으면 로컬 환경변수
    elif os.getenv("GOOGLE_API_KEY"):
        return os.getenv("GOOGLE_API_KEY")
    return None

# 사이드바 설정 부분
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 키 자동 로드 시도
    api_key = get_api_key()
    
    if api_key:
        st.success("✅ 서버에 등록된 API Key 사용 중")
    else:
        # 키가 없으면 수동 입력창 표시
        api_key = st.text_input("Google Gemini API Key", type="password")