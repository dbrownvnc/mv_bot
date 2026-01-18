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
st.set_page_config(page_title="AI MV Director (Mobile)", layout="wide", initial_sidebar_state="collapsed")

# --- 스타일링 (모바일 최적화) ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
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

# --- 사이드바 (설정) ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 실행 모드 선택
    execution_mode = st.radio(
        "실행 방식",
        ["API 자동 실행", "수동 모드 (무제한)"],
        index=0
    )
    
    st.markdown("---")

    # API 모드일 때만 키 입력 받기
    gemini_key = None
    gemini_model = None
    
    if execution_mode == "API 자동 실행":
        gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
        if gemini_key:
            st.success("✅ Gemini Key 연결됨")
        else:
            gemini_key = st.text_input("Gemini API Key", type="password")
            
        st.caption("사용 모델")
        model_options = [
            "gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", 
            "gemini-1.5-pro", "gemini-1.0-pro", "gemini-flash-latest"
        ]
        gemini_model = st.selectbox("모델 선택", model_options, index=0, label_visibility="collapsed")
    
    st.markdown("---")
    
    # 이미지 생성 설정
    st.subheader("🎨 이미지 생성 설정")
    
    image_provider = st.selectbox(
        "이미지 생성 제공자",
        ["Pollinations AI (무료)", "Hugging Face"],
        index=0
    )
    
    if image_provider == "Pollinations AI (무료)":
        pollinations_model = st.selectbox(
            "Pollinations 모델",
            [
                "flux",
                "flux-realism", 
                "flux-anime",
                "flux-3d",
                "turbo",
                "flux-pro"
            ],
            index=0
        )
        st.caption("✨ Pollinations는 무료이며 API 키가 필요없습니다")
        
        # 이미지 품질 설정
        image_width = st.slider("이미지 너비", 512, 2048, 1024, 128)
        image_height = st.slider("이미지 높이", 512, 2048, 1024, 128)
        
    else:  # Hugging Face
        hf_token = get_api_key("HF_TOKEN")
        if hf_token:
            st.success("✅ HF Token 연결됨")
        else:
            hf_token = st.text_input("Hugging Face Token", type="password")
        
        hf_model_id = st.selectbox(
            "HF 이미지 모델",
            [
                "black-forest-labs/FLUX.1-dev",
                "black-forest-labs/FLUX.1-schnell",
                "stabilityai/stable-diffusion-xl-base-1.0", 
                "runwayml/stable-diffusion-v1-5"
            ],
            index=0
        )

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

with st.expander("📝 프로젝트 설정 (터치하여 열기)", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제를 입력하세요", height=100, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")
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
# 1. API 자동 실행 로직
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
# 2. 향상된 이미지 생성 로직
# ------------------------------------------------------------------

def generate_image_pollinations(prompt, model="flux", width=1024, height=1024, seed=None):
    """
    Pollinations AI를 사용한 이미지 생성 (무료, API 키 불필요)
    """
    try:
        if seed is None:
            seed = random.randint(0, 999999)
        
        # 프롬프트 최적화
        enhanced_prompt = f"{prompt}, cinematic lighting, 8k, high quality, detailed, professional photography"
        
        # URL 인코딩
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        
        # Pollinations API URL
        api_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model}&width={width}&height={height}&seed={seed}&nologo=true"
        
        # 이미지 다운로드
        response = requests.get(api_url, timeout=60)
        
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            st.error(f"Pollinations API 오류: {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"이미지 생성 실패: {e}")
        return None

def generate_image_hf(prompt, token, model_id):
    """
    Hugging Face를 사용한 이미지 생성
    """
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    seed = random.randint(0, 999999) 
    payload = {
        "inputs": f"{prompt}, cinematic lighting, 8k, high quality, detailed", 
        "parameters": {"seed": seed}
    }

    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            elif "estimated_time" in response.json():
                wait_time = response.json().get("estimated_time", 10)
                st.toast(f"😴 모델 깨우는 중... ({wait_time:.1f}초)")
                time.sleep(wait_time + 1)
                continue
            else:
                break
        except Exception as e:
            time.sleep(1)
    return None

# ------------------------------------------------------------------
# 3. 메인 실행 로직
# ------------------------------------------------------------------

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

# A. 실행 버튼 클릭 시 (Auto 모드)
if submit_btn and execution_mode == "API 자동 실행":
    if not gemini_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        st.session_state['generated_images'] = {} 
        st.session_state['plan_data'] = None
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['plan_data'] = generate_plan_auto(topic, gemini_key, gemini_model)
            if st.session_state['plan_data']:
                status.update(label="기획 완료!", state="complete", expanded=False)
            else:
                status.update(label="실패", state="error")

# B. 수동 모드 UI
if execution_mode == "수동 모드 (무제한)":
    st.info("💡 주제를 입력한 후 아래 단계를 따라주세요.")
    
    prompt_to_copy = get_system_prompt(topic) if topic else "주제를 먼저 입력해주세요."
    
    with st.container():
        st.markdown(f"<div class='manual-box'>", unsafe_allow_html=True)
        st.markdown("**1. 프롬프트 복사**")
        st.code(prompt_to_copy, language="text")
        
        c1, c2 = st.columns(2)
        with c1:
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
            # 이미지 생성 버튼
            if st.button(f"📸 촬영 (Scene {scene_num})", key=f"gen_{scene_num}"):
                with st.spinner("🎨 이미지 생성 중..."):
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    
                    img = None
                    if image_provider == "Pollinations AI (무료)":
                        img = generate_image_pollinations(
                            full_prompt, 
                            model=pollinations_model,
                            width=image_width,
                            height=image_height
                        )
                    else:  # Hugging Face
                        if 'hf_token' in locals() and hf_token:
                            img = generate_image_hf(full_prompt, hf_token, hf_model_id)
                        else:
                            st.error("HF 토큰이 필요합니다.")
                    
                    if img:
                        st.session_state['generated_images'][scene_num] = img
                        st.rerun()
                    else:
                        st.error("이미지 생성 실패")

        st.caption(f"⏱️ {scene['timecode']}")
        st.write(f"**Action:** {scene['action']}")
        st.write(f"**Camera:** {scene['camera']}")
        
        with st.expander("Prompt"):
            st.code(scene['image_prompt'], language="text")
            
        st.markdown("</div>", unsafe_allow_html=True)
