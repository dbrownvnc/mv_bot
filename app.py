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
st.set_page_config(page_title="AI MV Director (Diagnostic)", layout="wide")

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
    .diagnostic-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        font-family: monospace;
        font-size: 0.85em;
        margin-bottom: 20px;
        border: 1px solid #ccc;
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
    
    # [NEW] API 키 진단 도구
    st.subheader("🛠️ 문제 해결 도구")
    if st.button("🔑 API 키 진단 및 테스트"):
        if not gemini_key:
            st.error("API Key를 먼저 입력하세요.")
        else:
            try:
                genai.configure(api_key=gemini_key)
                # 1. 모델 리스트 조회
                st.write("📡 Google 서버 접속 중...")
                models = list(genai.list_models())
                
                # 'generateContent' 기능을 지원하는 모델만 필터링
                available_models = []
                for m in models:
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                
                if available_models:
                    st.success("✅ API Key 유효함 (접속 성공)")
                    st.markdown("⬇️ **내 키로 사용 가능한 모델 목록:**")
                    st.code("\n".join(available_models))
                    
                    # 2. 간단한 테스트 생성
                    test_model = available_models[0]
                    st.write(f"🧪 '{test_model}' 모델로 테스트 생성 시도...")
                    m = genai.GenerativeModel(test_model)
                    res = m.generate_content("Hello, AI.")
                    st.info(f"응답 성공: {res.text}")
                else:
                    st.warning("⚠️ 접속은 됐는데, 텍스트 생성 가능한 모델이 없습니다. (권한 문제)")
                    
            except Exception as e:
                st.error(f"❌ API Key 문제 발생:\n{e}")
                st.caption("Tip: 키가 만료되었거나, 'Generative Language API'가 활성화되지 않았을 수 있습니다.")

    st.markdown("---")
    
    # 모델 선택 (진단 결과에 따라 유연하게 선택 가능)
    st.subheader("🤖 분석 모델")
    model_options = [
        "gemini-1.5-pro", 
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    gemini_model = st.selectbox("기본 분석 모델", model_options, index=2) # 1.5-flash 기본
    
    st.markdown("---")
    st.subheader("🎨 이미지 모델")
    image_model = st.selectbox("Pollinations 모델", ["flux", "turbo"], index=0)

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
st.caption("System Diagnostic Mode | Smart Fallback")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# ------------------------------------------------------------------
# 1. Gemini 로직 (스마트 폴백 - 진단 결과 반영 가능)
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    
    # 1. 우선순위 리스트 구성
    fallback_chain = [start_model]
    backups = [
        "gemini-1.5-flash",        # 가장 안전
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash-8b", 
        "gemini-1.0-pro", 
        "gemini-flash-latest"
    ]
    
    for b in backups:
        if b != start_model: fallback_chain.append(b)
            
    last_error = None
    
    # 2. 순차 실행 (UI 간섭 없이 빠름)
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            time.sleep(1) 
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            # 404(모델 없음)나 400(Bad Request)는 즉시 다음으로
            # 429(Quota)는 어쩔 수 없이 넘김 (대기해도 무료 티어는 바로 안 풀림)
            time.sleep(0.5)
            continue
    
    # [최후의 수단] 하드코딩 모델이 다 실패하면, '사용 가능한 모델'을 동적으로 찾아서 시도
    try:
        print("하드코딩 모델 실패. 동적 모델 탐색 시도...")
        all_models = genai.list_models()
        for m in all_models:
            if 'generateContent' in m.supported_generation_methods:
                # 찾은 모델로 마지막 시도
                model = genai.GenerativeModel(m.name)
                response = model.generate_content(prompt)
                return response.text, m.name
    except:
        pass

    raise Exception(f"모든 모델 실패. (API Key 권한을 확인하세요). Last Error: {last_error}")

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
        st.toast(f"✅ 기획 생성 완료 (Used: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
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
