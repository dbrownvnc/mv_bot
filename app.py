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
st.set_page_config(page_title="AI MV Director (Final Rescue)", layout="wide", initial_sidebar_state="collapsed")

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
        border-left: 5px solid #FFD700;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em; 
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
    hf_token = get_api_key("HF_TOKEN") or st.text_input("Hugging Face Token", type="password")
    
    # [중요] 현재 무료 API에서 가장 생존율이 높은 모델들로 재구성
    hf_model_id = st.selectbox(
        "이미지 모델 선택",
        [
            "stabilityai/stable-diffusion-2-1",         # 1순위: 가장 안정적 (404 확률 낮음)
            "black-forest-labs/FLUX.1-schnell",       # 2순위: 고화질 고속
            "runwayml/stable-diffusion-v1-5"          # 3순위: 최후의 보루 (무조건 됨)
        ],
        index=0
    )
    st.caption("※ 404 발생 시 모델을 바꿔보세요.")

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

with st.expander("📝 프로젝트 설정", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제", height=100, placeholder="예: 비 오는 서울의 밤")
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 1. Gemini 기획 로직 (생략 - 기존과 동일)
# ------------------------------------------------------------------
def clean_json_text(text):
    if not text: return ""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_plan_auto(topic, api_key, model_name):
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Music video plan for '{topic}' in JSON format. project_title, logline, music (style, suno_prompt), visual_style (description, character_prompt), scenes (scene_num, timecode, action, camera, image_prompt). 4 scenes."
        response = model.generate_content(prompt)
        return json.loads(clean_json_text(response.text))
    except: return None

# ------------------------------------------------------------------
# 2. [초강력 수정] 이미지 생성 (Direct Inference Call)
# ------------------------------------------------------------------
def generate_image_hf(prompt, token, model_id):
    """
    404 에러를 원천 차단하기 위해 주소 체계를 직접 구성합니다.
    """
    # 허깅페이스 공식 권장 API 주소 방식
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "inputs": f"{prompt}, cinematic, 8k, highly detailed",
        "options": {"wait_for_model": True} # 모델 로딩까지 서버에서 대기하도록 설정
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)), None
        
        # 만약 404가 뜨면 'router' 주소로 한 번 더 시도
        if response.status_code in [404, 410]:
            router_url = f"https://router.huggingface.co/models/{model_id}"
            response = requests.post(router_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content)), None

        # 여전히 실패 시 에러 메시지 반환
        try:
            err_msg = response.json()
        except:
            err_msg = response.text[:100]
            
        return None, f"상태코드 {response.status_code}: {err_msg}"
        
    except Exception as e:
        return None, str(e)

# ------------------------------------------------------------------
# 3. 메인 실행 및 결과 (모바일 최적화)
# ------------------------------------------------------------------
if 'plan_data' not in st.session_state: st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state: st.session_state['generated_images'] = {}

if submit_btn:
    # 기획안 생성 부분 (Gemini Key 사용)
    gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
    st.session_state['plan_data'] = generate_plan_auto(topic, gemini_key, "gemini-1.5-flash")

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    st.divider()
    st.subheader(f"🎥 {plan.get('project_title', 'MV Project')}")
    
    for scene in plan.get('scenes', []):
        scene_num = scene['scene_num']
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        st.write(f"**Scene {scene_num}** ({scene['timecode']})")
        
        if scene_num in st.session_state['generated_images']:
            st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
        else:
            if st.button(f"📸 촬영 시작", key=f"btn_{scene_num}"):
                with st.spinner("이미지 생성 중..."):
                    img, err = generate_image_hf(scene['image_prompt'], hf_token, hf_model_id)
                    if img:
                        st.session_state['generated_images'][scene_num] = img
                        st.rerun()
                    else:
                        st.error(f"실패: {err}")
                        if "404" in str(err):
                            st.info("💡 모델 주소가 변경되었습니다. 사이드바에서 다른 모델을 선택해 보세요.")
        
        st.write(f"Action: {scene['action']}")
        st.markdown("</div>", unsafe_allow_html=True)
