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
    # Secrets에서 HF_TOKEN을 못 찾으면 직접 입력
    hf_token = get_api_key("HF_TOKEN") or st.text_input("Hugging Face Token", type="password")
    
    # [중요] 404 에러 방지를 위한 검증된 모델 리스트
    hf_model_id = st.selectbox(
        "이미지 모델 선택",
        [
            "stabilityai/stable-diffusion-2-1",         # 현재 가장 안정적 (추천)
            "runwayml/stable-diffusion-v1-5",          # 초경량, 높은 성공률
            "black-forest-labs/FLUX.1-schnell",       # 최신 고화질 (간헐적 404 가능성)
            "prompthero/openjourney"                   # 예술적인 화풍
        ],
        index=0
    )
    st.info("💡 404 에러가 계속되면 모델을 바꿔보세요.")

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

with st.expander("📝 프로젝트 설정", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제 입력", height=100, placeholder="예: 비 오는 서울의 밤, 네온사인 거리")
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 1. Gemini 기획 로직 (V84 핵심 엔진 이식)
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
        prompt = f"Music video plan for '{topic}' in JSON format. 4 scenes with Action and Image Prompt."
        response = model.generate_content(prompt)
        return json.loads(clean_json_text(response.text))
    except: return None

# ------------------------------------------------------------------
# 2. [완벽 보완] 이미지 생성 (404 방지 Multi-URL 구조)
# ------------------------------------------------------------------
def generate_image_hf(prompt, token, model_id):
    """
    여러 가지 주소 형식을 시도하여 404 에러를 우회합니다.
    """
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "inputs": f"{prompt}, high quality, detailed, cinematic lighting",
        "options": {"wait_for_model": True}
    }

    # 시도해볼 주소 후보들
    try_urls = [
        f"https://api-inference.huggingface.co/models/{model_id}",
        f"https://router.huggingface.co/models/{model_id}"
    ]

    last_err = ""
    for url in try_urls:
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                return Image.open(BytesIO(response.content)), None
            
            # 모델 로딩 대기 로직
            if response.status_code == 503:
                time.sleep(10) # 10초 대기 후 재시도
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content)), None

            last_err = f"{url} -> {response.status_code}: {response.text[:100]}"
            
        except Exception as e:
            last_err = str(e)
            continue
            
    return None, last_err

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
    st.subheader(f"🎥 {plan.get('project_title', 'MV Project')}")
    
    # 씬 렌더링
    for scene in plan.get('scenes', []):
        scene_num = scene['scene_num']
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        st.write(f"**Scene {scene_num}** ({scene.get('timecode', '00:00')})")
        
        if scene_num in st.session_state['generated_images']:
            st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
        else:
            if st.button(f"📸 이미지 생성 (Scene {scene_num})", key=f"btn_{scene_num}"):
                if not hf_token:
                    st.error("Hugging Face 토큰을 입력해주세요.")
                else:
                    with st.spinner("AI가 그리는 중..."):
                        img, err = generate_image_hf(scene.get('image_prompt', topic), hf_token, hf_model_id)
                        if img:
                            st.session_state['generated_images'][scene_num] = img
                            st.rerun()
                        else:
                            st.error(f"생성 실패: {err}")
                            if "404" in str(err):
                                st.warning("⚠️ 선택한 모델이 현재 API 주소에서 사라졌습니다. 사이드바에서 다른 모델(예: SD 2.1)을 선택해 보세요.")

        st.write(f"**Action:** {scene.get('action', '정보 없음')}")
        st.markdown("</div>", unsafe_allow_html=True)
