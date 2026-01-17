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
st.set_page_config(page_title="AI MV Director (Final v84)", layout="wide")

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
    .regen-btn {
        background-color: #f0f2f6;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# --- API 키 로드 (범용 함수) ---
def get_api_key(key_name):
    # 1. Streamlit Secrets에서 확인
    if key_name in st.secrets:
        return st.secrets[key_name]
    # 2. 환경변수에서 확인
    elif os.getenv(key_name):
        return os.getenv(key_name)
    return None

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 (Final v84)")
    
    # 1. Google Gemini API Key
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")

    # 2. [NEW] Gemini 모델 선택 (DeBrief 앱 방식 적용)
    st.subheader("🧠 기획 모델 (Gemini)")
    gemini_model_options = [
        "gemini-1.5-pro", 
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    selected_gemini_model = st.selectbox(
        "기본 분석 모델", 
        gemini_model_options, 
        index=0
    )

    st.markdown("---")
    
    # 3. Hugging Face Token (이미지 생성용)
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ Hugging Face Token 연결됨")
    else:
        hf_token = st.text_input("Hugging Face Token", type="password", help="Write 권한이 있는 토큰을 입력하세요.")
        st.caption("[👉 토큰 발급받기](https://huggingface.co/settings/tokens)")
    
    # 4. HF 모델 선택
    st.subheader("🎨 화가 모델 (Hugging Face)")
    hf_model_id = st.selectbox(
        "사용할 이미지 모델 ID",
        [
            "black-forest-labs/FLUX.1-dev",     # 1순위
            "black-forest-labs/FLUX.1-schnell", # 2순위
            "stabilityai/stable-diffusion-xl-base-1.0", # 3순위
        ],
        index=0,
        help="FLUX.1-dev가 퀄리티가 가장 좋습니다."
    )

    st.markdown("---")
    if st.button("🗑️ 프로젝트 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Final v84)")
st.subheader("DeBrief급 강력한 기획 엔진 & 고화질 스토리보드")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# --- Gemini 로직 (DeBrief 앱 로직 이식) ---

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

# [핵심] DeBrief 앱의 generate_with_fallback 함수 그대로 적용
def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    
    # 1. 시작 모델을 리스트의 첫 번째로 설정
    fallback_chain = [start_model]
    
    # 2. 백업 모델 리스트 (DeBrief 앱과 동일)
    backups = [
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    
    # 3. 시작 모델과 중복되지 않게 백업 체인 구성
    for b in backups:
        if b != start_model: 
            fallback_chain.append(b)
            
    last_error = None
    
    # 4. 순차적 실행 (상위 모델 실패 시 하위 모델 자동 시도)
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # 성공 시 1초 대기 (안정성 확보)
            time.sleep(1) 
            
            # 텍스트와 성공한 모델명 반환
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            # 실패 시 로그 출력 (디버깅용) 및 잠시 대기 후 다음 모델 시도
            # print(f"⚠️ {model_name} 실패: {e}") 
            time.sleep(0.5)
            continue
            
    # 모든 모델 실패 시 에러 발생
    raise Exception(f"All models failed. Last Error: {last_error}")

def generate_plan_gemini(topic, api_key, selected_model):
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
        # [수정] 사이드바에서 선택한 모델을 시작 모델로 전달
        response_text, used_model = generate_with_fallback(prompt, api_key, selected_model)
        
        # 성공한 모델 정보 표시 (토스트 메시지)
        st.toast(f"✅ 기획 생성 완료 (Used: {used_model})")
        
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 오류: {e}")
        return None

# --- Hugging Face 이미지 생성 함수 (유지) ---
def generate_image_hf(prompt, token, model_id):
    """
    Hugging Face Inference API를 사용하여 이미지를 생성합니다.
    503(모델 로딩) 에러 시 자동 대기 기능을 포함합니다.
    """
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    seed = random.randint(0, 999999) 
    
    payload = {
        "inputs": f"{prompt}, cinematic lighting, 8k, high quality",
        "parameters": {"seed": seed} 
    }

    # 최대 5번 재시도 (모델 깨우기)
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
                print(f"Error: {response.text}")
                break
                
        except Exception as e:
            time.sleep(1)
            
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
        st.warning("Hugging Face Token이 필요합니다.")
    else:
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['generated_images'] = {} 
            # [수정] 선택된 모델을 인자로 전달
            st.session_state['plan_data'] = generate_plan_gemini(topic, gemini_key, selected_gemini_model)
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
                    # 2. 없으면 HF API로 생성 시도
                    if hf_token:
                        with st.spinner("📸 촬영 중..."):
                             full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                             
                             img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                             
                             if img_data:
                                 st.session_state['generated_images'][scene_num] = img_data
                                 st.image(img_data, use_container_width=True)
                             else:
                                 st.error("이미지 생성 실패 (토큰/모델 확인 필요)")
                    else:
                        st.info("토큰을 입력해주세요.")

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
