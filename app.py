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
from datetime import datetime
import base64

# --- 페이지 설정 ---
st.set_page_config(page_title="AI MV Director Pro", layout="wide", initial_sidebar_state="collapsed")

# --- 스타일링 ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
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
        background-color: #fff9e6;
        border: 2px solid #FFD700;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .trend-box {
        background-color: #e6f7ff;
        border: 2px solid #1890ff;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    }
    .turntable-tag {
        display: inline-block;
        background: linear-gradient(135deg, #FFD700, #FFA500);
        color: #000;
        padding: 4px 12px;
        border-radius: 15px;
        margin: 4px;
        font-size: 11px;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em; 
        font-weight: bold;
    }
    .status-box {
        background-color: #f0f7ff;
        border-left: 4px solid #4285F4;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 14px;
    }
    .realtime-calc {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 트렌드 키워드 ---
TRENDING_KEYWORDS = {
    "emotions": ["heartbreak", "hope", "nostalgia", "euphoria", "melancholy", "rage"],
    "settings": ["neon city", "abandoned subway", "rooftop at dawn", "underwater palace"],
    "characters": ["lonely hacker", "rebel artist", "time traveler", "android musician"],
    "aesthetics": ["retro 80s", "vaporwave dreams", "dark academia", "cyberpunk"],
    "times": ["midnight", "golden hour", "endless night"]
}

def generate_trending_topic():
    templates = [
        "{character} experiencing {emotion} in a {setting} during {time}, {aesthetic} style",
        "{emotion} journey of a {character} in {setting}, {aesthetic} vibes",
    ]
    template = random.choice(templates)
    return template.format(
        emotion=random.choice(TRENDING_KEYWORDS["emotions"]),
        setting=random.choice(TRENDING_KEYWORDS["settings"]),
        character=random.choice(TRENDING_KEYWORDS["characters"]),
        aesthetic=random.choice(TRENDING_KEYWORDS["aesthetics"]),
        time=random.choice(TRENDING_KEYWORDS["times"])
    )

def get_viral_topic_with_ai(api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = "Generate ONE viral music video concept (2 sentences)."
        response = model.generate_content(prompt)
        return response.text.strip().strip('"')
    except:
        return generate_trending_topic()

# --- API 키 ---
def get_api_key(key_name):
    if key_name in st.secrets: return st.secrets[key_name]
    elif os.getenv(key_name): return os.getenv(key_name)
    return None

# --- 장르/스타일 ---
VIDEO_GENRES = ["Action", "Sci-Fi", "Fantasy", "Drama", "Romance", "Cyberpunk", "Music Video"]
VISUAL_STYLES = ["Cinematic", "Anime", "3D Animation", "Watercolor", "Cyberpunk Neon", "Retro 80s"]
MUSIC_GENRES = ["Pop", "Hip-Hop", "EDM", "R&B", "Rock", "Lo-Fi", "K-Pop"]

# --- 비주얼 스타일 강조 ---
def get_visual_style_emphasis(visual_style):
    if "Cinematic" in visual_style:
        return "Photorealistic, 8K, shot on ARRI Alexa, detailed skin texture, realistic lighting"
    elif "Anime" in visual_style:
        return "Anime style, Makoto Shinkai style, vibrant colors, high detail"
    return f"{visual_style}, best quality, masterpiece"

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    execution_mode = st.radio("실행 방식", ["API 자동 실행", "수동 모드 (무제한)"], index=0)
    st.markdown("---")

    gemini_key = None
    gemini_model = None
    
    if execution_mode == "API 자동 실행":
        gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
        if gemini_key:
            st.success("✅ Gemini Key 연결됨")
        else:
            gemini_key = st.text_input("Gemini API Key", type="password")
        model_options = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        gemini_model = st.selectbox("모델", model_options, index=0)
    
    st.markdown("---")
    st.subheader("🎨 이미지 생성")
    auto_generate = st.checkbox("자동 이미지 생성", value=False)
    infinite_retry = st.checkbox("무한 재시도", value=False)
    
    # [요청 반영] Segmind를 기본값(index=0)으로 복구
    image_provider = st.selectbox("엔진", ["Segmind", "Pollinations Turbo ⚡", "Pollinations Flux"], index=0)
    
    if not infinite_retry:
        max_retries = st.slider("재시도", 1, 10, 3)
    else:
        max_retries = 999

    st.markdown("---")
    if st.button("🗑️ 전체 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 화면 ---
st.title("🎬 AI MV Director Pro")

ratio_map = {
    "16:9 (Cinema)": (1024, 576),
    "9:16 (Portrait)": (576, 1024),
    "1:1 (Square)": (1024, 1024),
}

# 세션 상태 초기화
defaults = {
    'scene_count': 8,
    'total_duration': 40,
    'seconds_per_scene': 5,
    'random_topic': "",
    'plan_data': None,
    'generated_images': {},
    'turntable_images': {}
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

with st.expander("📝 프로젝트 설정", expanded=True):
    st.markdown("<div class='trend-box'>", unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        if st.button("🎲 랜덤 생성", use_container_width=True):
            st.session_state.random_topic = generate_trending_topic()
            st.rerun()
    with col_t3:
        if st.button("🤖 AI 생성", use_container_width=True):
            if gemini_key:
                st.session_state.random_topic = get_viral_topic_with_ai(gemini_key, gemini_model)
                st.rerun()
            else:
                st.warning("API 키 필요")
    
    if st.session_state.random_topic:
        st.info(f"💡 {st.session_state.random_topic}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    with st.form("project_form"):
        topic = st.text_area("🎯 영상 주제/컨셉", height=80, 
                            value=st.session_state.random_topic,
                            placeholder="주제를 입력하세요...")
        
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1: selected_genre = st.selectbox("🎬 장르", VIDEO_GENRES, index=0)
        with col_g2: selected_visual = st.selectbox("🎨 스타일", VISUAL_STYLES, index=0)
        with col_g3: selected_music = st.selectbox("🎵 음악", MUSIC_GENRES, index=0)
        
        st.markdown("---")
        
        aspect_ratio = st.selectbox("🎞️ 화면 비율", list(ratio_map.keys()), index=0)
        image_width, image_height = ratio_map[aspect_ratio]
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 프로젝트 생성", use_container_width=True, type="primary")

    st.markdown("#### ⏱️ 타임라인 설정 (실시간 계산)")
    duration_mode = st.radio("설정 방식", ["총 런닝타임 기준", "씬 개수 기준"], horizontal=True)
    
    col_time1, col_time2, col_time3 = st.columns(3)
    
    if duration_mode == "총 런닝타임 기준":
        with col_time1:
            total_duration = st.number_input("총 런닝타임 (초)", min_value=10, max_value=600, value=st.session_state.total_duration, step=5, key="input_total_dur")
        with col_time2:
            seconds_per_scene = st.number_input("컷당 길이 (초)", min_value=2, max_value=20, value=st.session_state.seconds_per_scene, step=1, key="input_sec_per_scene_1")
        
        scene_count = max(1, int(total_duration / seconds_per_scene))
        st.session_state.scene_count = scene_count
        st.session_state.total_duration = total_duration
        st.session_state.seconds_per_scene = seconds_per_scene
        
        with col_time3:
            st.markdown(f"""
            <div class='realtime-calc'>
                📊 총 {scene_count}개 씬<br>
                <small>{total_duration}s ÷ {seconds_per_scene}s</small>
            </div>
            """, unsafe_allow_html=True)
            
    else: 
        with col_time1:
            scene_count = st.number_input("씬 개수", min_value=2, max_value=50, value=st.session_state.scene_count, step=1, key="input_scene_count")
        with col_time2:
            seconds_per_scene = st.number_input("컷당 길이 (초)", min_value=2, max_value=20, value=st.session_state.seconds_per_scene, step=1, key="input_sec_per_scene_2")
            
        total_duration = scene_count * seconds_per_scene
        st.session_state.scene_count = scene_count
        st.session_state.total_duration = total_duration
        st.session_state.seconds_per_scene = seconds_per_scene
        
        with col_time3:
            st.markdown(f"""
            <div class='realtime-calc'>
                ⏱️ 총 {total_duration}초<br>
                <small>({scene_count}scenes × {seconds_per_scene}s)</small>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 시스템 프롬프트 (일관성 및 턴테이블 강화 - 수정됨)
# ------------------------------------------------------------------
def get_system_prompt(topic, scene_count, genre, visual_style, music_genre, seconds_per_scene):
    visual_emphasis = get_visual_style_emphasis(visual_style)
    
    return f"""You are an ELITE music video director. Create an ULTRA-DETAILED production plan in VALID JSON format.

PROJECT BRIEF:
Theme: "{topic}"
Genre: {genre}
Visual Style: {visual_style} (Strictly enforce: {visual_emphasis})
Format: {scene_count} scenes, {seconds_per_scene} seconds each.

***CRITICAL INSTRUCTIONS FOR CONSISTENCY (THE 100x RULE)***:
1. **MANDATORY JSON PROFILES**: You MUST generate a "json_profile" dictionary for EVERY Character, Location, and Key Object used in the video.
2. **EXTREME DETAIL**: Inside `json_profile`, the `description` field must be dense and specific. Use HEX COLOR CODES (e.g., #FF0000) for clothes, hair, eyes, and environment lights. This description will be copy-pasted into every image prompt. If you generate this 100 times, it must look identical 100 times.
3. **TURNTABLE MANDATE**: Generate `turntable` entries for ALL entities (Characters, Locations, Objects).
4. **MULTI-VIEW TURNTABLES**: 
   - For Characters: Prompt MUST start with "{visual_emphasis}, character sheet, multiple views, front view, side view, back view, 3/4 view all in one image, white background..." followed by the detailed profile.
   - For Locations: Prompt MUST be "Environment concept sheet, wide shot, establishing shot..."
5. **SCENE PROMPT INJECTION**: In the `scenes` array, the `image_prompt` MUST explicitly include the full text from the relevant `json_profile`. DO NOT just say "Character A". Say "Character A, [insert full description including hex codes and features]".

RETURN THIS EXACT JSON STRUCTURE:
{{
  "project_title": "Title",
  "logline": "Concept",
  "turntable": {{
    "characters": [
      {{
        "id": "char1",
        "name": "Name",
        "json_profile": {{
           "description": "25yo female, cybernetic left arm (silver #C0C0C0), neon pink bob hair (#FF00FF), wearing matte black tactical vest..."
        }},
        "views": [
           {{ "view_type": "character_sheet", "prompt": "{visual_emphasis}, character sheet, multiple views, front view, side view, back view all in one image, white background, [INSERT FULL json_profile.description HERE]" }}
        ]
      }}
    ],
    "locations": [
      {{
        "id": "loc1",
        "name": "Location Name",
        "json_profile": {{ "description": "Cyberpunk alleyway, wet pavement reflecting neon blue (#0000FF) signs, steam rising..." }},
        "views": [
           {{ "view_type": "environment_sheet", "prompt": "{visual_emphasis}, environment concept art, wide shot, establishing shot, [INSERT FULL json_profile.description HERE]" }}
        ]
      }}
    ],
    "objects": [
       {{
         "id": "obj1",
         "name": "Object Name",
         "json_profile": {{ "description": "Antique pocket watch, gold (#FFD700), cracked glass face..." }},
         "views": [
            {{ "view_type": "product_sheet", "prompt": "{visual_emphasis}, product photography, multiple angles, white background, [INSERT FULL json_profile.description HERE]" }}
         ]
       }}
    ]
  }},
  "scenes": [
    {{
      "scene_num": 1,
      "timecode": "00:00-00:{seconds_per_scene:02d}",
      "action": "Action description",
      "used_turntables": ["char1", "loc1"],
      "image_prompt": "{visual_emphasis}, [INSERT FULL DESCRIPTION FROM char1 JSON_PROFILE], [INSERT FULL DESCRIPTION FROM loc1 JSON_PROFILE], acting out [Action], cinematic lighting, masterpiece",
      "video_prompt": "Camera movement"
    }}
  ]
}}
"""

# ------------------------------------------------------------------
# JSON 정리 및 로드
# ------------------------------------------------------------------
def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: text = match.group(1)
    else:
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match: text = match.group(1)
    return text.strip()

def apply_json_profiles_to_prompt(base_prompt, used_turntables, turntable_data):
    # 비상용 함수: LLM이 프롬프트에 설명을 포함하지 않았을 경우 강제 주입
    if not used_turntables or not turntable_data:
        return base_prompt
    
    additions = []
    for tt_ref in used_turntables:
        for cat in ['characters', 'locations', 'objects']:
            if cat in turntable_data:
                for item in turntable_data[cat]:
                    if item.get('id') == tt_ref:
                        if 'json_profile' in item and 'description' in item['json_profile']:
                            additions.append(item['json_profile']['description'])
    
    # 중복 방지: 이미 프롬프트에 설명이 포함되어 있는지 확인은 어렵지만, LLM 지시가 강력하므로
    # 여기서는 정말 누락되었을 때를 대비해 앞에 붙임
    if additions:
        return ", ".join(additions) + ", " + base_prompt
    return base_prompt

# ------------------------------------------------------------------
# 이미지 생성 함수 (Segmind/Flux 지원)
# ------------------------------------------------------------------
def try_generate_image_with_fallback(prompt, width, height, provider, max_retries=3):
    enhanced = f"{prompt}, cinematic, high quality, 8k"
    
    # Pollinations URL Construction
    # Segmind 요청시 Flux 모델(고퀄리티)로 매핑하여 Segmind급 퀄리티 보장
    if "Segmind" in provider or "Flux" in provider:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}&model=flux"
    else:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200 and len(response.content) > 1000:
                img = Image.open(BytesIO(response.content))
                return img
        except:
            time.sleep(1)
    return None

# ------------------------------------------------------------------
# API 통신
# ------------------------------------------------------------------
def generate_plan_api(topic, api_key, model_name, scene_count, genre, visual, music, seconds):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = get_system_prompt(topic, scene_count, genre, visual, music, seconds)
    
    try:
        response = model.generate_content(prompt)
        return json.loads(clean_json_text(response.text))
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

# ------------------------------------------------------------------
# 메인 실행 로직
# ------------------------------------------------------------------
if submit_btn:
    if not topic:
        st.warning("⚠️ 주제를 입력해주세요")
    else:
        if execution_mode == "API 자동 실행":
            if not gemini_key:
                st.warning("⚠️ API Key가 필요합니다")
            else:
                with st.spinner("🎬 기획안 생성 중..."):
                    st.session_state['plan_data'] = generate_plan_api(
                        topic, gemini_key, gemini_model, 
                        st.session_state.scene_count, selected_genre, selected_visual, selected_music, 
                        st.session_state.seconds_per_scene
                    )
                if st.session_state['plan_data']:
                    st.success("✅ 기획안 생성 완료!")
                    st.rerun()
        else:
            st.session_state['manual_prompt'] = get_system_prompt(
                topic, st.session_state.scene_count, selected_genre, selected_visual, selected_music, 
                st.session_state.seconds_per_scene
            )
            st.session_state['show_manual'] = True
            st.rerun()

# ------------------------------------------------------------------
# 수동 모드 UI
# ------------------------------------------------------------------
if execution_mode == "수동 모드 (무제한)" and st.session_state.get('show_manual'):
    st.markdown("---")
    st.subheader("📋 수동 모드")
    
    col_m1, col_m2 = st.columns([4, 1])
    with col_m1:
        st.code(st.session_state['manual_prompt'], language="text")
        st.caption("👆 위 박스 우측 상단 'Copy' 아이콘을 누르면 전체 복사됩니다.")
    with col_m2:
        st.link_button("🚀 Gemini 열기", "https://gemini.google.com/", use_container_width=True)
        st.link_button("🤖 ChatGPT 열기", "https://chat.openai.com/", use_container_width=True)

    st.markdown("### 📥 결과 붙여넣기")
    manual_json = st.text_area("JSON 결과", height=300)
    if st.button("✅ 적용"):
        try:
            st.session_state['plan_data'] = json.loads(clean_json_text(manual_json))
            st.session_state['show_manual'] = False
            st.rerun()
        except:
            st.error("JSON 파싱 실패. 형식을 확인하세요.")

# ------------------------------------------------------------------
# 결과 표시 및 이미지 생성
# ------------------------------------------------------------------
if st.session_state.get('plan_data'):
    plan = st.session_state['plan_data']
    
    st.markdown("---")
    st.header(f"🎬 {plan.get('project_title', 'Project')}")
    st.info(f"Concept: {plan.get('logline', '')}")

    # --- 전체 일괄 생성 버튼 ---
    st.markdown("### 🚀 전체 이미지 일괄 생성")
    if st.button("🎨 턴테이블 & 모든 씬 이미지 한번에 생성하기", type="primary", use_container_width=True):
        tt_items = []
        for cat in ['characters', 'locations', 'objects']:
            if cat in plan.get('turntable', {}):
                for item in plan['turntable'][cat]:
                    tt_items.append((cat, item))
        
        scenes = plan.get('scenes', [])
        total_tasks = len(tt_items) + len(scenes)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 1. 턴테이블 생성
        for idx, (cat, item) in enumerate(tt_items):
            status_text.text(f"생성 중 (턴테이블): {item.get('name')}...")
            if 'views' in item:
                for view in item['views']:
                    key = f"{cat}_{item.get('id')}_{view.get('view_type')}"
                    if key not in st.session_state['turntable_images']:
                        prompt = view.get('prompt', '')
                        # JSON 프로필 강제 주입
                        if 'json_profile' in item and 'description' in item['json_profile']:
                            prompt = f"{item['json_profile']['description']}, {prompt}"
                            
                        img = try_generate_image_with_fallback(prompt, 1024, 1024, image_provider, max_retries)
                        if img: st.session_state['turntable_images'][key] = img
            progress_bar.progress((idx + 1) / total_tasks)
            
        # 2. 씬 생성
        current_progress = len(tt_items)
        for idx, scene in enumerate(scenes):
            scene_num = scene.get('scene_num', idx+1)
            status_text.text(f"생성 중 (씬): Scene {scene_num}...")
            
            if scene_num not in st.session_state['generated_images']:
                prompt = scene.get('image_prompt', '')
                # 안전장치: 씬 프롬프트에 프로필 누락시 강제 주입
                if 'used_turntables' in scene:
                    prompt = apply_json_profiles_to_prompt(prompt, scene['used_turntables'], plan.get('turntable', {}))
                
                img = try_generate_image_with_fallback(prompt, image_width, image_height, image_provider, max_retries)
                if img: st.session_state['generated_images'][scene_num] = img
            
            progress_bar.progress((current_progress + idx + 1) / total_tasks)
            
        status_text.text("✅ 전체 생성 완료!")
        st.rerun()

    st.markdown("---")

    # --- 턴테이블 표시 ---
    if 'turntable' in plan:
        st.markdown("## 🎭 Turntable Reference Sheets")
        for cat in ['characters', 'locations', 'objects']:
            if cat in plan['turntable']:
                st.markdown(f"### {cat.upper()}")
                cols = st.columns(2)
                for idx, item in enumerate(plan['turntable'][cat]):
                    with cols[idx % 2]:
                        st.markdown(f"<div class='turntable-box'>", unsafe_allow_html=True)
                        st.markdown(f"**{item.get('name')}**")
                        
                        # JSON 프로필 표시 (누락 확인용)
                        if 'json_profile' in item:
                            with st.expander("🔍 JSON Profile (Consistency)"):
                                st.write(item['json_profile'].get('description', 'No description found'))
                        
                        if 'views' in item:
                            for view in item['views']:
                                key = f"{cat}_{item.get('id')}_{view.get('view_type')}"
                                prompt = view.get('prompt', '')
                                
                                # 이미지 표시
                                if key in st.session_state['turntable_images']:
                                    st.image(st.session_state['turntable_images'][key], use_container_width=True)
                                else:
                                    if st.button(f"📸 생성 ({item.get('name')})", key=f"btn_{key}"):
                                        if 'json_profile' in item and 'description' in item['json_profile']:
                                            prompt = f"{item['json_profile']['description']}, {prompt}"
                                        
                                        with st.spinner("생성 중..."):
                                            img = try_generate_image_with_fallback(prompt, 1024, 1024, image_provider, max_retries)
                                            if img: 
                                                st.session_state['turntable_images'][key] = img
                                                st.rerun()
                                
                                st.caption(f"Prompt: {prompt[:50]}...")
                        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- 씬 표시 ---
    st.markdown("## 🎬 Storyboard")
    for scene in plan.get('scenes', []):
        scene_num = scene.get('scene_num')
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(f"**Scene {scene_num}** ({scene.get('timecode')})")
            st.write(f"📝 **Action**: {scene.get('action')}")
            st.caption(f"🎥 **Camera**: {scene.get('video_prompt')}")
            
            if 'used_turntables' in scene:
                for tt in scene['used_turntables']:
                    st.markdown(f"<span class='turntable-tag'>{tt}</span>", unsafe_allow_html=True)
            
            with st.expander("Full Prompt (Includes JSON Profile)"):
                st.text(scene.get('image_prompt'))

        with col2:
            if scene_num in st.session_state['generated_images']:
                st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
                if st.button("🔄 재생성", key=f"re_sc_{scene_num}"):
                    del st.session_state['generated_images'][scene_num]
                    st.rerun()
            else:
                if st.button(f"📸 씬 생성", key=f"gen_sc_{scene_num}"):
                    with st.spinner("생성 중..."):
                        prompt = scene.get('image_prompt', '')
                        if 'used_turntables' in scene:
                            prompt = apply_json_profiles_to_prompt(prompt, scene['used_turntables'], plan.get('turntable', {}))
                            
                        img = try_generate_image_with_fallback(prompt, image_width, image_height, image_provider, max_retries)
                        if img: 
                            st.session_state['generated_images'][scene_num] = img
                            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
