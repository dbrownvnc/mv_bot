import streamlit as st
import google.generativeai as genai
import os
import json
import re
import urllib.parse
import time
import random

# --- 페이지 설정 ---
st.set_page_config(page_title="AI MV Director (Real-time)", layout="wide")

# --- 스타일링 ---
st.markdown("""
<style>
    .scene-box {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
        border-left: 6px solid #FF4B4B;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .status-badge {
        background-color: #e6f3ff;
        color: #0066cc;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
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
    st.info("💡 팁: 이미지가 안 뜨면 3~4초 기다려보세요. 순차적으로 생성됩니다.")

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Live Mode)")
st.subheader("실시간으로 그려지는 뮤직비디오 스토리보드")

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
    # DeBrief 앱과 동일한 검증된 모델 리스트
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

def get_pollinations_url(prompt):
    # 프롬프트 길이 제한 및 랜덤 시드 적용
    safe_prompt = prompt[:400]
    encoded = urllib.parse.quote(safe_prompt)
    seed = random.randint(0, 999999)
    # turbo 모델 사용 시도 (더 빠르고 제한이 적음) -> 실패하면 flux로 변경 가능
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model=flux&nologo=true&seed={seed}&enhance=false"

# --- 실행 로직 (순차 생성 적용) ---

if st.button("🚀 프로젝트 시작"):
    if not api_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        # 1. 기획안 작성 단계
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            plan_data = generate_plan_gemini(topic, api_key)
            status.update(label="기획안 작성 완료! 스토리보드 생성을 시작합니다.", state="complete", expanded=False)

        if plan_data:
            # 2. 기획 내용 먼저 화면에 표시 (사용자가 읽을 수 있게)
            st.divider()
            st.markdown(f"## 🎥 {plan_data['project_title']}")
            st.info(f"**로그라인:** {plan_data['logline']}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 🎵 Music")
                st.write(plan_data['music']['style'])
                st.code(plan_data['music']['suno_prompt'], language="text")
            with c2:
                st.markdown("### 🎨 Visuals")
                st.write(plan_data['visual_style']['description'])
                st.code(plan_data['visual_style']['character_prompt'], language="text")
            
            st.markdown("---")
            st.subheader("🖼️ 비주얼 스토리보드 제작 (실시간)")
            
            # 3. 씬별 순차 생성 (여기서 하나씩 그리고 표시함)
            
            # 진행바 생성
            progress_bar = st.progress(0)
            total_scenes = len(plan_data['scenes'])
            
            for idx, scene in enumerate(plan_data['scenes']):
                # 컨테이너를 먼저 만들어서 자리를 잡음
                with st.container():
                    st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
                    st.markdown(f"#### 🎬 Scene {scene['scene_num']} <span style='font-size:0.8em; color:gray'>({scene['timecode']})</span>", unsafe_allow_html=True)
                    
                    col_text, col_img = st.columns([1, 1.5])
                    
                    with col_text:
                        st.write(f"**내용:** {scene['action']}")
                        st.write(f"**촬영:** {scene['camera']}")
                        with st.expander("프롬프트 상세"):
                            st.code(scene['image_prompt'], language="text")
                            
                    with col_img:
                        # 이미지 생성 중임을 알리는 스피너
                        with st.spinner(f"Scene {scene['scene_num']} 촬영 중... (잠시만 기다려주세요)"):
                            
                            # 1. 딜레이 (서버 차단 방지 3초)
                            time.sleep(3.0) 
                            
                            # 2. URL 생성
                            full_prompt = f"{plan_data['visual_style']['character_prompt']}, {scene['image_prompt']}"
                            img_url = get_pollinations_url(full_prompt)
                            
                            # 3. 이미지 표시
                            st.image(img_url, use_container_width=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # 진행률 업데이트
                progress_bar.progress((idx + 1) / total_scenes)
            
            st.success("✨ 모든 장면 촬영이 완료되었습니다!")
            st.balloons()
