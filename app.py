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
st.set_page_config(page_title="AI MV Director (Speed Ver)", layout="wide")

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
    
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    # [첨부파일과 동일] 기본 모델 선택
    st.subheader("🤖 분석 모델")
    model_options = [
        "gemini-1.5-pro", 
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    # 속도를 위해 1.5-flash를 기본으로 추천하지만, 선택은 자유입니다.
    gemini_model = st.selectbox("기본 모델", model_options, index=2) 
    
    st.markdown("---")
    st.subheader("🎨 이미지 모델")
    image_model = st.selectbox("Pollinations 모델", ["flux", "turbo"], index=0)

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
st.caption("DeBrief Engine (Fast-Fail Mode) | 고속 생성")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# ------------------------------------------------------------------
# 1. Gemini 로직 (첨부파일의 'Fast Fail' 로직 완벽 복원)
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    
    # 1. 시작 모델 설정
    fallback_chain = [start_model]
    
    # 2. 백업 모델 리스트 (첨부파일 app_final_v84.py와 동일)
    backups = [
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    
    # 체인 구성
    for b in backups:
        if b != start_model: 
            fallback_chain.append(b)
            
    last_error = None
    log_placeholder = st.empty()
    
    # [핵심 수정] 무한 루프 제거 -> 한 번씩만 빠르게 시도하고 넘어가기 (속도 최적화)
    for model_name in fallback_chain:
        try:
            # 로그 표시 (사용자가 진행상황 인지)
            log_placeholder.markdown(f"<div class='process-log'>⚡ <b>{model_name}</b> 연결 중...</div>", unsafe_allow_html=True)
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # 성공 시 즉시 반환 (불필요한 대기 제거)
            log_placeholder.empty()
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            # [속도 핵심] 실패 시 대기 시간을 0.5초로 최소화
            # 안 되는 모델 붙잡고 있지 않고 바로 다음 타자로 넘김
            time.sleep(0.5)
            continue
            
    # 모든 모델이 실패했을 때만 에러 발생
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
        response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
        st.toast(f"✅ 기획 생성 완료! (Used: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# ------------------------------------------------------------------
# 2. 이미지 생성 로직 (서버 사이드 다운로드 - 안정성 유지)
# ------------------------------------------------------------------

def fetch_image_server_side(prompt, model="flux"):
    safe_prompt = urllib.parse.quote(prompt[:400])
    seed = random.randint(0, 999999)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=576&model={model}&nologo=true&seed={seed}&enhance=false"
    
    try:
        response = requests.get(url, timeout=15) # 타임아웃 적절히 설정
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Image Error: {e}")
    return None

# ------------------------------------------------------------------
# 3. 실행 로직 (실시간 시각화 유지)
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
        
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            # 기획안 생성 호출
            st.session_state['plan_data'] = generate_plan_gemini(topic, gemini_key, gemini_model)
            
            if st.session_state['plan_data']:
                status.update(label="기획 완료! 비주얼 생성을 시작합니다.", state="complete", expanded=False)
            else:
                status.update(label="기획 실패", state="error")

# 결과 표시 및 순차적 이미지 생성
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

    # 씬 루프
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
                    # 실시간 생성 과정 보여주기
                    status_placeholder = st.empty()
                    img_placeholder = st.empty()
                    
                    status_placeholder.info(f"📸 Scene {scene_num} 촬영 중...")
                    
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    
                    # 이미지 생성 요청
                    img_data = fetch_image_server_side(full_prompt, image_model)
                    
                    if img_data:
                        st.session_state['generated_images'][scene_num] = img_data
                        status_placeholder.empty()
                        img_placeholder.image(img_data, use_container_width=True)
                        time.sleep(0.1) # 아주 짧은 대기 후 바로 리런 (속도감 향상)
                        st.rerun()
                    else:
                        status_placeholder.error("이미지 생성 실패")

            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 모든 촬영이 종료되었습니다!")
