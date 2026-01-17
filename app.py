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
st.set_page_config(page_title="AI MV Director (Zombie Mode)", layout="wide")

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
    .status-ok { color: green; font-weight: bold; }
    .status-err { color: red; font-weight: bold; }
    .status-warn { color: orange; font-weight: bold; }
    .diagnostic-log {
        font-family: monospace;
        font-size: 0.8em;
        max_height: 200px;
        overflow-y: auto;
        background-color: #f8f9fa;
        padding: 10px;
        border: 1px solid #ddd;
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
    
    # [핵심] 대규모 모델 리스트 (Zombie List)
    st.subheader("🏥 시스템 생존 진단")
    
    # 알려진 모든 Gemini 모델 식별자 (순서: 최신 -> 구형)
    all_known_models = [
        # 2.0 Series (Newest)
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-2.0-flash-exp",
        
        # 1.5 Flash Series (Fast & Cheap)
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-8b",
        
        # 1.5 Pro Series (High Quality)
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro-001",
        "gemini-1.5-pro-002",
        
        # Experimental (Randomly available)
        "gemini-exp-1206",
        "gemini-exp-1121",
        "learnlm-1.5-pro-experimental",
        
        # 1.0 Legacy (Last Resort)
        "gemini-1.0-pro",
        "gemini-1.0-pro-latest",
        "gemini-pro"
    ]
    
    # 세션에 '살아있는 모델' 저장
    if 'alive_models' not in st.session_state:
        st.session_state['alive_models'] = []

    if st.button("🧬 전체 모델 정밀 스캔"):
        if not gemini_key:
            st.error("API Key 필요")
        else:
            genai.configure(api_key=gemini_key)
            alive_list = []
            
            with st.status("🔍 모델 생존 여부 확인 중...", expanded=True) as status:
                st.write("각 모델에 'Hi'를 보내 응답을 확인합니다.")
                
                for m in all_known_models:
                    try:
                        # 최소 토큰으로 핑(Ping) 테스트
                        model = genai.GenerativeModel(m)
                        model.generate_content("Hi", generation_config={"max_output_tokens": 1})
                        
                        st.markdown(f"✅ **{m}**: <span class='status-ok'>생존 (Alive)</span>", unsafe_allow_html=True)
                        alive_list.append(m)
                        
                    except Exception as e:
                        err_msg = str(e)
                        if "429" in err_msg or "Quota" in err_msg:
                            st.markdown(f"⚠️ **{m}**: <span class='status-warn'>한도 초과 (429)</span>", unsafe_allow_html=True)
                        elif "404" in err_msg or "Not Found" in err_msg:
                            # 404는 너무 많으므로 로그 간소화
                            # st.markdown(f"❌ **{m}**: <span class='status-err'>없음 (404)</span>", unsafe_allow_html=True)
                            pass
                        else:
                            st.markdown(f"❌ **{m}**: <span class='status-err'>사망 ({err_msg[:20]}...)</span>", unsafe_allow_html=True)
                
                if alive_list:
                    st.session_state['alive_models'] = alive_list
                    status.update(label=f"스캔 완료! 생존 모델 {len(alive_list)}개 발견", state="complete")
                else:
                    status.update(label="스캔 실패: 생존 모델 0개", state="error")
                    st.error("모든 모델이 응답하지 않습니다. API Key를 점검하세요.")

    # 스캔 결과에 따라 선택박스 업데이트
    final_model_list = st.session_state['alive_models'] if st.session_state['alive_models'] else all_known_models
    
    st.markdown("---")
    st.subheader("🤖 분석 모델 선택")
    gemini_model = st.selectbox(
        "사용할 모델", 
        final_model_list, 
        index=0,
        help="스캔을 돌리면 살아있는 모델만 표시됩니다."
    )
    
    st.markdown("---")
    st.subheader("🎨 이미지 모델")
    image_model = st.selectbox("Pollinations 모델", ["flux", "turbo"], index=0)

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director")
st.caption("Massive Model Scanner Mode | Zombie Fallback")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# ------------------------------------------------------------------
# 1. Gemini 로직 (생존자 우선 투입)
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    
    # 1. 시작 모델 + 스캔된 생존 모델들 + 전체 리스트 (중복 제거)
    # 전략: 사용자가 고른 놈 -> 스캔으로 확인된 산 놈들 -> 나머지 전체
    
    fallback_chain = [start_model]
    
    # 이미 살아있다고 확인된 모델들을 우선 배치 (매우 중요)
    if 'alive_models' in st.session_state and st.session_state['alive_models']:
        for m in st.session_state['alive_models']:
            if m not in fallback_chain:
                fallback_chain.append(m)
    
    # 혹시 모르니 나머지 리스트도 뒤에 붙임 (보험)
    all_backups = [
        "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash-lite-preview-02-05",
        "gemini-1.5-pro", "gemini-1.0-pro"
    ]
    for b in all_backups:
        if b not in fallback_chain:
            fallback_chain.append(b)
            
    last_error = None
    
    # 2. 순차 실행
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            time.sleep(1) 
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            # 실패 시 빠르게 스킵
            time.sleep(0.5)
            continue
            
    raise Exception(f"All models ({len(fallback_chain)} tried) failed. Last Error: {last_error}")

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
        st.toast(f"✅ 기획 완료 (Used: {used_model})")
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
