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
st.set_page_config(page_title="AI MV Director (Final v84 Replica)", layout="wide")

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
    .process-log {
        font-family: monospace;
        font-size: 0.85em;
        color: #555;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 4px;
        margin-top: 5px;
        border-left: 3px solid #ccc;
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
    st.header("⚙️ 설정")
    
    # 1. Gemini Key
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")

    # 2. 모델 선택 (app_final_v84.py에 포함된 모델들 위주로 구성)
    st.subheader("🤖 분석 모델 (DeBrief Engine)")
    
    # app_final_v84.py에서 확인된 모델 리스트
    gemini_model_options = [
        "gemini-1.5-pro", 
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    selected_gemini_model = st.selectbox(
        "시작 모델 선택", 
        gemini_model_options, 
        index=0
    )

    st.markdown("---")
    
    # 3. HF Token & Model
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ Hugging Face Token 연결됨")
    else:
        hf_token = st.text_input("Hugging Face Token", type="password", help="Write 권한 필요")
        st.caption("[👉 토큰 발급](https://huggingface.co/settings/tokens)")
    
    st.subheader("🎨 화가 모델 (Hugging Face)")
    hf_model_id = st.selectbox(
        "사용할 이미지 모델",
        [
            "black-forest-labs/FLUX.1-dev",     
            "black-forest-labs/FLUX.1-schnell", 
            "stabilityai/stable-diffusion-xl-base-1.0",
        ],
        index=0
    )

    st.markdown("---")
    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
st.caption("DeBrief v84 Gemini Engine | Hugging Face Image Gen")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# ------------------------------------------------------------------
# [핵심] app_final_v84.py의 Gemini 로직 (100% 동일하게 이식)
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model):
    """
    app_final_v84.py의 generate_with_fallback 함수 원본 로직입니다.
    상위 모델 실패 시 backups 리스트에 있는 모델들을 순차적으로 시도합니다.
    """
    genai.configure(api_key=api_key)
    
    # 1. 시작 모델 설정
    fallback_chain = [start_model]
    
    # 2. 백업 모델 리스트 (원본 코드와 100% 동일)
    backups = [
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    
    # 3. 체인 구성 (중복 방지)
    for b in backups:
        if b != start_model: 
            fallback_chain.append(b)
            
    last_error = None
    
    # UI에 진행 상황을 보여주기 위한 placeholder
    log_placeholder = st.empty()
    
    # 4. 순차적 실행 (원본 로직: try-except, sleep 시간 등)
    for model_name in fallback_chain:
        try:
            # 진행 로그 표시
            log_placeholder.markdown(f"<div class='process-log'>🔄 <b>{model_name}</b> 모델로 시도 중...</div>", unsafe_allow_html=True)
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # 원본 코드: time.sleep(1)
            time.sleep(1) 
            
            # 성공 시 로그 지우고 반환
            log_placeholder.empty()
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            # 원본 코드: time.sleep(0.5)
            time.sleep(0.5)
            # 실패 로그 남기기 (디버깅용)
            print(f"Failed {model_name}: {e}")
            continue
            
    # 모든 모델 실패 시 에러 발생
    # 여기서 1.0-pro 등의 에러가 최종적으로 잡힙니다.
    raise Exception(f"All models failed. Last Error: {last_error}")

def generate_plan_gemini(topic, api_key, model_name):
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
        # 폴백 함수 호출
        response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
        
        st.toast(f"✅ 기획 생성 성공! (Used: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# ------------------------------------------------------------------
# [유지] Hugging Face 이미지 생성 (이전 요청사항 유지)
# ------------------------------------------------------------------

def generate_image_hf(prompt, token, model_id):
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    seed = random.randint(0, 999999) 
    
    payload = {
        "inputs": f"{prompt}, cinematic lighting, 8k, high quality",
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
# 실행 로직
# ------------------------------------------------------------------

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

start_btn = st.button("🚀 프로젝트 시작")

if start_btn:
    if not gemini_key or not topic:
        st.warning("Google API Key와 주제를 입력해주세요.")
    elif not hf_token:
        st.warning("Hugging Face Token이 필요합니다.")
    else:
        # [단계 1] 기획안 생성
        st.session_state['generated_images'] = {} 
        st.session_state['plan_data'] = None
        
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            # 선택된 모델로 시작하여 폴백 로직 수행
            st.session_state['plan_data'] = generate_plan_gemini(topic, gemini_key, selected_gemini_model)
            status.update(label="기획안 작성 완료!", state="complete", expanded=False)

# [단계 2] 결과 표시 및 이미지 생성
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
    st.subheader(f"🖼️ 비주얼 스토리보드 (Image Model: {hf_model_id.split('/')[-1]})")

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
                else:
                    if hf_token:
                        # 이미지 생성 중임을 알림
                        with st.spinner(f"📸 Scene {scene_num} 촬영 중..."):
                             full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                             img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                             
                             if img_data:
                                 st.session_state['generated_images'][scene_num] = img_data
                                 st.image(img_data, use_container_width=True)
                             else:
                                 st.error("이미지 생성 실패")
                    else:
                        st.info("토큰 필요")

                if st.button(f"🔄 다시 그리기", key=f"regen_{scene_num}"):
                     if hf_token:
                        with st.spinner("📸 재촬영 중..."):
                            full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                            img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                            if img_data:
                                st.session_state['generated_images'][scene_num] = img_data
                                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 스토리보드 완성!")
