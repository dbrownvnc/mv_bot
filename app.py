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
st.set_page_config(page_title="AI MV Director", layout="wide", initial_sidebar_state="collapsed")

# --- 스타일링 ---
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
    .turntable-box {
        background-color: #f0f9ff;
        border: 2px solid #4285F4;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(66,133,244,0.15);
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
    .prompt-preview {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        margin: 8px 0;
        font-family: monospace;
        font-size: 12px;
    }
    .stImage {
        max-height: 400px;
    }
    .stImage img {
        max-height: 400px;
        object-fit: contain;
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
            "Segmind (안정)",
            "Pollinations Turbo (초고속) ⚡",
            "Pollinations Flux (고품질)",
            "Hugging Face Schnell (빠름)",
            "Image.AI (무제한)",
        ],
        index=0
    )
    
    # 엔진별 설명
    engine_info = {
        "Segmind (안정)": "✨ 안정적 (기본 추천)",
        "Pollinations Turbo (초고속) ⚡": "✨ 1-2초 생성, 무료, 무제한",
        "Pollinations Flux (고품질)": "✨ 고품질, 3-5초, 무료",
        "Hugging Face Schnell (빠름)": "✨ 빠른 생성, 무료",
        "Image.AI (무제한)": "✨ 완전 무제한"
    }
    st.caption(engine_info[image_provider])
    
    # 재시도 설정
    max_retries = st.slider("생성 실패시 재시도 횟수", 1, 5, 3)

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
        topic = st.text_area("영상 주제를 입력하세요", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 이미지 비율 선택
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
        
        with col2:
            # 런닝타임 설정 방식
            duration_mode = st.radio(
                "⏱️ 런닝타임 설정",
                ["총 런닝타임", "씬 개수"],
                horizontal=True
            )
            
            if duration_mode == "총 런닝타임":
                total_duration = st.number_input("총 런닝타임 (초)", min_value=10, max_value=300, value=60, step=10)
                seconds_per_scene = st.slider("컷당 길이 (초)", 3, 15, 5)
                scene_count = int(total_duration / seconds_per_scene)
                st.caption(f"→ 총 {scene_count}개 씬 생성")
            else:
                scene_count = st.number_input("생성할 씬 개수", min_value=2, max_value=20, value=8, step=1)
                st.caption(f"총 {scene_count}개 씬")
        
        # 스토리 옵션
        st.markdown("**📖 스토리 구성**")
        story_options = st.columns(4)
        
        with story_options[0]:
            use_arc = st.checkbox("기승전결", value=True)
            use_sensory = st.checkbox("감각적", value=True)
        
        with story_options[1]:
            use_trial = st.checkbox("시련/갈등", value=False)
            use_dynamic = st.checkbox("역동적", value=True)
        
        with story_options[2]:
            use_emotional = st.checkbox("감정 변화", value=True)
            use_climax = st.checkbox("클라이맥스", value=True)
        
        with story_options[3]:
            use_symbolic = st.checkbox("상징적", value=False)
            use_twist = st.checkbox("반전", value=False)
        
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

def get_system_prompt(topic, scene_count, options):
    # 옵션을 텍스트로 변환
    story_elements = []
    if options.get('use_arc'): story_elements.append("classic story arc (introduction, rising action, climax, resolution)")
    if options.get('use_trial'): story_elements.append("conflict and trials for the protagonist")
    if options.get('use_sensory'): story_elements.append("highly sensory and immersive descriptions")
    if options.get('use_dynamic'): story_elements.append("dynamic and energetic movement")
    if options.get('use_emotional'): story_elements.append("clear emotional progression and character development")
    if options.get('use_climax'): story_elements.append("powerful climactic moment")
    if options.get('use_symbolic'): story_elements.append("symbolic imagery and metaphors")
    if options.get('use_twist'): story_elements.append("unexpected plot twist")
    
    story_instruction = ", ".join(story_elements) if story_elements else "cinematic storytelling"
    
    return f"""
    You are a professional Music Video Director.
    Analyze the following theme: "{topic}"
    Create a detailed plan with {scene_count} scenes in JSON format ONLY.
    
    Story Requirements: {story_instruction}
    
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
      "turntable_references": [
        {{
          "type": "character/object/environment",
          "name": "Name (Korean)",
          "description": "Detailed description (Korean)",
          "turntable_prompt": "Highly detailed English prompt for turntable/reference image generation. Include: lighting (studio lighting, neutral background), camera angle (360 degree view or front/side/back), material details, textures, colors, and specific features."
        }}
      ],
      "scenes": [
        {{
          "scene_num": 1,
          "timecode": "00:00-00:05",
          "action": "Scene description (Korean)",
          "camera": "Shot type (Korean)",
          "image_prompt": "Highly detailed English prompt for image generation.",
          "video_prompt": "Detailed English prompt for video generation describing movement, camera motion, and transitions."
        }}
        // Create {scene_count} scenes total with appropriate timing
      ]
    }}
    
    IMPORTANT: Create 3-5 turntable_references for main characters, key objects, and important environments that will appear throughout the scenes.
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

def generate_plan_auto(topic, api_key, model_name, scene_count, options):
    try:
        prompt = get_system_prompt(topic, scene_count, options)
        response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
        st.toast(f"✅ 기획 생성 완료 (Used: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# ------------------------------------------------------------------
# 2. 향상된 이미지 생성 로직
# ------------------------------------------------------------------

def try_generate_image_with_fallback(prompt, width, height, provider, max_retries=3):
    """
    선택된 엔진으로 이미지 생성 시도
    """
    enhanced_prompt = f"{prompt}, cinematic, high quality, detailed, professional"
    
    # 엔진별 엔드포인트
    if provider == "Pollinations Turbo (초고속) ⚡":
        endpoints = [
            {
                'name': 'Pollinations-Turbo',
                'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&model=turbo&seed={random.randint(0,999999)}"
            }
        ]
    elif provider == "Pollinations Flux (고품질)":
        endpoints = [
            {
                'name': 'Pollinations-Flux',
                'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&model=flux&seed={random.randint(0,999999)}"
            }
        ]
    elif provider == "Hugging Face Schnell (빠름)":
        endpoints = [
            {
                'name': 'HF-Schnell',
                'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
            }
        ]
    else:  # Segmind, Image.AI
        endpoints = [
            {
                'name': provider,
                'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
            }
        ]
    
    # 공통 폴백 (모든 엔진 실패시)
    fallback_endpoints = [
        {
            'name': 'Pollinations-Alt',
            'url': f"https://pollinations.ai/p/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}"
        }
    ]
    
    all_endpoints = endpoints + fallback_endpoints
    
    for attempt in range(max_retries):
        for endpoint in all_endpoints:
            try:
                response = requests.get(endpoint['url'], timeout=60)
                
                if response.status_code == 200 and len(response.content) > 1000:
                    img = Image.open(BytesIO(response.content))
                    if img.size[0] > 100 and img.size[1] > 100:
                        return img, endpoint['name']
            except Exception as e:
                continue
        
        if attempt < max_retries - 1:
            time.sleep(1)
    
    return None, None

# ------------------------------------------------------------------
# 3. 메인 실행 로직
# ------------------------------------------------------------------

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {}
if 'turntable_images' not in st.session_state:
    st.session_state['turntable_images'] = {}
if 'image_status' not in st.session_state:
    st.session_state['image_status'] = {}
if 'turntable_status' not in st.session_state:
    st.session_state['turntable_status'] = {}
if 'prompts_generated' not in st.session_state:
    st.session_state['prompts_generated'] = False
if 'auto_generation_running' not in st.session_state:
    st.session_state['auto_generation_running'] = False

# A. 실행 버튼 클릭 시 (Auto 모드)
if submit_btn and execution_mode == "API 자동 실행":
    if not gemini_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        st.session_state['generated_images'] = {} 
        st.session_state['turntable_images'] = {}
        st.session_state['image_status'] = {}
        st.session_state['turntable_status'] = {}
        st.session_state['plan_data'] = None
        st.session_state['prompts_generated'] = False
        st.session_state['auto_generation_running'] = False
        
        # 스토리 옵션 수집
        story_opts = {
            'use_arc': use_arc,
            'use_trial': use_trial,
            'use_sensory': use_sensory,
            'use_dynamic': use_dynamic,
            'use_emotional': use_emotional,
            'use_climax': use_climax,
            'use_symbolic': use_symbolic,
            'use_twist': use_twist
        }
        
        # 1. 기획안 생성
        plan_container = st.empty()
        with plan_container.container():
            st.markdown("<div class='status-box'>📝 AI가 기획안과 프롬프트를 작성하고 있습니다...</div>", unsafe_allow_html=True)
            
        st.session_state['plan_data'] = generate_plan_auto(topic, gemini_key, gemini_model, scene_count, story_opts)
        
        if st.session_state['plan_data']:
            plan = st.session_state['plan_data']
            st.session_state['prompts_generated'] = True
            
            with plan_container.container():
                st.markdown("<div class='status-box'>✅ 기획안 및 프롬프트 생성 완료!</div>", unsafe_allow_html=True)
            
            # 자동 생성 활성화시 즉시 이미지 생성 시작
            if auto_generate:
                st.session_state['auto_generation_running'] = True
                st.rerun()
        else:
            plan_container.markdown("<div class='error-box'>❌ 기획안 생성 실패</div>", unsafe_allow_html=True)

# B. 수동 모드 UI
if execution_mode == "수동 모드 (무제한)":
    st.info("💡 주제를 입력한 후 아래 단계를 따라주세요.")
    
    story_opts = {
        'use_arc': use_arc if 'use_arc' in locals() else True,
        'use_trial': use_trial if 'use_trial' in locals() else False,
        'use_sensory': use_sensory if 'use_sensory' in locals() else True,
        'use_dynamic': use_dynamic if 'use_dynamic' in locals() else True,
        'use_emotional': use_emotional if 'use_emotional' in locals() else True,
        'use_climax': use_climax if 'use_climax' in locals() else True,
        'use_symbolic': use_symbolic if 'use_symbolic' in locals() else False,
        'use_twist': use_twist if 'use_twist' in locals() else False
    }
    
    scene_count_manual = scene_count if 'scene_count' in locals() else 8
    prompt_to_copy = get_system_prompt(topic, scene_count_manual, story_opts) if topic else "주제를 먼저 입력해주세요."
    
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
                    st.session_state['turntable_images'] = {}
                    st.session_state['image_status'] = {}
                    st.session_state['turntable_status'] = {}
                    st.session_state['prompts_generated'] = True
                    st.success("로드 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 4. 자동 이미지 생성 프로세스
# ------------------------------------------------------------------

if st.session_state.get('auto_generation_running') and st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    
    st.markdown("---")
    st.markdown("### 🎨 자동 이미지 생성 중...")
    
    progress_container = st.container()
    
    # 1단계: 턴테이블 이미지 생성
    if 'turntable_references' in plan and plan['turntable_references']:
        turntables = plan['turntable_references']
        total_turntables = len(turntables)
        
        with progress_container:
            st.markdown("#### 📐 레퍼런스 이미지 생성")
            turntable_progress = st.progress(0)
            turntable_status = st.empty()
        
        for idx, ref in enumerate(turntables):
            ref_key = f"{ref['type']}_{idx}"
            
            if ref_key not in st.session_state['turntable_images']:
                turntable_status.markdown(f"<div class='status-box'>🎨 {ref['name']} 생성 중... ({idx+1}/{total_turntables})</div>", unsafe_allow_html=True)
                
                img, provider = try_generate_image_with_fallback(
                    ref['turntable_prompt'],
                    image_width,
                    image_height,
                    image_provider,
                    max_retries=max_retries
                )
                
                if img:
                    st.session_state['turntable_images'][ref_key] = img
                    st.session_state['turntable_status'][ref_key] = f"✅ 성공 ({provider})"
                else:
                    st.session_state['turntable_status'][ref_key] = "❌ 생성 실패"
                
                turntable_progress.progress((idx + 1) / total_turntables)
                time.sleep(0.3)
        
        turntable_status.markdown("<div class='status-box'>✅ 레퍼런스 이미지 생성 완료!</div>", unsafe_allow_html=True)
        time.sleep(1)
    
    # 2단계: 씬 이미지 생성
    scenes = plan['scenes']
    total_scenes = len(scenes)
    
    with progress_container:
        st.markdown("#### 🎬 씬 이미지 생성")
        scene_progress = st.progress(0)
        scene_status = st.empty()
    
    for idx, scene in enumerate(scenes):
        scene_num = scene['scene_num']
        
        if scene_num not in st.session_state['generated_images']:
            scene_status.markdown(f"<div class='status-box'>🎬 Scene {scene_num} 이미지 생성 중... ({idx+1}/{total_scenes})</div>", unsafe_allow_html=True)
            
            full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
            
            img, provider = try_generate_image_with_fallback(
                full_prompt,
                image_width,
                image_height,
                image_provider,
                max_retries=max_retries
            )
            
            if img:
                st.session_state['generated_images'][scene_num] = img
                st.session_state['image_status'][scene_num] = f"✅ 성공 ({provider})"
            else:
                st.session_state['image_status'][scene_num] = "❌ 생성 실패"
            
            scene_progress.progress((idx + 1) / total_scenes)
            time.sleep(0.3)
    
    scene_status.markdown("<div class='status-box'>✅ 모든 이미지 생성 완료!</div>", unsafe_allow_html=True)
    st.session_state['auto_generation_running'] = False
    time.sleep(1)
    st.rerun()

# ------------------------------------------------------------------
# 5. 결과 표시
# ------------------------------------------------------------------

if st.session_state['plan_data'] and st.session_state['prompts_generated']:
    plan = st.session_state['plan_data']
    
    # 기획안 요약 표시
    st.markdown("---")
    st.subheader(f"🎥 {plan['project_title']}")
    st.info(plan['logline'])
    
    with st.expander("📋 전체 기획안 보기", expanded=False):
        st.markdown(f"**음악 스타일:** {plan['music']['style']}")
        st.code(plan['music']['suno_prompt'], language="text")
        st.markdown(f"**비주얼 스타일:** {plan['visual_style']['description']}")
        st.code(plan['visual_style']['character_prompt'], language="text")
    
    # 턴테이블 레퍼런스 섹션
    if 'turntable_references' in plan and plan['turntable_references']:
        st.markdown("---")
        st.markdown("### 📐 레퍼런스 이미지 (Turntable)")
        
        turntable_cols = st.columns(min(3, len(plan['turntable_references'])))
        
        for idx, ref in enumerate(plan['turntable_references']):
            ref_key = f"{ref['type']}_{idx}"
            col = turntable_cols[idx % 3]
            
            with col:
                st.markdown(f"<div class='turntable-box'>", unsafe_allow_html=True)
                st.markdown(f"**{ref['name']}** ({ref['type']})")
                
                if ref_key in st.session_state['turntable_images']:
                    st.image(st.session_state['turntable_images'][ref_key], use_container_width=True)
                    if ref_key in st.session_state['turntable_status']:
                        st.caption(st.session_state['turntable_status'][ref_key])
                else:
                    if ref_key in st.session_state['turntable_status']:
                        st.markdown(f"<div class='error-box'>{st.session_state['turntable_status'][ref_key]}</div>", unsafe_allow_html=True)
                    
                    if st.button(f"📸 생성", key=f"gen_turntable_{idx}"):
                        with st.spinner("🎨 이미지 생성 중..."):
                            img, provider = try_generate_image_with_fallback(
                                ref['turntable_prompt'],
                                image_width,
                                image_height,
                                image_provider,
                                max_retries=max_retries
)
    if img:
                            st.session_state['turntable_images'][ref_key] = img
                            st.session_state['turntable_status'][ref_key] = f"✅ 성공 ({provider})"
                            st.rerun()
                        else:
                            st.session_state['turntable_status'][ref_key] = "❌ 생성 실패"
                            st.error("이미지 생성 실패")
            
            with st.expander("📝 프롬프트"):
                st.caption(ref['description'])
                st.code(ref['turntable_prompt'], language="text")
            
            st.markdown("</div>", unsafe_allow_html=True)

# 스토리보드 섹션
st.markdown("---")
st.markdown("### 🖼️ 스토리보드")

# 전체 재생성 버튼
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    if st.button("🔄 모든 씬 재생성", use_container_width=True):
        st.session_state['generated_images'] = {}
        st.session_state['image_status'] = {}
        st.rerun()
with col_btn2:
    if st.button("🔄 레퍼런스 재생성", use_container_width=True):
        st.session_state['turntable_images'] = {}
        st.session_state['turntable_status'] = {}
        st.rerun()
with col_btn3:
    if st.button("📋 프롬프트 모두 보기", use_container_width=True):
        for scene in plan['scenes']:
            with st.expander(f"Scene {scene['scene_num']}", expanded=True):
                full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                st.code(full_prompt, language="text")

for scene in plan['scenes']:
    scene_num = scene['scene_num']
    
    st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
    
    # 씬 헤더
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"#### Scene {scene_num} - {scene['timecode']}")
    with col2:
        # 개별 재생성 버튼
        if scene_num in st.session_state['generated_images']:
            if st.button("🔄", key=f"regen_{scene_num}", help="이미지 재생성"):
                del st.session_state['generated_images'][scene_num]
                st.rerun()
    
    # 이미지 표시
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
                    image_provider,
                    max_retries=max_retries
                )
                
                if img:
                    st.session_state['generated_images'][scene_num] = img
                    st.session_state['image_status'][scene_num] = f"✅ 성공 ({provider})"
                    st.rerun()
                else:
                    st.session_state['image_status'][scene_num] = "❌ 생성 실패"
                    st.error("이미지 생성 실패 - 다시 시도해주세요")

    # 씬 정보
    st.write(f"**액션:** {scene['action']}")
    st.write(f"**카메라:** {scene['camera']}")
    
    with st.expander("📝 프롬프트 상세"):
        st.markdown("**이미지 프롬프트:**")
        full_img_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
        st.code(full_img_prompt, language="text")
        if 'video_prompt' in scene:
            st.markdown("**영상 프롬프트:**")
            st.code(scene['video_prompt'], language="text")
        
    st.markdown("</div>", unsafe_allow_html=True)
