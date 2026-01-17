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
st.set_page_config(page_title="AI MV Director (Infinite Retry)", layout="wide")

# --- 스타일링 ---
st.markdown("""
<style>
    .scene-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 6px solid #4285F4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .process-log {
        font-family: monospace;
        font-size: 0.9em;
        color: #0066cc;
        background-color: #f0f7ff;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border: 1px solid #cce5ff;
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
    
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    st.subheader("🤖 분석 모델 (DeBrief Engine)")
    model_options = [
        "gemini-1.5-pro", 
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    gemini_model = st.selectbox("기본 모델", model_options, index=0)
    
    st.markdown("---")
    st.subheader("🎨 이미지 모델")
    image_model = st.selectbox("Pollinations 모델", ["flux", "turbo"], index=0)

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
st.caption("무한 재시도 엔진 탑재 (Never Give Up Mode)")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# ------------------------------------------------------------------
# 1. Gemini 로직 (무한 재시도 적용)
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model):
    """
    쿼터 에러 발생 시 대기 후 재시도하는 강력한 로직
    """
    genai.configure(api_key=api_key)
    
    # 모델 리스트 구성
    backup_models = [
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    fallback_chain = [start_model] + [m for m in backup_models if m != start_model]
    
    log_placeholder = st.empty()
    
    # [핵심] 전체 리스트를 3바퀴까지 돔 (끈질기게 시도)
    max_global_retries = 3 
    
    for attempt in range(max_global_retries):
        for model_name in fallback_chain:
            try:
                msg = f"🔄 <b>{model_name}</b> 연결 시도 중... (Cycle {attempt+1}/{max_global_retries})"
                log_placeholder.markdown(f"<div class='process-log'>{msg}</div>", unsafe_allow_html=True)
                
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                # 성공!
                time.sleep(1)
                log_placeholder.empty()
                return response.text, model_name 
                
            except Exception as e:
                error_str = str(e)
                
                # 429(Quota) 에러일 경우: 멈추지 않고 '대기' 후 계속 진행
                if "429" in error_str or "Quota" in error_str:
                    wait_sec = 10 + (attempt * 5) # 시도할수록 대기시간 늘림 (10초, 15초, 20초...)
                    log_placeholder.markdown(
                        f"<div class='process-log' style='color:#d9534f;'>⚠️ 쿼터 초과! {wait_sec}초 식히는 중...</div>", 
                        unsafe_allow_html=True
                    )
                    time.sleep(wait_sec)
                    continue
                
                # 404나 기타 에러: 빠르게 다음 모델로
                time.sleep(0.5)
                continue
            
    # 여기까지 왔다면 정말 안 되는 상태
    raise Exception(f"모든 모델 재시도 실패. API Key 상태를 확인해주세요.")

# ------------------------------------------------------------------
# 2. 이미지 생성 로직 (서버 사이드 다운로드)
# ------------------------------------------------------------------

def fetch_image_server_side(prompt, model="flux"):
    safe_prompt = urllib.parse.quote(prompt[:400])
    seed = random.randint(0, 999999)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=576&model={model}&nologo=true&seed={seed}&enhance=false"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Image Error: {e}")
    return None

# ------------------------------------------------------------------
# 3. 실행 로직
# ------------------------------------------------------------------

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

start_btn = st.button("🚀 프로젝트 시작")

if start_btn:
    if not gemini_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        st.session_state['generated_images'] = {} 
        st.session_state['plan_data'] = None
        
        with st.status("📝 기획안 작성 중... (최대 1~2분 소요될 수 있습니다)", expanded=True) as status:
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
            
            try:
                raw_text, used_model = generate_with_fallback(prompt, gemini_key, gemini_model)
                st.session_state['plan_data'] = json.loads(clean_json_text(raw_text))
                status.update(label=f"기획 완료! (성공 모델: {used_model})", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"기획안 생성 최종 실패: {e}")

# 결과 표시
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
    st.subheader("🖼️ 비주얼 스토리보드 제작")

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
                    img_placeholder = st.empty()
                    status_placeholder = st.empty()
                    
                    status_placeholder.info(f"📸 Scene {scene_num} 촬영 중... (AI가 그리는 중)")
                    
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    
                    # 이미지 생성
                    img_data = fetch_image_server_side(full_prompt, image_model)
                    
                    if img_data:
                        st.session_state['generated_images'][scene_num] = img_data
                        status_placeholder.empty()
                        img_placeholder.image(img_data, use_container_width=True)
                        time.sleep(0.5) 
                        st.rerun()
                    else:
                        status_placeholder.error("이미지 생성 실패")

            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 모든 촬영이 종료되었습니다!")
