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
st.set_page_config(page_title="AI MV Director (Auto-Link)", layout="wide", initial_sidebar_state="collapsed")

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
    
    # 모델 선택
    hf_model_id = st.selectbox(
        "이미지 모델",
        [
            "stabilityai/stable-diffusion-xl-base-1.0", # [추천]
            "runwayml/stable-diffusion-v1-5", 
            "black-forest-labs/FLUX.1-dev", 
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
    if not text: return ""
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
            if not response.text:
                raise Exception("Empty response from Gemini")
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
        
        cleaned_json = clean_json_text(response_text)
        if not cleaned_json:
            raise Exception("JSON 추출 실패 (빈 응답)")
            
        return json.loads(cleaned_json)
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# ------------------------------------------------------------------
# 2. [완벽 해결] Hugging Face 이미지 생성 (Multi-URL Smart Try)
# ------------------------------------------------------------------
def generate_image_hf(prompt, token, model_id):
    """
    여러 API 주소(endpoint)를 순차적으로 시도하여 이미지를 받아옵니다.
    404, 410 에러가 나면 즉시 다음 주소로 넘어갑니다.
    """
    
    # 시도할 주소 목록 (순서 중요: 표준 -> 라우터)
    base_urls = [
        f"https://api-inference.huggingface.co/models/{model_id}", # SDXL 등 대부분
        f"https://router.huggingface.co/models/{model_id}",       # FLUX 등 일부
    ]
    
    headers = {"Authorization": f"Bearer {token}"}
    seed = random.randint(0, 999999) 
    
    payload = {
        "inputs": f"{prompt}, cinematic lighting, 8k, high quality, detailed",
        "parameters": {"seed": seed}
    }

    last_error = None

    # 각 주소에 대해 시도
    for url in base_urls:
        # 주소별로 최대 3번 시도 (로딩 대기 포함)
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                # [성공] 200 OK
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content)), None
                
                # [치명적 에러] 주소 틀림 (404, 410) -> 즉시 다음 URL 시도
                if response.status_code in [404, 410]:
                    last_error = f"Address Failed ({response.status_code})"
                    break # 현재 URL 포기하고 다음 URL 루프로
                
                # [대기 필요] 503 모델 로딩 중
                try:
                    err_json = response.json()
                    if "estimated_time" in err_json:
                        wait_time = err_json.get("estimated_time", 20)
                        st.toast(f"😴 모델 로딩 중... {wait_time:.1f}초 대기")
                        time.sleep(wait_time + 2)
                        continue # 같은 URL 재시도
                except:
                    pass
                
                # 기타 에러 (403 권한 등)
                last_error = f"Error {response.status_code}: {response.text[:100]}"
                break # 다음 URL 시도 (혹시 모르니)

            except Exception as e:
                last_error = str(e)
                time.sleep(1)
    
    return None, f"모든 연결 실패. 마지막 에러: {last_error}"

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
                        
                        img, err_msg = generate_image_hf(full_prompt, hf_token, hf_model_id)
                        
                        if img:
                            st.session_state['generated_images'][scene_num] = img
                            st.rerun()
                        else:
                            st.error(f"실패: {err_msg}")
                            if "403" in str(err_msg):
                                st.warning("⚠️ 약관 동의(Accept License)가 필요한 모델입니다.")
            else:
                st.warning("HF 토큰 필요")

        st.caption(f"⏱️ {scene['timecode']}")
        st.write(f"**Action:** {scene['action']}")
        
        with st.expander("Prompt"):
            st.code(scene['image_prompt'], language="text")
            
        st.markdown("</div>", unsafe_allow_html=True)
