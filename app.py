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

# --- 스타일링 ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .scene-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #2ECC71; /* 성공 시 초록색 */
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
    st.header("⚙️ 설정")
    execution_mode = st.radio("실행 방식", ["API 자동 실행", "수동 모드 (무제한)"], index=0)
    st.markdown("---")

    gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
    hf_token = get_api_key("HF_TOKEN") or st.text_input("Hugging Face Token", type="password")
    
    hf_model_id = st.selectbox(
        "이미지 모델 (1순위)",
        ["stabilityai/stable-diffusion-xl-base-1.0", "runwayml/stable-diffusion-v1-5", "black-forest-labs/FLUX.1-dev"],
        index=0
    )
    st.info("💡 HF 엔진이 404 에러를 내면 자동으로 '무적의 응급 복구 엔진'이 가동됩니다.")

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

with st.expander("📝 프로젝트 설정", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제", height=100, placeholder="예: 비 오는 서울의 밤, 네온사인 거리")
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 공통 함수 및 Gemini 로직
# ------------------------------------------------------------------
def clean_json_text(text):
    if not text: return ""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def get_system_prompt(topic):
    return f"Music video plan for '{topic}' in JSON format. 4 scenes. output JSON only."

def generate_plan_auto(topic, api_key):
    if not api_key: return None
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(get_system_prompt(topic))
        return json.loads(clean_json_text(response.text))
    except: return None

# ------------------------------------------------------------------
# [핵심] 무적의 이미지 생성 로직 (Multi-Engine)
# ------------------------------------------------------------------

def fetch_pollinations_image(prompt):
    """최후의 보루: 토큰 없이 99% 성공하는 엔진"""
    try:
        safe_prompt = urllib.parse.quote(prompt)
        seed = random.randint(0, 99999)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?seed={seed}&width=1024&height=576&nologo=true"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            return Image.open(BytesIO(res.content))
    except:
        return None
    return None

def generate_image_robust(prompt, token, model_id):
    """1순위 HF 시도 -> 실패 시 Pollinations AI로 긴급 복구"""
    
    # 1. Hugging Face 시도 (사용자 선택 모델)
    urls = [
        f"https://router.huggingface.co/models/{model_id}",
        f"https://api-inference.huggingface.co/models/{model_id}"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt, "options": {"wait_for_model": True}}

    for url in urls:
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                return Image.open(BytesIO(res.content)), "HuggingFace"
        except:
            continue

    # 2. [긴급 복구] HF가 모두 실패(404 등)했을 때 가동
    st.toast("⚠️ HF 엔진 실패. 응급 복구 엔진(Pollinations)을 가동합니다...")
    img = fetch_pollinations_image(prompt)
    if img:
        return img, "Emergency Rescue Engine"
    
    return None, "모든 엔진 실패"

# ------------------------------------------------------------------
# 메인 실행 로직
# ------------------------------------------------------------------
if 'plan_data' not in st.session_state: st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state: st.session_state['generated_images'] = {}

if submit_btn:
    with st.spinner("기획안 작성 중..."):
        st.session_state['plan_data'] = generate_plan_auto(topic, gemini_key)
        st.session_state['generated_images'] = {}

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    st.divider()
    st.subheader(f"🎥 {plan.get('project_title', 'MV Project')}")
    
    for scene in plan.get('scenes', []):
        num = scene['scene_num']
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        st.write(f"**Scene {num}**")
        
        if num in st.session_state['generated_images']:
            st.image(st.session_state['generated_images'][num], use_container_width=True)
        else:
            if st.button(f"📸 이미지 생성 (Scene {num})", key=f"gen_{num}"):
                with st.spinner("이미지 생성 중..."):
                    img_prompt = scene.get('image_prompt', topic)
                    img, engine_name = generate_image_robust(img_prompt, hf_token, hf_model_id)
                    if img:
                        st.session_state['generated_images'][num] = img
                        st.success(f"생성 완료! (사용한 엔진: {engine_name})")
                        st.rerun()
                    else:
                        st.error("모든 이미지 엔진이 응답하지 않습니다.")

        st.write(f"**Action:** {scene.get('action', '')}")
        st.markdown("</div>", unsafe_allow_html=True)
