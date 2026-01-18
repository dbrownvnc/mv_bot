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
st.set_page_config(page_title="AI MV Director (No-Fail Mode)", layout="wide", initial_sidebar_state="collapsed")

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
        border-left: 5px solid #2ECC71; /* Success Green */
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

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 설정")
    execution_mode = st.radio("실행 방식", ["API 자동 실행", "수동 모드 (무제한)"], index=0)
    
    st.markdown("---")
    hf_token = get_api_key("HF_TOKEN") or st.text_input("Hugging Face Token", type="password")
    
    st.info("💡 이 버전은 HF 실패 시 '긴급 복구 엔진'을 가동하여 어떻게든 이미지를 생성합니다.")

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

with st.expander("📝 프로젝트 설정", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제 입력", height=100, placeholder="예: 미래 지향적인 사이버펑크 도시의 밤")
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 1. 기획 로직 (Gemini)
# ------------------------------------------------------------------
def clean_json_text(text):
    if not text: return ""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_plan_auto(topic, api_key):
    if not api_key: return None
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Music video plan for '{topic}' in JSON format. 4 scenes. output JSON only."
        response = model.generate_content(prompt)
        return json.loads(clean_json_text(response.text))
    except: return None

# ------------------------------------------------------------------
# 2. [최후의 보루] 응급 복구 이미지 생성 엔진
# ------------------------------------------------------------------
def fetch_emergency_image(prompt):
    """
    HF가 죽었을 때 사용하는 무적의 엔진 (Pollinations AI)
    API Key가 필요 없고 404가 거의 없습니다.
    """
    try:
        safe_prompt = urllib.parse.quote(prompt)
        seed = random.randint(0, 99999)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?seed={seed}&width=1024&height=576&nologo=true"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        return None
    return None

def generate_image_smart(prompt, token):
    """
    1순위로 HF(안정모델) 시도, 실패 시 2순위 긴급 엔진 가동
    """
    # 1순위: 가장 가볍고 404 안 뜨는 HF 모델
    model_id = "runwayml/stable-diffusion-v1-5"
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt, "options": {"wait_for_model": True}}

    try:
        # HF 시도
        res = requests.post(api_url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            return Image.open(BytesIO(res.content)), "HuggingFace (SD 1.5)"
        
        # 503(로딩 중)일 때만 한 번 더 대기
        if res.status_code == 503:
            time.sleep(5)
            res = requests.post(api_url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                return Image.open(BytesIO(res.content)), "HuggingFace (SD 1.5)"
    except:
        pass

    # [긴급 가동] HF가 404이거나 에러 나면 즉시 무인증 엔진으로 전환
    st.toast("⚠️ HF 엔진 응답 없음. 긴급 복구 엔진 가동...")
    img = fetch_emergency_image(prompt)
    if img:
        return img, "Emergency Rescue Engine"
    
    return None, "모든 엔진 작동 불가"

# ------------------------------------------------------------------
# 3. 메인 실행 및 결과 표시
# ------------------------------------------------------------------
if 'plan_data' not in st.session_state: st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state: st.session_state['generated_images'] = {}

if submit_btn:
    gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
    with st.spinner("기획안 작성 중..."):
        st.session_state['plan_data'] = generate_plan_auto(topic, gemini_key)
        st.session_state['generated_images'] = {}

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    st.divider()
    st.subheader(f"🎥 {plan.get('project_title', 'Project')}")
    
    for scene in plan.get('scenes', []):
        num = scene['scene_num']
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        st.write(f"**Scene {num}**")
        
        if num in st.session_state['generated_images']:
            st.image(st.session_state['generated_images'][num], use_container_width=True)
        else:
            if st.button(f"📸 촬영 (Scene {num})", key=f"btn_{num}"):
                with st.spinner("이미지 생성 중..."):
                    prompt = scene.get('image_prompt', topic)
                    img, engine_name = generate_image_smart(prompt, hf_token)
                    if img:
                        st.session_state['generated_images'][num] = img
                        st.success(f"생성 완료! (Engine: {engine_name})")
                        st.rerun()
                    else:
                        st.error("이미지 생성에 완전히 실패했습니다. 인터넷 연결을 확인하세요.")

        st.write(f"**Action:** {scene.get('action', '')}")
        st.markdown("</div>", unsafe_allow_html=True)
