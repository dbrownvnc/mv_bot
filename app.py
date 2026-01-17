import streamlit as st
import google.generativeai as genai
import os
import json
import re
import urllib.parse
import time
import random

# --- 페이지 설정 ---
st.set_page_config(page_title="AI MV Director (Turbo)", layout="wide")

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
    /* 재생성 버튼 스타일 강조 */
    .regen-btn {
        background-color: #f0f2f6;
        color: #333;
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
    
    # 1. API Key
    loaded_key = get_api_key()
    if loaded_key:
        st.success("✅ API Key 연결됨")
        api_key = loaded_key
    else:
        api_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    # 2. [수정됨] 이미지 모델 선택 (Turbo 기본)
    st.subheader("🎨 화가 모델 선택")
    
    # 리스트 순서를 바꿔서 turbo가 0번(기본)이 되도록 함
    model_options = ["turbo", "flux", "midjourney", "anime", "3d-render"]
    image_model = st.selectbox(
        "사용할 모델",
        model_options,
        index=0, # 0번 인덱스인 'turbo'가 기본값
        help="Turbo: 무제한/빠름, Flux: 고화질/느림"
    )
    
    if image_model == "turbo":
        st.success("⚡ Turbo 모드: 속도가 빠르고 제한이 없습니다.")
    elif image_model == "flux":
        st.info("ℹ️ Flux 모드: 고화질이지만 요청 제한이 걸릴 수 있습니다.")

    st.markdown("---")
    
    # 3. [추가됨] 모델 변경 즉시 적용 버튼
    if st.button("🔄 선택한 모델로 전체 다시 그리기"):
        # 생성된 이미지 기록만 날리고 화면 갱신 -> 다시 그리게 유도
        st.session_state['generated_images'] = {}
        st.rerun()

    st.markdown("---")
    if st.button("🗑️ 프로젝트 완전 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Turbo)")
st.subheader("초고속 스토리보드 제작 & 모델 즉시 변경")

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

# --- 이미지 URL 생성 (모델 적용) ---
def get_pollinations_url(prompt, model_name):
    safe_prompt = prompt[:450]
    encoded = urllib.parse.quote(safe_prompt)
    seed = random.randint(0, 9999999)
    
    # 사용자가 선택한 model_name을 URL에 반영
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model={model_name}&nologo=true&seed={seed}&enhance=false"

# --- 실행 로직 ---

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

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
    st.subheader(f"🖼️ 비주얼 스토리보드 (현재 모델: {image_model})")

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
                # 1. 이미지 표시 (이미 있으면 보여줌)
                if scene_num in st.session_state['generated_images']:
                    st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
                else:
                    # 없으면 자동 생성 (Turbo는 빠르므로 바로 생성)
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    img_url = get_pollinations_url(full_prompt, image_model)
                    st.session_state['generated_images'][scene_num] = img_url
                    st.image(img_url, use_container_width=True)

                # 2. 개별 재생성 버튼 (현재 선택된 모델 적용)
                if st.button(f"🔄 {image_model} 모델로 다시 그리기", key=f"regen_{scene_num}"):
                    with st.spinner("📸 다시 촬영 중..."):
                        full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                        
                        # [핵심] 현재 사이드바에 선택된 image_model을 사용하여 URL 재생성
                        new_url = get_pollinations_url(full_prompt, image_model)
                        
                        st.session_state['generated_images'][scene_num] = new_url
                        st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 스토리보드 완성!")
