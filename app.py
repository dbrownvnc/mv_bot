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
st.set_page_config(page_title="AI MV Director (Exact Replica)", layout="wide")

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
    
    # Gemini Key
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    # [핵심] 첨부파일 Line 446과 100% 동일한 모델 리스트
    st.subheader("🤖 분석 모델 (DeBrief Engine)")
    model_options = [
        "gemini-1.5-pro", 
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    gemini_model = st.selectbox("기본 모델", model_options, index=0) # 기본값: 1.5-pro
    
    st.markdown("---")
    st.subheader("🎨 이미지 모델")
    image_model = st.selectbox("Pollinations 모델", ["flux", "turbo"], index=0)

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
st.caption("DeBrief 엔진 (Exact Ver.) | 실시간 생성 프로세스")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# ------------------------------------------------------------------
# 1. Gemini 로직 (첨부파일 generate_with_fallback 완벽 이식)
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

# [핵심] 첨부파일 Line 229 ~ 243 로직 복원
def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    
    # 1. 시작 모델 설정
    fallback_chain = [start_model]
    
    # 2. 첨부파일 Line 232의 backups 리스트 (정확히 일치시킴)
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
    log_placeholder = st.empty() # 진행 상황 표시용 (UI 추가)
    
    # 4. 순차 실행
    for model_name in fallback_chain:
        try:
            log_placeholder.markdown(f"<div class='process-log'>🔄 {model_name} 모델로 생성 시도 중...</div>", unsafe_allow_html=True)
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            time.sleep(1) # 첨부파일 Line 237 (1초 대기)
            log_placeholder.empty()
            
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            # 실패 시 로그 찍고 잠시 대기
            time.sleep(0.5) # 첨부파일 Line 241 (0.5초 대기)
            continue
            
    # 모든 모델 실패 시
    raise Exception(f"All models failed. Last Error: {last_error}")

# ------------------------------------------------------------------
# 2. 이미지 생성 로직 (서버 사이드 다운로드 유지)
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
        # [단계 1] 기획안 생성
        st.session_state['generated_images'] = {} 
        st.session_state['plan_data'] = None
        
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
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
                # [수정] 첨부파일과 동일한 함수 호출
                raw_text, used_model = generate_with_fallback(prompt, gemini_key, gemini_model)
                st.session_state['plan_data'] = json.loads(clean_json_text(raw_text))
                status.update(label=f"기획 완료! (모델: {used_model})", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"기획안 생성 실패: {e}")

# [단계 2] 결과 표시
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

    # [단계 3] 씬별 순차적 생성
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
