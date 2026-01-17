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
st.set_page_config(page_title="AI MV Director (Final Fixed)", layout="wide")

# --- 스타일링 ---
st.markdown("""
<style>
    .scene-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 6px solid #FFD700; /* HF Yellow */
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
    .status-badge {
        font-size: 0.8em;
        background-color: #f0f2f6;
        padding: 4px 8px;
        border-radius: 4px;
        color: #555;
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
    st.header("⚙️ 설정 (Final Fixed)")
    
    # 1. Gemini Key
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key 연결됨")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")

    # 2. [수정됨] Gemini 모델 선택 (안정적인 모델을 기본값으로)
    st.subheader("🧠 기획 모델 (Gemini)")
    
    # 에러가 난 2.5/2.0 버전보다, 쿼터가 넉넉한 1.5-flash를 0번 인덱스(기본)로 설정
    gemini_options = [
        "gemini-1.5-flash",        # [추천] 하루 1,500회 무료 (가장 안전)
        "gemini-2.0-flash-lite-preview-02-05", # 최신 (하루 50회 제한 가능성)
        "gemini-1.5-pro",          # 고성능 (하루 50회 제한)
        "gemini-1.5-flash-8b",     # 초경량
    ]
    selected_gemini_model = st.selectbox(
        "기본 분석 모델", 
        gemini_options, 
        index=0, # 1.5-flash를 기본으로 설정하여 429 에러 방지
        help="429 에러가 뜨면 1.5-flash를 선택하세요."
    )

    st.markdown("---")
    
    # 3. HF Token & Model
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ Hugging Face Token 연결됨")
    else:
        hf_token = st.text_input("Hugging Face Token", type="password")
        st.caption("[👉 토큰 발급](https://huggingface.co/settings/tokens)")
    
    st.subheader("🎨 화가 모델 (Hugging Face)")
    hf_model_id = st.selectbox(
        "사용할 이미지 모델",
        [
            "black-forest-labs/FLUX.1-dev",     
            "black-forest-labs/FLUX.1-schnell", 
            "stabilityai/stable-diffusion-xl-base-1.0",
        ],
        index=0
    )

    st.markdown("---")
    if st.button("🗑️ 프로젝트 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 타이틀 ---
st.title("🎬 AI MV Director (Final Fixed)")
st.subheader("쿼터 걱정 없는 안정적 기획 & 고화질 스토리보드")

topic = st.text_area("영상 주제 입력", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")

# --- Gemini 로직 (429 에러 완벽 대응) ---

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
    
    # 2. 백업 모델 리스트 (쿼터가 넉넉한 순서로 배치)
    # 429 에러 발생 시 즉시 1.5-flash로 넘어가도록 설계
    backups = [
        "gemini-1.5-flash",        # [핵심] 가장 쿼터가 많음 (구원투수)
        "gemini-1.5-flash-8b",     # 경량화 모델
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.0-pro"           
    ]
    
    # 중복 제거 및 체인 구성
    seen = set(fallback_chain)
    for b in backups:
        if b not in seen:
            fallback_chain.append(b)
            seen.add(b)
            
    last_error = None
    
    # 3. 순차적 실행 (429 에러 시 즉시 스킵)
    for model_name in fallback_chain:
        try:
            # 모델 생성 및 호출
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # 성공 시
            time.sleep(1)
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            # [중요] 429(Quota Exceeded) 에러 감지 시
            if "429" in error_str or "Quota" in error_str:
                # 사용자에게 알리지 않고 조용히(혹은 로그만 남기고) 다음 모델로 넘어감
                print(f"⚠️ {model_name} 쿼터 초과. 다음 모델로 전환합니다.")
                time.sleep(0.5)
                continue
            
            # 기타 에러도 넘어가기
            time.sleep(0.5)
            continue
            
    # 모든 모델 실패 시
    raise Exception(f"모든 모델이 실패했습니다. (마지막 에러: {last_error})\n다른 구글 계정을 사용하거나 잠시 후 시도해주세요.")

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
        st.toast(f"✅ 기획 생성 성공! (Used Model: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# --- HF 이미지 생성 (유지) ---
def generate_image_hf(prompt, token, model_id):
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    seed = random.randint(0, 999999) 
    payload = {
        "inputs": f"{prompt}, cinematic lighting, 8k, high quality",
        "parameters": {"seed": seed} 
    }
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            elif "estimated_time" in response.json():
                wait_time = response.json().get("estimated_time", 10)
                st.toast(f"😴 모델 깨우는 중... ({wait_time:.1f}초)")
                time.sleep(wait_time + 1)
                continue
            else:
                break
        except Exception as e:
            time.sleep(1)
    return None

# --- 실행 로직 ---

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

start_btn = st.button("🚀 프로젝트 시작")

if start_btn:
    if not gemini_key or not topic:
        st.warning("Google API Key와 주제를 입력해주세요.")
    elif not hf_token:
        st.warning("Hugging Face Token이 필요합니다.")
    else:
        with st.status("📝 기획안 작성 중...", expanded=True) as status:
            st.session_state['generated_images'] = {} 
            st.session_state['plan_data'] = generate_plan_gemini(topic, gemini_key, selected_gemini_model)
            status.update(label="기획안 작성 완료!", state="complete", expanded=False)

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
    st.subheader(f"🖼️ 비주얼 스토리보드 (Image Model: {hf_model_id.split('/')[-1]})")

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
                else:
                    if hf_token:
                        with st.spinner("📸 촬영 중..."):
                             full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                             img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                             if img_data:
                                 st.session_state['generated_images'][scene_num] = img_data
                                 st.image(img_data, use_container_width=True)
                             else:
                                 st.error("이미지 생성 실패")
                    else:
                        st.info("토큰 필요")

                if st.button(f"🔄 다시 그리기", key=f"regen_{scene_num}"):
                     if hf_token:
                        with st.spinner("📸 재촬영 중..."):
                            full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                            img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                            if img_data:
                                st.session_state['generated_images'][scene_num] = img_data
                                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ 스토리보드 완성!")
