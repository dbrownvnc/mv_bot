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
st.set_page_config(page_title="AI MV Director (Final)", layout="wide")

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
    st.header("⚙️ 설정 (Final Edition)")
    
    # 1. Google Gemini API Key
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    # 2. Hugging Face Token (이미지 생성용)
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ Hugging Face Token 연결됨")
    else:
        hf_token = st.text_input("Hugging Face Token", type="password", help="Write 권한이 있는 토큰을 입력하세요.")
        st.caption("[👉 토큰 발급받기](https://huggingface.co/settings/tokens)")
    
    st.markdown("---")
    
    # 3. 모델 선택 (Hugging Face 모델 ID)
    st.subheader("🎨 화가 모델 선택")
    
    hf_model_id = st.selectbox(
        "사용할 모델 ID",
        [
            "black-forest-labs/FLUX.1-dev",     # 1순위: 최신 고화질 (추천)
            "black-forest-labs/FLUX.1-schnell", # 2순위: 고속 버전
            "stabilityai/stable-diffusion-xl-base-1.0", # 3순위: 안정적인 SDXL
        ],
        index=0,
        help="FLUX.1-dev가 퀄리티가 가장 좋습니다."
    )

    st.markdown("---")
    if st.button("🗑️ 프로젝트 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Final)")
st.subheader("끊김 없는 고화질 스토리보드 & 쿼터 자동 우회")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# --- Gemini 로직 (쿼터 에러 자동 우회 적용) ---

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model="gemini-2.0-flash"):
    genai.configure(api_key=api_key)
    
    # [전략]
    # 1. 최신 모델(2.0 등)을 먼저 시도
    # 2. 429(쿼터 초과) 발생 시, 무료 한도가 넉넉한 1.5 Flash 계열로 즉시 전환
    # 3. 그래도 안 되면 구버전 1.0 Pro 시도
    
    fallback_chain = [
        start_model,               # 1순위: 지정된 모델 (예: 최신 버전)
        "gemini-1.5-flash",        # 2순위: [추천] 무료 쿼터가 가장 넉넉함 (하루 1500회 이상)
        "gemini-1.5-flash-8b",     # 3순위: 더 가볍고 빠른 모델
        "gemini-1.5-pro",          # 4순위: 성능은 좋으나 쿼터가 적을 수 있음
        "gemini-1.0-pro"           # 5순위: 최후의 보루 (구버전)
    ]
    
    # 중복 모델 제거 로직
    seen = set()
    unique_chain = []
    for m in fallback_chain:
        if m not in seen and m: # 빈 문자열 제외
            unique_chain.append(m)
            seen.add(m)

    last_error = None
    
    for model_name in unique_chain:
        try:
            # 모델 생성 시도
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # 성공 시 약간의 대기 후 반환 (연속 호출 방지)
            time.sleep(1) 
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            # 429(Quota) 에러가 떴을 때 로그 출력 후 즉시 다음 모델로
            if "429" in error_str or "Quota" in error_str:
                print(f"⚠️ {model_name} 모델 쿼터 초과(429). 즉시 대안 모델로 전환합니다.")
                # st.toast(f"⚠️ {model_name} 한도 초과 -> 다음 모델로 자동 전환") 
                time.sleep(0.5)
                continue
            
            # 그 외 에러(404 등)도 다음 모델 시도
            time.sleep(0.5)
            continue
            
    # 모든 모델 실패 시
    raise Exception(f"모든 모델이 실패했습니다. (마지막 에러: {last_error})\n다른 구글 계정의 키를 사용하거나 잠시 후 시도해주세요.")

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
        response_text, _ = generate_with_fallback(prompt, api_key, "gemini-2.0-flash")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 오류: {e}")
        return None

# --- Hugging Face 이미지 생성 함수 (API 호출 방식) ---
def generate_image_hf(prompt, token, model_id):
    """
    Hugging Face Inference API를 사용하여 이미지를 생성합니다.
    503(모델 로딩) 에러 시 자동 대기 기능을 포함합니다.
    """
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    seed = random.randint(0, 999999) 
    
    # Flux 모델 등에 맞는 Payload
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
                # 에러 발생 시 로그 출력 (디버깅용)
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
                    # 2. 없으면 HF API로 생성 시도
                    if hf_token:
                        with st.spinner("📸 촬영 중..."):
                             full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                             
                             # HF API 호출
                             img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                             
                             if img_data:
                                 st.session_state['generated_images'][scene_num] = img_data
                                 st.image(img_data, use_container_width=True)
                             else:
                                 st.error("이미지 생성 실패 (토큰 권한 확인)")
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
