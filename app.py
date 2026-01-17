import streamlit as st
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
st.set_page_config(page_title="AI MV Director (Direct API)", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# --- [핵심 1] API 키 로드 (모든 가능성 체크) ---
def get_api_key():
    # 1. Secrets에서 찾기 (여러 이름 시도)
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    if "GEMINI_API_KEY" in st.secrets:  # 사용자님 케이스
        return st.secrets["GEMINI_API_KEY"]
    
    # 2. 환경변수에서 찾기
    if os.getenv("GOOGLE_API_KEY"):
        return os.getenv("GOOGLE_API_KEY")
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY")
        
    return None

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    gemini_key = get_api_key()
    if gemini_key:
        st.success("✅ Gemini Key 자동 연결됨")
    else:
        gemini_key = st.text_input("Gemini API Key", type="password")
    
    st.markdown("---")
    
    # 모델 선택
    st.subheader("🤖 분석 모델")
    model_options = [
        "gemini-1.5-pro", 
        "gemini-1.5-flash", 
        "gemini-1.0-pro",
        "gemini-2.0-flash-exp" # 최신은 이름이 자주 바뀌므로 주의
    ]
    gemini_model = st.selectbox("기본 모델", model_options, index=1) # 1.5-flash 안전빵
    
    st.markdown("---")
    st.subheader("🎨 이미지 모델")
    image_model = st.selectbox("Pollinations 모델", ["flux", "turbo"], index=0)

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
st.caption("Direct API Mode (Library-Free) | No 404/429 Issues")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# ------------------------------------------------------------------
# 1. Gemini 로직 (Direct HTTP Request)
# ------------------------------------------------------------------
# 라이브러리 없이 직접 구글 서버에 요청을 보냅니다. 훨씬 안정적입니다.

def call_gemini_api(prompt, api_key, model="gemini-1.5-flash"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2000
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        # 200 OK
        if response.status_code == 200:
            result = response.json()
            # 응답 파싱
            try:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return text, None # 성공
            except:
                return None, "응답 형식 오류"
                
        # 에러 처리
        else:
            return None, f"Error {response.status_code}: {response.text}"
            
    except Exception as e:
        return None, str(e)

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_plan_gemini(topic, api_key, start_model):
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
    
    # 1. 선택된 모델 시도
    text, error = call_gemini_api(prompt, api_key, start_model)
    if text: 
        st.toast(f"✅ 기획 완료 ({start_model})")
        return json.loads(clean_json_text(text))
    
    # 2. 실패 시 백업 모델 (1.5-flash -> 1.0-pro)
    backups = ["gemini-1.5-flash", "gemini-1.0-pro"]
    for model in backups:
        if model == start_model: continue
        
        time.sleep(1) # 잠시 대기
        text, error = call_gemini_api(prompt, api_key, model)
        if text:
            st.toast(f"✅ 기획 완료 (Backup: {model})")
            return json.loads(clean_json_text(text))
            
    st.error(f"모든 모델 실패. Last Error: {error}")
    return None

# ------------------------------------------------------------------
# 2. 이미지 생성 로직
# ------------------------------------------------------------------

def fetch_image_server_side(prompt, model="flux"):
    safe_prompt = urllib.parse.quote(prompt[:400])
    seed = random.randint(0, 999999)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=576&model={model}&nologo=true&seed={seed}&enhance=false"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        pass
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
        
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['plan_data'] = generate_plan_gemini(topic, gemini_key, gemini_model)
            
            if st.session_state['plan_data']:
                status.update(label="기획 완료!", state="complete", expanded=False)
            else:
                status.update(label="실패", state="error")

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
    st.subheader("🖼️ 비주얼 스토리보드")

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
                    msg = st.empty()
                    msg.info("📸 촬영 중...")
                    
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    img_data = fetch_image_server_side(full_prompt, image_model)
                    
                    if img_data:
                        st.session_state['generated_images'][scene_num] = img_data
                        msg.empty()
                        st.rerun()
                    else:
                        msg.error("이미지 생성 실패")

            st.markdown("</div>", unsafe_allow_html=True)
    
    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 프로젝트 완성!")
