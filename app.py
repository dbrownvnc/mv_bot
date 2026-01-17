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
st.set_page_config(page_title="AI MV Director (HF + Manual)", layout="wide")

# --- 스타일링 ---
st.markdown("""
<style>
    .scene-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 6px solid #FFD700; /* HF Yellow */
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .manual-box {
        background-color: #f8f9fa;
        border: 2px dashed #FFD700;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
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
    
    # [설정] 실행 모드 선택
    st.subheader("🚀 실행 모드")
    execution_mode = st.radio(
        "방식을 선택하세요",
        ["API 자동 실행 (편리함)", "수동 프롬프트 생성 (무제한)"],
        index=0,
        help="API 한도가 찼거나 오류가 날 때는 '수동'을 선택하세요."
    )
    
    st.markdown("---")

    # API 모드일 때만 키 입력 받기
    gemini_key = None
    gemini_model = None
    
    if execution_mode == "API 자동 실행 (편리함)":
        gemini_key = get_api_key("GOOGLE_API_KEY")
        if not gemini_key:
            gemini_key = get_api_key("GEMINI_API_KEY")
            
        if gemini_key:
            st.success("✅ Gemini Key 연결됨")
        else:
            gemini_key = st.text_input("Gemini API Key", type="password")
            
        st.subheader("🤖 분석 모델")
        model_options = [
            "gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", 
            "gemini-1.5-pro", "gemini-1.0-pro", "gemini-flash-latest"
        ]
        gemini_model = st.selectbox("기본 모델", model_options, index=0)
    else:
        st.info("💡 수동 모드는 API Key가 필요 없습니다.")
    
    st.markdown("---")
    
    # [수정됨] HF 토큰은 이미지 생성용이라 항상 필요 (Secrets 우선)
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ HF Token 연결됨")
    else:
        hf_token = st.text_input("Hugging Face Token", type="password", help="Write 권한이 있는 토큰 필요")
    
    st.subheader("🎨 이미지 모델")
    hf_model_id = st.selectbox(
        "사용할 이미지 모델",
        [
            "black-forest-labs/FLUX.1-dev",     # 고화질 (추천)
            "black-forest-labs/FLUX.1-schnell", # 고속
            "stabilityai/stable-diffusion-xl-base-1.0", 
            "runwayml/stable-diffusion-v1-5"
        ],
        index=0
    )

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
if execution_mode == "API 자동 실행 (편리함)":
    st.caption("Auto Mode | Gemini API + Hugging Face")
else:
    st.caption("Manual Mode | No Quota Limit | Manual Prompting")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

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
# 2. [수정됨] Hugging Face 이미지 생성 로직
# ------------------------------------------------------------------
def generate_image_hf(prompt, token, model_id):
    """
    Hugging Face Inference API를 사용하여 이미지를 생성합니다.
    모델 로딩 시간(Cold Start)을 고려하여 재시도 로직이 포함되어 있습니다.
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
            
            # 모델 로딩 중일 때 (503)
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

# A. 모드에 따른 시작 버튼 동작
if execution_mode == "API 자동 실행 (편리함)":
    if st.button("🚀 프로젝트 시작 (Auto)"):
        if not gemini_key or not topic:
            st.warning("API Key와 주제를 입력해주세요.")
        # HF 토큰 체크 추가
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

else: # 수동 모드 로직
    st.markdown("### 🛠️ 수동 모드 가이드")
    st.info("API 오류가 나거나 키가 없을 때 사용하는 '무적 모드'입니다.")
    
    prompt_to_copy = get_system_prompt(topic) if topic else "주제를 먼저 입력해주세요."
    
    with st.container():
        st.markdown(f"<div class='manual-box'>", unsafe_allow_html=True)
        st.markdown("**1단계: 아래 프롬프트를 복사하세요.**")
        st.code(prompt_to_copy, language="text")
        
        st.markdown("**2단계: 버튼을 눌러 Gemini 웹사이트를 엽니다.**")
        st.link_button("🚀 Google Gemini 열기 (새창)", "https://gemini.google.com/")
        
        st.markdown("**3단계: Gemini의 답변(JSON)을 아래에 붙여넣고 '적용'을 누르세요.**")
        manual_json_input = st.text_area("JSON 결과 붙여넣기", height=200, placeholder="```json\n{\n  \"project_title\": ... \n}\n```")
        
        if st.button("✅ 결과 적용 및 스토리보드 생성"):
            if not manual_json_input.strip():
                st.warning("결과를 붙여넣어주세요.")
            else:
                try:
                    st.session_state['plan_data'] = json.loads(clean_json_text(manual_json_input))
                    st.session_state['generated_images'] = {} 
                    st.success("기획안이 로드되었습니다! 아래에서 이미지를 생성합니다.")
                except Exception as e:
                    st.error(f"JSON 형식 오류: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 4. 결과 표시 및 이미지 생성 (공통)
# ------------------------------------------------------------------

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    
    st.divider()
    st.markdown(f"## 🎥 {plan['project_title']}")
    st.info(f"**로그라인:** {plan['logline']}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎵 Music")
        st.write(plan['music']['style'])
        st.code(plan['music']['suno_prompt'], language="text")
    with c2:
        st.markdown("### 🎨 Visuals")
        st.write(plan['visual_style']['description'])
        st.code(plan['visual_style']['character_prompt'], language="text")
    
    st.markdown("---")
    st.subheader(f"🖼️ 비주얼 스토리보드 (Model: {hf_model_id.split('/')[-1]})")

    for scene in plan['scenes']:
        scene_num = scene['scene_num']
        
        with st.container():
            st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
            st.markdown(f"#### 🎬 Scene {scene_num} <span style='font-size:0.8em; color:gray'>({scene['timecode']})</span>", unsafe_allow_html=True)
            
            col_text, col_img = st.columns([1, 1.5])
            
            with col_text:
                st.write(f"**내용:** {scene['action']}")
                st.write(f"**촬영:** {scene['camera']}")
                with st.expander("프롬프트 상세"):
                    st.code(scene['image_prompt'], language="text")
            
            with col_img:
                if scene_num in st.session_state['generated_images']:
                    st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
                    st.success("✅ 생성 완료")
                else:
                    # Hugging Face 이미지 생성
                    if st.button(f"📸 촬영 (HF)", key=f"gen_hf_{scene_num}"):
                        if hf_token:
                            with st.spinner(f"생성 중... ({hf_model_id})"):
                                full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                                img = generate_image_hf(full_prompt, hf_token, hf_model_id) 
                                if img:
                                    st.session_state['generated_images'][scene_num] = img
                                    st.rerun()
                                else:
                                    st.error("생성 실패 (잠시 후 다시 시도하세요)")
                        else:
                            st.warning("HF 토큰이 필요합니다.")
                    
                    # 다시 그리기 (이미지 있을 때)
                    if scene_num in st.session_state['generated_images']:
                         if st.button(f"🔄 재생성", key=f"regen_{scene_num}"):
                            # 로직 동일
                            pass

            st.markdown("</div>", unsafe_allow_html=True)
    
    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 프로젝트 완성!")
