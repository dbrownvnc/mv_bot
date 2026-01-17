import streamlit as st
import google.generativeai as genai
import os
import json
import re
import urllib.parse
import time
import random

# --- 페이지 설정 ---
st.set_page_config(page_title="AI MV Director (Stable)", layout="wide")

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
    .status-text {
        color: #666;
        font-size: 0.9em;
        font-style: italic;
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
    st.header("⚙️ 설정 (Free Edition)")
    loaded_key = get_api_key()
    if loaded_key:
        st.success("✅ API Key 연결됨")
        api_key = loaded_key
    else:
        api_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    st.info("💡 팁: 이미지가 생성되는 동안 '새로고침'을 하지 마세요.")
    
    # [추가] 초기화 버튼 (새로운 주제로 다시 시작하고 싶을 때)
    if st.button("🔄 프로젝트 초기화 (Reset)"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Stable Mode)")
st.subheader("끊김 없는 뮤직비디오 스토리보드 제작")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# --- [유지] Gemini 기획안 생성 함수 (수정 없음) ---

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model="gemini-1.5-flash"):
    genai.configure(api_key=api_key)
    backups = [
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
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

# --- [수정] 이미지 URL 생성 함수 (안정성 강화) ---
def get_pollinations_url(prompt):
    safe_prompt = prompt[:400]
    encoded = urllib.parse.quote(safe_prompt)
    seed = random.randint(0, 999999) # 매번 새로운 시드
    # width/height를 16:9 비율(1024x576)로 고정
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model=flux&nologo=true&seed={seed}&enhance=false"

# --- 실행 로직 (세션 상태 적용으로 해결) ---

# 1. 세션 변수 초기화 (새로고침해도 데이터 유지)
if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} # {scene_num: url} 저장

start_btn = st.button("🚀 프로젝트 시작")

if start_btn:
    if not api_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        # 기획안이 없거나 새로운 주제로 시작할 때
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['generated_images'] = {} # 이미지 초기화
            st.session_state['plan_data'] = generate_plan_gemini(topic, api_key)
            status.update(label="기획안 작성 완료!", state="complete", expanded=False)

# 2. 기획안이 존재하면 화면 표시 (여기서부터는 버튼 안 눌러도 유지됨)
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

    # 3. 씬별 표시 및 이미지 순차 생성
    for scene in plan['scenes']:
        scene_num = scene['scene_num']
        
        # 씬별 UI 박스 생성
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
                # A. 이미 생성된 이미지가 있으면 바로 보여줌 (저장된 URL 사용)
                if scene_num in st.session_state['generated_images']:
                    st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
                    st.success("✅ 생성 완료")
                
                # B. 아직 생성 안 됐으면 지금 생성 (실시간)
                else:
                    status_placeholder = st.empty()
                    status_placeholder.info("📸 촬영 중... (AI가 그리는 중)")
                    
                    # 서버 차단 방지를 위한 3초 대기
                    time.sleep(3.0)
                    
                    # 이미지 URL 생성
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    img_url = get_pollinations_url(full_prompt)
                    
                    # 세션에 저장 (중요!)
                    st.session_state['generated_images'][scene_num] = img_url
                    
                    # 화면 표시
                    status_placeholder.empty() # "촬영 중" 메시지 삭제
                    st.image(img_url, use_container_width=True)
                    
                    # 다음 장면으로 자연스럽게 넘어가기 위해 리런 (선택사항이나 안정성을 위해 추천)
                    time.sleep(0.5)
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

    # 모든 이미지가 다 생성되었으면 축하 메시지
    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 모든 장면의 촬영이 완료되었습니다!")
        st.balloons()
