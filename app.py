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
st.set_page_config(page_title="AI MV Director (HF)", layout="wide")

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
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- API 키 로드 ---
def get_api_key(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    elif os.getenv(key_name):
        return os.getenv(key_name)
    return None

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 (Hugging Face)")
    
    # 1. Google Gemini Key
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    # 2. [NEW] Hugging Face Token 입력
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ Hugging Face Token 연결됨")
    else:
        hf_token = st.text_input("Hugging Face Access Token", type="password", help="Hugging Face 설정에서 'Write' 권한으로 발급받으세요.")
        st.markdown("[👉 토큰 발급받기 (무료)](https://huggingface.co/settings/tokens)")

    st.markdown("---")
    
    # 3. 모델 선택
    st.subheader("🎨 화가 모델 (Hugging Face)")
    hf_model_id = st.selectbox(
        "사용할 모델 ID",
        [
            "black-forest-labs/FLUX.1-dev",     # 1순위: 최신 고화질 (추천)
            "black-forest-labs/FLUX.1-schnell", # 2순위: 고속 버전
            "stabilityai/stable-diffusion-xl-base-1.0", # 3순위: 안정적인 SDXL
            "stabilityai/stable-diffusion-3.5-large"  # 4순위: 최신 SD3.5
        ],
        index=0
    )
    
    st.markdown("---")
    if st.button("🗑️ 프로젝트 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Hugging Face Edition)")
st.subheader("끊김 없는 고화질 스토리보드 제작")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# --- Gemini 로직 (문제없는 기존 버전 유지) ---

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model="gemini-1.5-flash"):
    genai.configure(api_key=api_key)
    backups = ["gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.0-pro", "gemini-flash-latest"]
    fallback_chain = [start_model] + [b for b in backups if b != start_model]
    
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
    raise Exception(f"모델 생성 실패: {last_error}")

def generate_plan_gemini(topic, api_key):
    try:
        prompt = f"""
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
        response_text, _ = generate_with_fallback(prompt, api_key, "gemini-1.5-flash")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 오류: {e}")
        return None

# --- [핵심] Hugging Face 이미지 생성 함수 ---
def generate_image_hf(prompt, token, model_id):
    """
    Hugging Face Inference API를 사용하여 이미지를 생성합니다.
    모델 로딩 중(503 에러)일 경우 자동으로 대기 후 재시도합니다.
    """
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 랜덤 시드 추가 (매번 다른 이미지 생성 유도)
    seed = random.randint(0, 999999) 
    
    # payload 설정 (Flux 모델은 inputs 파라미터를 씁니다)
    payload = {
        "inputs": f"{prompt}, high quality, cinematic lighting, 8k",
        "parameters": {"seed": seed} # 시드 적용
    }

    # 최대 5번 재시도 (모델이 'Cold Boot' 상태일 때 깨우기 위함)
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            # 1. 성공 시 이미지 반환
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            
            # 2. 모델 로딩 중 (503) -> 대기 후 재시도
            elif "estimated_time" in response.json():
                wait_time = response.json().get("estimated_time", 10)
                st.toast(f"😴 모델 깨우는 중... ({wait_time:.1f}초 대기)")
                time.sleep(wait_time + 1) # 안전하게 1초 더 대기
                continue
                
            else:
                st.error(f"API Error: {response.text}")
                break
                
        except Exception as e:
            st.error(f"요청 오류: {e}")
            time.sleep(2)
            
    return None

# --- 실행 로직 ---

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

start_btn = st.button("🚀 프로젝트 시작")

if start_btn:
    if not gemini_key or not topic:
        st.warning("Google API Key와 주제를 입력해주세요.")
    elif not hf_token:
        st.warning("Hugging Face Token이 필요합니다. 사이드바에서 입력해주세요.")
    else:
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['generated_images'] = {} 
            st.session_state['plan_data'] = generate_plan_gemini(topic, gemini_key)
            status.update(label="기획안 작성 완료!", state="complete", expanded=False)

# 화면 표시
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
                # 1. 이미지가 있으면 표시
                if scene_num in st.session_state['generated_images']:
                    st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
                else:
                    # 2. 없으면 Hugging Face 생성 시도
                    if hf_token:
                        with st.spinner(f"📸 Hugging Face에서 생성 중... ({hf_model_id})"):
                             full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                             
                             # [핵심] HF API 호출
                             img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                             
                             if img_data:
                                 st.session_state['generated_images'][scene_num] = img_data
                                 st.image(img_data, use_container_width=True)
                             else:
                                 st.error("이미지 생성 실패. 토큰 권한이나 모델 상태를 확인하세요.")
                    else:
                        st.warning("Hugging Face Token을 입력해야 이미지가 보입니다.")

                # 3. 개별 재생성 버튼
                if st.button(f"🔄 다시 그리기", key=f"regen_{scene_num}"):
                     if hf_token:
                        with st.spinner("📸 재촬영 중..."):
                            full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                            img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                            
                            if img_data:
                                st.session_state['generated_images'][scene_num] = img_data
                                st.rerun()
                     else:
                         st.error("Token이 필요합니다.")
            
            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 스토리보드 완성!")
