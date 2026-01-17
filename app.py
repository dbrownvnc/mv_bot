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
        border-left: 6px solid #FF4B4B;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- API 키 로드 ---
def get_api_key():
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    elif os.getenv("GOOGLE_API_KEY"):
        return os.getenv("GOOGLE_API_KEY")
    return None

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 (Final)")
    
    # 1. API Key
    loaded_key = get_api_key()
    if loaded_key:
        st.success("✅ API Key 연결됨")
        api_key = loaded_key
    else:
        api_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    # 2. [NEW] 이미지 서비스 선택 (대안 추가)
    st.subheader("🎨 이미지 서비스 선택")
    image_service = st.selectbox(
        "사용할 서비스",
        ["Pollinations (Flux)", "Pollinations (Turbo)", "Hercai (SDXL)"],
        index=1, # Turbo를 기본값으로 (가장 빠름)
        help="Pollinations가 안 되면 Hercai를 선택하세요."
    )
    
    st.info(f"현재 선택: {image_service}")

    st.markdown("---")
    if st.button("🗑️ 프로젝트 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Final)")
st.subheader("등록 없는 무료 이미지 API & 강력한 다운로드 모드")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# --- Gemini 로직 (유지) ---

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

# --- [핵심 수정] 이미지 직접 다운로드 함수 (브라우저 차단 우회) ---
def fetch_image_from_api(prompt, service_type):
    """
    URL을 주는 게 아니라, 파이썬이 직접 이미지를 다운로드해서 가져옵니다.
    이 방식은 브라우저 차단을 100% 우회합니다.
    """
    safe_prompt = prompt[:400]
    seed = random.randint(0, 999999)
    
    try:
        # 1. Pollinations (Flux/Turbo)
        if "Pollinations" in service_type:
            model = "flux" if "Flux" in service_type else "turbo"
            encoded = urllib.parse.quote(safe_prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model={model}&nologo=true&seed={seed}&enhance=false"
            
            # 파이썬 내부에서 다운로드
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
            
        # 2. Hercai (대안 서비스)
        elif "Hercai" in service_type:
            # Hercai API 호출
            api_url = f"https://hercai.onrender.com/v3/text2image?prompt={urllib.parse.quote(safe_prompt)}"
            response = requests.get(api_url, timeout=30) # Hercai는 조금 느릴 수 있음
            data = response.json()
            
            if "url" in data:
                # 이미지 URL을 받아서 다시 다운로드
                img_response = requests.get(data["url"], timeout=15)
                return Image.open(BytesIO(img_response.content))
            else:
                return None
                
    except Exception as e:
        st.warning(f"이미지 다운로드 실패 ({service_type}): {e}")
        return None

# --- 실행 로직 ---

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} # {scene_num: PIL.Image 객체} 저장

start_btn = st.button("🚀 프로젝트 시작")

if start_btn:
    if not api_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['generated_images'] = {} 
            st.session_state['plan_data'] = generate_plan_gemini(topic, api_key)
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
    st.subheader(f"🖼️ 비주얼 스토리보드 (Service: {image_service})")

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
                    # 2. 없으면 자동 생성 시도 (Python 내부 다운로드 방식)
                    with st.spinner(f"📸 {image_service} 서버에서 이미지 다운로드 중..."):
                         full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                         
                         # [핵심] URL을 주는 게 아니라 이미지를 받아옴
                         img_data = fetch_image_from_api(full_prompt, image_service)
                         
                         if img_data:
                             st.session_state['generated_images'][scene_num] = img_data
                             st.image(img_data, use_container_width=True)
                         else:
                             st.error("이미지 생성 실패. 잠시 후 재생성 버튼을 눌러주세요.")

                # 3. 개별 재생성 버튼
                if st.button(f"🔄 다시 그리기", key=f"regen_{scene_num}"):
                    with st.spinner("📸 재촬영 중..."):
                        full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                        
                        img_data = fetch_image_from_api(full_prompt, image_service)
                        
                        if img_data:
                            st.session_state['generated_images'][scene_num] = img_data
                            st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 스토리보드 완성!")
