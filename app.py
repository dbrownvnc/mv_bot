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
st.set_page_config(page_title="AI MV Director (Mobile)", layout="wide", initial_sidebar_state="collapsed")

# --- 스타일링 (모바일 최적화) ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    .scene-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #4285F4;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em; 
        font-weight: bold;
    }
    .manual-box {
        background-color: #f8f9fa;
        border: 2px dashed #FFD700;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stProgress > div > div > div > div {
        background-color: #4285F4;
    }
    .status-box {
        background-color: #f0f7ff;
        border-left: 4px solid #4285F4;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 14px;
    }
    .error-box {
        background-color: #fff0f0;
        border-left: 4px solid #ff4444;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- API 키 로드 ---
def get_api_key(key_name):
    if key_name in st.secrets: return st.secrets[key_name]
    elif os.getenv(key_name): return os.getenv(key_name)
    return None

# --- 사이드바 (설정) ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 실행 모드 선택
    execution_mode = st.radio(
        "실행 방식",
        ["API 자동 실행", "수동 모드 (무제한)"],
        index=0
    )
    
    st.markdown("---")

    # API 모드일 때만 키 입력 받기
    gemini_key = None
    gemini_model = None
    
    if execution_mode == "API 자동 실행":
        gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
        if gemini_key:
            st.success("✅ Gemini Key 연결됨")
        else:
            gemini_key = st.text_input("Gemini API Key", type="password")
            
        st.caption("사용 모델")
        model_options = [
            "gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", 
            "gemini-1.5-pro", "gemini-1.0-pro", "gemini-flash-latest"
        ]
        gemini_model = st.selectbox("모델 선택", model_options, index=0, label_visibility="collapsed")
    
    st.markdown("---")
    
    # 이미지 생성 설정
    st.subheader("🎨 이미지 생성 설정")
    
    # 자동 생성 옵션
    auto_generate = st.checkbox("프로젝트 생성시 자동 이미지 생성", value=True)
    
    image_provider = st.selectbox(
        "이미지 생성 엔진",
        [
            "Segmind (무료/빠름) ⚡",
            "Pollinations AI (무료)",
            "Image.AI (무료/무제한)",
            "Hugging Face"
        ],
        index=0
    )
    
    if image_provider == "Segmind (무료/빠름) ⚡":
        segmind_model = st.selectbox(
            "Segmind 모델",
            [
                "sd1.5",
                "sdxl",
                "kandinsky",
                "playground"
            ],
            index=0
        )
        st.caption("✨ 가장 빠르고 안정적 (추천)")
        
    elif image_provider == "Pollinations AI (무료)":
        pollinations_model = st.selectbox(
            "Pollinations 모델",
            [
                "flux",
                "flux-realism", 
                "flux-anime",
                "flux-3d",
                "turbo"
            ],
            index=0
        )
        st.caption("✨ 고품질 이미지 생성")
        
    elif image_provider == "Image.AI (무료/무제한)":
        st.caption("✨ 완전 무제한, API 키 불필요")
        
    else:  # Hugging Face
        hf_token = get_api_key("HF_TOKEN")
        if hf_token:
            st.success("✅ HF Token 연결됨")
        else:
            hf_token = st.text_input("Hugging Face Token", type="password")
        
        hf_model_id = st.selectbox(
            "HF 이미지 모델",
            [
                "black-forest-labs/FLUX.1-schnell",
                "stabilityai/stable-diffusion-xl-base-1.0"
            ],
            index=0
        )
    
    # 재시도 설정
    st.markdown("---")
    max_retries = st.slider("생성 실패시 재시도 횟수", 1, 5, 3)
    st.caption("실패한 이미지는 자동으로 다시 시도합니다")

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

# 비율 매핑
ratio_map = {
    "1:1 (Square)": (1024, 1024),
    "16:9 (Cinema)": (1024, 576),
    "9:16 (Portrait)": (576, 1024),
    "4:3 (Classic)": (1024, 768),
    "3:2 (Photo)": (1024, 683),
    "21:9 (Ultra Wide)": (1024, 439)
}

with st.expander("📝 프로젝트 설정 (터치하여 열기)", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제를 입력하세요", height=100, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")
        
        # 이미지 비율 선택 추가
        aspect_ratio = st.selectbox(
            "🎞️ 이미지 비율",
            [
                "16:9 (Cinema)",
                "9:16 (Portrait)",
                "1:1 (Square)",
                "4:3 (Classic)",
                "3:2 (Photo)",
                "21:9 (Ultra Wide)"
            ],
            index=0
        )
        
        image_width, image_height = ratio_map[aspect_ratio]
        st.caption(f"해상도: {image_width}x{image_height}")
        
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 공통 함수
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def get_system_prompt(topic):
    return f"""
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
          "image_prompt": "Highly detailed English prompt for image generation.",
          "video_prompt": "Detailed English prompt for video generation describing movement, camera motion, and transitions."
        }}
        // Create 4 scenes total
      ]
    }}
    """

# ------------------------------------------------------------------
# 1. API 자동 실행 로직
# ------------------------------------------------------------------
def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    fallback_chain = [start_model]
    backups = ["gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-flash-8b", "gemini-1.0-pro", "gemini-flash-latest"]
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

def generate_plan_auto(topic, api_key, model_name):
    try:
        prompt = get_system_prompt(topic)
        response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
        st.toast(f"✅ 기획 생성 완료 (Used: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# ------------------------------------------------------------------
# 2. 향상된 이미지 생성 로직 (다중 폴백)
# ------------------------------------------------------------------

def try_generate_image_with_fallback(prompt, width, height, max_retries=3):
    """
    여러 무료 API를 순차적으로 시도하는 폴백 시스템
    """
    enhanced_prompt = f"{prompt}, cinematic, high quality, detailed, professional"
    
    # 시도할 API 엔드포인트들 (우선순위순)
    endpoints = [
        # Pollinations (가장 안정적)
        {
            'name': 'Pollinations',
            'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
        },
        # Pollinations 대체 URL
        {
            'name': 'Pollinations Alt',
            'url': f"https://pollinations.ai/p/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}"
        },
        # Segmind-style API
        {
            'name': 'Segmind',
            'url': f"https://api.segmind.com/v1/sd1.5",
            'method': 'POST',
            'json': {
                "prompt": enhanced_prompt,
                "negative_prompt": "blurry, bad quality, distorted",
                "samples": 1,
                "scheduler": "DDIM",
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
                "seed": random.randint(0, 999999),
                "img_width": width,
                "img_height": height
            }
        }
    ]
    
    for attempt in range(max_retries):
        for endpoint in endpoints:
            try:
                if endpoint.get('method') == 'POST':
                    response = requests.post(
                        endpoint['url'], 
                        json=endpoint['json'], 
                        timeout=60
                    )
                else:
                    response = requests.get(endpoint['url'], timeout=60)
                
                if response.status_code == 200 and len(response.content) > 1000:  # 최소 크기 확인
                    img = Image.open(BytesIO(response.content))
                    # 이미지 유효성 검증
                    if img.size[0] > 100 and img.size[1] > 100:
                        return img, endpoint['name']
            except Exception as e:
                continue
        
        if attempt < max_retries - 1:
            time.sleep(2)  # 재시도 전 대기
    
    return None, None

# ------------------------------------------------------------------
# 3. 메인 실행 로직
# ------------------------------------------------------------------

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {}
if 'image_status' not in st.session_state:
    st.session_state['image_status'] = {}

# A. 실행 버튼 클릭 시 (Auto 모드)
if submit_btn and execution_mode == "API 자동 실행":
    if not gemini_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        st.session_state['generated_images'] = {} 
        st.session_state['image_status'] = {}
        st.session_state['plan_data'] = None
        
        # 1. 기획안 생성
        plan_container = st.empty()
        with plan_container.container():
            st.markdown("<div class='status-box'>📝 AI가 기획안을 작성하고 있습니다...</div>", unsafe_allow_html=True)
            
        st.session_state['plan_data'] = generate_plan_auto(topic, gemini_key, gemini_model)
        
        if st.session_state['plan_data']:
            plan = st.session_state['plan_data']
            
            # 기획안 즉시 표시
            with plan_container.container():
                st.markdown("<div class='status-box'>✅ 기획안 생성 완료!</div>", unsafe_allow_html=True)
                st.subheader(f"🎥 {plan['project_title']}")
                st.info(plan['logline'])
                
                with st.expander("📋 전체 기획안 보기", expanded=False):
                    st.markdown(f"**음악 스타일:** {plan['music']['style']}")
                    st.code(plan['music']['suno_prompt'], language="text")
                    st.markdown(f"**비주얼 스타일:** {plan['visual_style']['description']}")
                    st.code(plan['visual_style']['character_prompt'], language="text")
                    
                    for scene in plan['scenes']:
                        st.markdown(f"**Scene {scene['scene_num']}** ({scene['timecode']})")
                        st.write(f"- {scene['action']}")
            
            # 2. 자동 이미지 생성
            if auto_generate:
                total_scenes = len(plan['scenes'])
                st.markdown("---")
                st.markdown("### 🎨 이미지 자동 생성")
                
                progress_bar = st.progress(0)
                status_container = st.container()
                
                for idx, scene in enumerate(plan['scenes']):
                    scene_num = scene['scene_num']
                    
                    with status_container:
                        st.markdown(f"<div class='status-box'>🎬 Scene {scene_num} 이미지 생성 중... ({idx+1}/{total_scenes})</div>", unsafe_allow_html=True)
                        
                        # 프롬프트 미리보기
                        with st.expander(f"Scene {scene_num} 프롬프트 보기"):
                            full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                            st.code(full_prompt, language="text")
                            if 'video_prompt' in scene:
                                st.markdown("**영상 프롬프트:**")
                                st.code(scene['video_prompt'], language="text")
                    
                    # 이미지 생성 시도
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    
                    img, provider = try_generate_image_with_fallback(
                        full_prompt,
                        image_width,
                        image_height,
                        max_retries=max_retries
                    )
                    
                    if img:
                        st.session_state['generated_images'][scene_num] = img
                        st.session_state['image_status'][scene_num] = f"✅ 성공 ({provider})"
                        st.toast(f"✅ Scene {scene_num} 완료! ({provider})")
                    else:
                        st.session_state['image_status'][scene_num] = "❌ 생성 실패"
                        st.warning(f"⚠️ Scene {scene_num} 생성 실패 - 나중에 재생성 가능")
                    
                    progress_bar.progress((idx + 1) / total_scenes)
                    time.sleep(0.5)
                
                st.markdown("<div class='status-box'>✅ 이미지 생성 프로세스 완료!</div>", unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
        else:
            plan_container.markdown("<div class='error-box'>❌ 기획안 생성 실패</div>", unsafe_allow_html=True)

# B. 수동 모드 UI
if execution_mode == "수동 모드 (무제한)":
    st.info("💡 주제를 입력한 후 아래 단계를 따라주세요.")
    
    prompt_to_copy = get_system_prompt(topic) if topic else "주제를 먼저 입력해주세요."
    
    with st.container():
        st.markdown(f"<div class='manual-box'>", unsafe_allow_html=True)
        st.markdown("**1. 프롬프트 복사**")
        st.code(prompt_to_copy, language="text")
        
        c1, c2 = st.columns(2)
        with c1:
            st.link_button("🚀 Gemini 열기", "https://gemini.google.com/", use_container_width=True)
        
        st.markdown("**2. 결과 붙여넣기**")
        manual_json_input = st.text_area("JSON 결과", height=150, placeholder="```json\n{\n ... \n}\n```", label_visibility="collapsed")
        
        if st.button("✅ 결과 적용"):
            if not manual_json_input.strip():
                st.warning("결과를 붙여넣어주세요.")
            else:
                try:
                    st.session_state['plan_data'] = json.loads(clean_json_text(manual_json_input))
                    st.session_state['generated_images'] = {} 
                    st.session_state['image_status'] = {}
                    st.success("로드 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 4. 결과 표시
# ------------------------------------------------------------------

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    
    # 자동 생성 후가 아니면 기획안 표시
    if not auto_generate or not submit_btn:
        st.divider()
        st.subheader(f"🎥 {plan['project_title']}")
        st.info(plan['logline'])
        
        with st.expander("🎵 음악 & 🎨 비주얼 설정", expanded=False):
            st.markdown("**Music:** " + plan['music']['style'])
            st.code(plan['music']['suno_prompt'])
            st.markdown("**Visual:** " + plan['visual_style']['description'])
            st.code(plan['visual_style']['character_prompt'])
    
    st.markdown("---")
    st.markdown("### 🖼️ 스토리보드")
    
    # 전체 재생성 버튼
    if st.button("🔄 모든 씬 재생성", key="regenerate_all"):
        st.session_state['generated_images'] = {}
        st.session_state['image_status'] = {}
        st.rerun()

    for scene in plan['scenes']:
        scene_num = scene['scene_num']
        
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"#### Scene {scene_num}")
        with col2:
            # 개별 재생성 버튼
            if scene_num in st.session_state['generated_images']:
                if st.button("🔄", key=f"regen_{scene_num}", help="이미지 재생성"):
                    del st.session_state['generated_images'][scene_num]
                    st.rerun()
        
        # 이미지 표시 또는 생성 버튼
        if scene_num in st.session_state['generated_images']:
            st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
            if scene_num in st.session_state['image_status']:
                st.caption(st.session_state['image_status'][scene_num])
        else:
            # 실패한 경우 표시
            if scene_num in st.session_state['image_status']:
                st.markdown(f"<div class='error-box'>{st.session_state['image_status'][scene_num]}</div>", unsafe_allow_html=True)
            
            # 수동 생성 버튼
            if st.button(f"📸 촬영 (Scene {scene_num})", key=f"gen_{scene_num}"):
                with st.spinner("🎨 이미지 생성 중..."):
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    
                    img, provider = try_generate_image_with_fallback(
                        full_prompt,
                        image_width,
                        image_height,
                        max_retries=max_retries
                    )
                    
                    if img:
                        st.session_state['generated_images'][scene_num] = img
                        st.session_state['image_status'][scene_num] = f"✅ 성공 ({provider})"
                        st.rerun()
                    else:
                        st.session_state['image_status'][scene_num] = "❌ 생성 실패"
                        st.error("이미지 생성 실패 - 다시 시도해주세요")

        st.caption(f"⏱️ {scene['timecode']}")
        st.write(f"**Action:** {scene['action']}")
        st.write(f"**Camera:** {scene['camera']}")
        
        with st.expander("📝 프롬프트 상세"):
            st.markdown("**이미지 프롬프트:**")
            st.code(scene['image_prompt'], language="text")
            if 'video_prompt' in scene:
                st.markdown("**영상 프롬프트:**")
                st.code(scene['video_prompt'], language="text")
            
        st.markdown("</div>", unsafe_allow_html=True)
