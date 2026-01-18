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
st.set_page_config(page_title="AI MV Director (Debug Mode)", layout="wide", initial_sidebar_state="collapsed")

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
        border-left: 5px solid #4285F4;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em; 
        font-weight: bold;
    }
    .manual-box {
        background-color: #f8f9fa;
        border: 2px dashed #FFD700;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
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

    gemini_key = None
    gemini_model = None
    
    if execution_mode == "API 자동 실행":
        gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
        if gemini_key:
            st.success("✅ Gemini Key 연결됨")
        else:
            gemini_key = st.text_input("Gemini API Key", type="password")
            
        model_options = [
            "gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", 
            "gemini-1.5-pro", "gemini-1.0-pro", "gemini-flash-latest"
        ]
        gemini_model = st.selectbox("Gemini 모델", model_options, index=0)
    
    st.markdown("---")
    
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ HF Token 연결됨")
    else:
        hf_token = st.text_input("Hugging Face Token", type="password")
    
    hf_model_id = st.selectbox(
        "이미지 모델",
        [
            "black-forest-labs/FLUX.1-dev",     # 고화질 (Access 필요)
            "black-forest-labs/FLUX.1-schnell", # 고속
            "stabilityai/stable-diffusion-xl-base-1.0", # 안정적
            "runwayml/stable-diffusion-v1-5"    # 매우 빠름
        ],
        index=0
    )

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

# 입력 폼
with st.expander("📝 프로젝트 설정", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제", height=100, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 공통 함수
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def get_system_prompt(topic):
    return f"""
    You are a professional Music Video Director.
    Analyze the following theme: "{topic}"
    Create a detailed plan in JSON format ONLY.
    
    JSON Structure:
    {{
      "project_title": "Creative Title (Korean)",
      "logline": "One sentence concept (Korean)",
      "music": {{
        "style": "Genre and Mood (Korean)",
        "suno_prompt": "English prompt for music AI."
      }},
      "visual_style": {{
        "description": "Visual tone (Korean)",
        "character_prompt": "English description of the main character."
      }},
      "scenes": [
        {{
          "scene_num": 1,
          "timecode": "00:00-00:05",
          "action": "Scene description (Korean)",
          "camera": "Shot type (Korean)",
          "image_prompt": "Highly detailed English prompt for image generation."
        }}
        // Create 4 scenes total
      ]
    }}
    """

# ------------------------------------------------------------------
# 1. API 자동 실행 로직 (Gemini)
# ------------------------------------------------------------------
def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    fallback_chain = [start_model]
    backups = ["gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-flash-8b", "gemini-1.0-pro", "gemini-flash-latest"]
    for b in backups:
        if b != start_model: fallback_chain.append(b)
            
    last_error = None
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            time.sleep(1) 
            return response.text, model_name 
        except Exception as e:
            last_error = e
            time.sleep(0.5)
            continue
    raise Exception(f"All models failed. Last Error: {last_error}")

def generate_plan_auto(topic, api_key, model_name):
    try:
        prompt = get_system_prompt(topic)
        response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
        st.toast(f"✅ 기획 생성 완료 (Used: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# ------------------------------------------------------------------
# 2. [강화된] Hugging Face 이미지 생성 로직 (디버깅용)
# ------------------------------------------------------------------
def generate_image_hf(prompt, token, model_id):
    """
    이미지 생성 함수. 실패 시 (None, 에러메시지)를 반환합니다.
    """
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    seed = random.randint(0, 999999) 
    
    # Payload
    payload = {
        "inputs": f"{prompt}, cinematic lighting, 8k, high quality, detailed",
        "parameters": {"seed": seed}
    }

    # 최대 5번 시도
    for attempt in range(5):
        try:
            # 타임아웃을 60초로 넉넉하게 잡음 (모델 로딩 시간 고려)
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            # 200 OK: 성공
            if response.status_code == 200:
                return Image.open(BytesIO(response.content)), None
            
            # 503 Service Unavailable: 모델 로딩 중 (Estimated Time)
            elif "estimated_time" in response.json():
                wait_time = response.json().get("estimated_time", 20)
                st.toast(f"😴 모델 로딩 중... {wait_time:.1f}초 대기 ({attempt+1}/5)")
                time.sleep(wait_time + 2) # 여유 있게 대기
                continue
            
            # 그 외 에러 (403, 500 등)
            else:
                return None, f"Error {response.status_code}: {response.text}"
                
        except Exception as e:
            time.sleep(1)
            # 마지막 시도였다면 에러 리턴
            if attempt == 4:
                return None, str(e)
            
    return None, "시간 초과: 모델이 응답하지 않습니다."

# ------------------------------------------------------------------
# 3. 메인 실행 로직
# ------------------------------------------------------------------

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

# A. 실행 (API Auto Mode)
if submit_btn and execution_mode == "API 자동 실행":
    if not gemini_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    elif not hf_token:
        st.warning("Hugging Face Token이 필요합니다.")
    else:
        st.session_state['generated_images'] = {} 
        st.session_state['plan_data'] = None
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['plan_data'] = generate_plan_auto(topic, gemini_key, gemini_model)
            if st.session_state['plan_data']:
                status.update(label="기획 완료!", state="complete", expanded=False)
            else:
                status.update(label="실패", state="error")

# B. 실행 (Manual Mode)
if execution_mode == "수동 모드 (무제한)":
    st.info("💡 주제를 입력한 후 아래 단계를 따라주세요.")
    prompt_to_copy = get_system_prompt(topic) if topic else "주제를 먼저 입력해주세요."
    
    with st.container():
        st.markdown(f"<div class='manual-box'>", unsafe_allow_html=True)
        st.markdown("**1. 프롬프트 복사**")
        st.code(prompt_to_copy, language="text")
        st.link_button("🚀 Gemini 열기", "https://gemini.google.com/", use_container_width=True)
        
        st.markdown("**2. 결과 붙여넣기**")
        manual_json_input = st.text_area("JSON 결과", height=150, placeholder="```json\n{\n ... \n}\n```", label_visibility="collapsed")
        
        if st.button("✅ 결과 적용"):
            if not manual_json_input.strip():
                st.warning("결과를 붙여넣어주세요.")
            else:
                try:
                    st.session_state['plan_data'] = json.loads(clean_json_text(manual_json_input))
                    st.session_state['generated_images'] = {} 
                    st.success("로드 완료!")
                except Exception as e:
                    st.error(f"오류: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 4. 결과 표시
# ------------------------------------------------------------------

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    
    st.divider()
    st.subheader(f"🎥 {plan['project_title']}")
    st.info(plan['logline'])
    
    with st.expander("🎵 음악 & 🎨 비주얼 설정", expanded=False):
        st.markdown("**Music:** " + plan['music']['style'])
        st.code(plan['music']['suno_prompt'])
        st.markdown("**Visual:** " + plan['visual_style']['description'])
        st.code(plan['visual_style']['character_prompt'])
    
    st.markdown("### 🖼️ 스토리보드")

    for scene in plan['scenes']:
        scene_num = scene['scene_num']
        
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        st.markdown(f"#### Scene {scene_num}")
        
        if scene_num in st.session_state['generated_images']:
            st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
        else:
            if hf_token:
                if st.button(f"📸 촬영 (Scene {scene_num})", key=f"gen_{scene_num}"):
                    with st.spinner(f"생성 중... ({hf_model_id})"):
                        full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                        
                        # [중요] 에러 메시지까지 받음
                        img, err_msg = generate_image_hf(full_prompt, hf_token, hf_model_id)
                        
                        if img:
                            st.session_state['generated_images'][scene_num] = img
                            st.rerun()
                        else:
                            st.error(f"실패 원인: {err_msg}")
                            # 403 에러면 친절하게 알려줌
                            if "403" in str(err_msg):
                                st.warning("⚠️ HF 사이트에서 약관 동의(Accept License)를 했는지 확인하세요. 동의 후에도 안 되면 토큰을 재발급(Fine-grained 말고 Legacy Write 권한 추천) 받아보세요.")
            else:
                st.warning("HF 토큰 필요")

        st.caption(f"⏱️ {scene['timecode']}")
        st.write(f"**Action:** {scene['action']}")
        
        with st.expander("Prompt"):
            st.code(scene['image_prompt'], language="text")
            
        st.markdown("</div>", unsafe_allow_html=True)
