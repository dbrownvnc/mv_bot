import streamlit as st
import google.generativeai as genai
import os
import json
import re
import urllib.parse
import time
import random
import requests  # [필수] 서버 사이드 다운로드를 위해 추가
from io import BytesIO

# --- 페이지 설정 ---
st.set_page_config(page_title="AI MV Director (Pro)", layout="wide")

# --- 스타일링 ---
st.markdown("""
<style>
    .scene-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 30px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .stSpinner > div {
        border-top-color: #FF4B4B !important;
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
    st.header("⚙️ 설정 (Pro Edition)")
    loaded_key = get_api_key()
    if loaded_key:
        st.success("✅ API Key 연결됨")
        api_key = loaded_key
    else:
        api_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    st.info("ℹ️ 이미지를 서버에서 직접 다운로드하여 표시합니다. 생성 속도가 조금 걸릴 수 있으나 안정적입니다.")

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Stability Ver.)")
st.caption("서버 사이드 렌더링을 통한 무중단 스토리보드 생성기")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# --- 함수 모음 ---

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model="gemini-1.5-flash"):
    genai.configure(api_key=api_key)
    backups = [
        "gemini-1.5-flash",
        "gemini-2.0-flash", 
        "gemini-1.5-pro", 
        "gemini-1.0-pro"
    ]
    
    fallback_chain = []
    if start_model in backups: fallback_chain.append(start_model)
    for b in backups:
        if b != start_model: fallback_chain.append(b)
    
    last_error = None
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name 
        except Exception as e:
            last_error = e
            time.sleep(1)
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
        response_text, _ = generate_with_fallback(prompt, api_key)
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 오류: {e}")
        return None

def get_pollinations_url(prompt):
    safe_prompt = prompt[:400]
    encoded = urllib.parse.quote(safe_prompt)
    seed = random.randint(0, 999999)
    # 모델을 'flux'로 지정 (고화질)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model=flux&nologo=true&seed={seed}&enhance=false"

# [핵심 해결책] 이미지를 직접 다운로드 받는 함수 (재시도 로직 포함)
def download_image_with_retry(url, retries=3):
    for attempt in range(retries):
        try:
            # 1. 서버에 이미지 요청 (타임아웃 20초)
            response = requests.get(url, timeout=20)
            
            # 2. 성공 시 바이너리 데이터 반환
            if response.status_code == 200:
                return BytesIO(response.content)
            else:
                # 429(Too Many Requests)나 500 에러 시 대기 후 재시도
                time.sleep(3)
        except Exception as e:
            time.sleep(3)
            
    return None # 3번 다 실패하면 None 반환

# --- 실행 로직 ---

if st.button("🚀 프로젝트 시작"):
    if not api_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        # 1. 기획안 작성
        with st.status("📝 AI 감독이 기획안을 작성 중입니다...", expanded=True) as status:
            plan_data = generate_plan_gemini(topic, api_key)
            status.update(label="기획안 작성 완료! 스토리보드 촬영을 시작합니다.", state="complete", expanded=False)

        if plan_data:
            # 2. 텍스트 기획안 표시
            st.divider()
            st.markdown(f"## 🎥 {plan_data['project_title']}")
            st.caption(f"Logline: {plan_data['logline']}")
            
            with st.expander("🎵 음악 및 캐릭터 설정 보기", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Music Style**")
                    st.info(plan_data['music']['style'])
                    st.code(plan_data['music']['suno_prompt'], language="text")
                with c2:
                    st.markdown("**Visual Tone**")
                    st.info(plan_data['visual_style']['description'])
                    st.code(plan_data['visual_style']['character_prompt'], language="text")
            
            st.markdown("### 🖼️ 비주얼 스토리보드 (순차 생성 중)")
            
            # 3. 씬별 순차 생성 루프
            progress_container = st.empty() # 진행바 위치 예약
            total_scenes = len(plan_data['scenes'])
            
            for idx, scene in enumerate(plan_data['scenes']):
                # 진행률 표시
                progress_container.progress((idx) / total_scenes, text=f"Scene {scene['scene_num']} 생성 중...")
                
                with st.container():
                    st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
                    
                    # 제목 먼저 표시
                    st.subheader(f"🎬 Scene {scene['scene_num']}")
                    
                    col_text, col_img = st.columns([1, 1.5])
                    
                    with col_text:
                        st.markdown(f"**⏱ Time:** `{scene['timecode']}`")
                        st.markdown(f"**📝 Action:** {scene['action']}")
                        st.markdown(f"**🎥 Camera:** {scene['camera']}")
                        with st.expander("프롬프트 확인"):
                            st.code(scene['image_prompt'], language="text")
                    
                    with col_img:
                        # 이미지 생성 프로세스
                        status_msg = st.empty()
                        status_msg.info("⏳ 이미지 생성 요청 중... (약 5~10초 소요)")
                        
                        full_prompt = f"{plan_data['visual_style']['character_prompt']}, {scene['image_prompt']}"
                        img_url = get_pollinations_url(full_prompt)
                        
                        # [여기서 다운로드 시도]
                        img_data = download_image_with_retry(img_url)
                        
                        if img_data:
                            status_msg.empty() # 로딩 메시지 삭제
                            st.image(img_data, use_container_width=True)
                        else:
                            status_msg.error("이미지 생성 실패 (서버 과부하). 다시 시도해주세요.")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # 다음 씬으로 넘어가기 전 안전 딜레이 (서버 밴 방지)
                time.sleep(2) 
            
            progress_container.progress(1.0, text="✨ 모든 작업이 완료되었습니다!")
            st.success("프로젝트 생성 완료!")
