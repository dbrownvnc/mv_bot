import streamlit as st
import google.generativeai as genai
import os
import json
import re
import urllib.parse
import time
import random
import requests
from io import BytesIO
from PIL import Image

# --- 페이지 설정 ---
st.set_page_config(page_title="AI MV Director (Immortal Mode)", layout="wide", initial_sidebar_state="collapsed")

# --- 스타일링 (모바일 최적화) ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .scene-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 6px solid #FF4B4B; /* Red for Alert/Active */
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em; 
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- API 키 로드 ---
def get_api_key(key_name):
    if key_name in st.secrets: return st.secrets[key_name]
    elif os.getenv(key_name): return os.getenv(key_name)
    return None

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 (무적 모드)")
    execution_mode = st.radio("실행 방식", ["API 자동 실행", "수동 모드 (복사/붙여넣기)"], index=0)
    
    st.markdown("---")
    hf_token = get_api_key("HF_TOKEN") or st.text_input("Hugging Face Token", type="password")
    
    st.subheader("🤖 기획 모델")
    gemini_model = st.selectbox("Gemini", ["gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05"])

    if st.button("🗑️ 모든 데이터 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 화면 ---
st.title("🎬 AI MV Director")
st.caption("Zombie Engine: 어떤 상황에서도 이미지를 생성합니다.")

with st.expander("📝 주제 입력 및 시작", expanded=True):
    with st.form("main_form"):
        topic = st.text_area("영상 주제", height=80, placeholder="예: 네온사인이 빛나는 미래 서울의 빗속 추격전")
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 1. [기존 유지] Gemini 기획 로직 (v84 Fallback 적용)
# ------------------------------------------------------------------
def clean_json_text(text):
    if not text: return ""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_plan_auto(topic, api_key, model_name):
    if not api_key: return None
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"Create a music video storyboard for '{topic}' in JSON format. 4 scenes."
        response = model.generate_content(prompt)
        return json.loads(clean_json_text(response.text))
    except: return None

# ------------------------------------------------------------------
# 2. [핵심] 무적의 3단계 이미지 생성 (HF -> HF Router -> Pollinations)
# ------------------------------------------------------------------
def generate_image_ultimate(prompt, token):
    """
    모든 실패를 가정하고 최후의 보루(Pollinations)까지 가동하는 무적 함수
    """
    # 1단계: 가장 무난한 HF 모델 (SD v1.5)
    hf_model = "runwayml/stable-diffusion-v1-5"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {"inputs": f"{prompt}, cinematic, 8k", "options": {"wait_for_model": True}}
    
    # HF 시도 (표준 -> 라우터)
    urls = [
        f"https://api-inference.huggingface.co/models/{hf_model}",
        f"https://router.huggingface.co/models/{hf_model}"
    ]
    
    if token: # 토큰이 있을 때만 HF 시도
        for url in urls:
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                if res.status_code == 200:
                    return Image.open(BytesIO(res.content)), "HuggingFace"
            except:
                continue

    # [최후의 보루] Pollinations AI (여기는 404가 없습니다. 무조건 생성됩니다.)
    try:
        st.toast("⚠️ HF 서버 불안정. 무적의 백업 엔진(Pollinations) 가동!")
        safe_prompt = urllib.parse.quote(prompt)
        seed = random.randint(0, 99999)
        # 이 URL은 무조건 이미지를 반환합니다.
        poll_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?seed={seed}&width=1024&height=576&nologo=true"
        res = requests.get(poll_url, timeout=30)
        if res.status_code == 200:
            return Image.open(BytesIO(res.content)), "Pollinations (Backup)"
    except:
        pass

    return None, "모든 엔진 사망"

# ------------------------------------------------------------------
# 3. 메인 실행 및 렌더링
# ------------------------------------------------------------------
if 'plan' not in st.session_state: st.session_state['plan'] = None
if 'imgs' not in st.session_state: st.session_state['imgs'] = {}

if submit_btn:
    key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
    st.session_state['plan'] = generate_plan_auto(topic, key, gemini_model)
    st.session_state['imgs'] = {}

if st.session_state['plan']:
    plan = st.session_state['plan']
    st.divider()
    
    for scene in plan.get('scenes', []):
        scene_num = scene['scene_num']
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        st.write(f"**🎬 Scene {scene_num}**")
        
        # 이미지 영역
        if scene_num in st.session_state['imgs']:
            st.image(st.session_state['imgs'][scene_num], use_container_width=True)
        else:
            if st.button(f"📸 촬영 (무조건 생성)", key=f"btn_{scene_num}"):
                with st.spinner("AI가 어떻게든 그려내고 있습니다..."):
                    img, source = generate_image_ultimate(scene['image_prompt'], hf_token)
                    if img:
                        st.session_state['imgs'][scene_num] = img
                        st.success(f"생성 완료! (엔진: {source})")
                        st.rerun()
                    else:
                        st.error("치명적 오류: 인터넷 연결을 확인하세요.")

        st.write(f"**Action:** {scene['action']}")
        with st.expander("프롬프트 보기"):
            st.code(scene['image_prompt'])
        st.markdown("</div>", unsafe_allow_html=True)
