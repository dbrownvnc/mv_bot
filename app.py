import streamlit as st
import google.generativeai as genai
import os
import json
import re
import urllib.parse
import time
import random  # [필수] 랜덤 시드 생성을 위해 추가

# --- 페이지 설정 ---
st.set_page_config(page_title="AI MV Director (Free)", layout="wide")

# --- 스타일링 ---
st.markdown("""
<style>
    .scene-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 5px solid #4285F4;
    }
    .prompt-box {
        background-color: #e9ecef;
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
        font-size: 0.85em;
    }
</style>
""", unsafe_allow_html=True)

# --- API 키 로드 함수 ---
def get_api_key():
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    elif os.getenv("GOOGLE_API_KEY"):
        return os.getenv("GOOGLE_API_KEY")
    return None

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 설정 (Free Edition)")
    
    loaded_key = get_api_key()
    
    if loaded_key:
        st.success("✅ API Key가 연결되었습니다.")
        api_key = loaded_key
    else:
        st.warning("API Key가 없습니다.")
        api_key = st.text_input("Google Gemini API Key", type="password")
        st.caption("Google AI Studio에서 무료로 발급받으세요.")
    
    st.markdown("---")
    st.info("이미지 생성: Pollinations.ai (Flux Model)")

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Gemini Edition)")
st.subheader("비용 걱정 없는 무제한 뮤직비디오 기획 툴")

topic = st.text_area("영상 주제 입력", height=80, 
                     placeholder="예: 사이버펑크 서울, 비 오는 네온 거리, 고독한 안드로이드, 몽환적인 분위기")

# --- 헬퍼 함수 ---

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

# [유지] 잘 작동하는 Gemini Fallback 로직
def generate_with_fallback(prompt, api_key, start_model="gemini-1.5-flash"):
    genai.configure(api_key=api_key)
    fallback_chain = [start_model]
    backups = ["gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.0-pro", "gemini-flash-latest"]
    
    for b in backups:
        if b != start_model: fallback_chain.append(b)
    
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
    raise Exception(f"All models failed. Last Error: {last_error}")

def generate_plan_gemini(topic, api_key):
    try:
        prompt = f"""
        You are a professional Music Video Director.
        Analyze the following theme: "{topic}"
        
        Create a detailed plan in JSON format ONLY. Do not write any other text.
        
        JSON Structure:
        {{
          "project_title": "Creative Title (Korean)",
          "logline": "One sentence concept (Korean)",
          "music": {{
            "style": "Genre and Mood (Korean)",
            "suno_prompt": "English prompt for music AI. Include structural tags like [Intro], [Drop]."
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
              "image_prompt": "Highly detailed English prompt for image generation. Keywords: cinematic, 8k, photorealistic."
            }}
            // Create 4 scenes total
          ]
        }}
        """
        response_text, used_model = generate_with_fallback(prompt, api_key, "gemini-1.5-flash")
        json_str = clean_json_text(response_text)
        return json.loads(json_str)
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# [수정됨] 이미지 URL 생성 함수 (안정성 강화)
def get_pollinations_url(prompt):
    """
    Pollinations.ai URL 생성
    - 프롬프트 길이 제한 (URL 에러 방지)
    - 랜덤 시드 추가 (캐싱/중복 요청 방지)
    """
    # 1. 프롬프트가 너무 길면 잘라냄 (URL 길이 제한 방지)
    safe_prompt = prompt[:450] 
    encoded_prompt = urllib.parse.quote(safe_prompt)
    
    # 2. 랜덤 시드 생성 (매번 다른 요청으로 인식하게 함)
    seed = random.randint(0, 999999)
    
    # model=flux (고화질), seed 추가, nologo 추가
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=576&model=flux&nologo=true&seed={seed}&enhance=false"

# --- 실행 로직 ---

if st.button("🚀 무료 생성 시작"):
    if not api_key:
        st.warning("Google API Key가 필요합니다.")
    elif not topic:
        st.warning("주제를 입력해주세요.")
    else:
        with st.status("🎬 작업 진행 중...", expanded=True) as status:
            st.write("🧠 Gemini가 기획안을 작성 중입니다...")
            plan_data = generate_plan_gemini(topic, api_key)
            
            if plan_data:
                st.write("✅ 기획안 완료! 이미지를 생성합니다...")
                status.update(label="작업 완료!", state="complete", expanded=False)
                
                st.divider()
                st.header(f"🎥 {plan_data['project_title']}")
                st.caption(plan_data['logline'])
                
                tab1, tab2 = st.tabs(["📊 기획 상세", "🖼️ 스토리보드"])
                
                with tab1:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("🎵 음악")
                        st.write(f"**스타일:** {plan_data['music']['style']}")
                        st.code(plan_data['music']['suno_prompt'], language="text")
                    with c2:
                        st.subheader("🎨 비주얼")
                        st.write(f"**컨셉:** {plan_data['visual_style']['description']}")
                        st.code(plan_data['visual_style']['character_prompt'], language="text")

                with tab2:
                    # [수정됨] 이미지 생성 루프
                    for scene in plan_data['scenes']:
                        with st.container():
                            st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
                            col1, col2 = st.columns([1, 1.5])
                            with col1:
                                st.subheader(f"Scene {scene['scene_num']}")
                                st.caption(f"⏱ {scene['timecode']}")
                                st.write(f"**내용:** {scene['action']}")
                                st.write(f"**촬영:** {scene['camera']}")
                                with st.expander("프롬프트"):
                                    st.code(scene['image_prompt'], language="text")
                            with col2:
                                # 캐릭터 프롬프트 + 씬 프롬프트 결합
                                full_prompt = f"{plan_data['visual_style']['character_prompt']}, {scene['image_prompt']}"
                                
                                # 이미지 URL 생성
                                img_url = get_pollinations_url(full_prompt)
                                
                                # 이미지 표시
                                st.image(img_url, use_container_width=True)
                                
                                # [핵심] 서버 과부하 방지를 위한 딜레이 (다음 이미지 생성 전 1.5초 대기)
                                time.sleep(1.5)
                                
                            st.markdown("</div>", unsafe_allow_html=True)
