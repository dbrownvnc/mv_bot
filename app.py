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
        background-color: #fff9e6;
        border: 2px solid #FFD700;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .youtube-box {
        background-color: #ffe6e6;
        border: 2px solid #FF0000;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
    .trend-box {
        background-color: #e6f7ff;
        border: 2px solid #1890ff;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    }
    .json-profile-box {
        background-color: #f0f5ff;
        border: 2px solid #597ef7;
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
        font-size: 12px;
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

# --- 유튜브 트렌드 알고리즘 ---
TRENDING_KEYWORDS = {
    "emotions": ["heartbreak", "hope", "nostalgia", "euphoria", "melancholy", "rage", "peace", "anxiety", "joy", "loneliness"],
    "settings": ["neon city", "abandoned subway", "rooftop at dawn", "underwater palace", "desert highway", "floating islands", "dystopian Tokyo", "cyberpunk Seoul", "ancient temple", "space station"],
    "characters": ["lonely hacker", "rebel artist", "time traveler", "android musician", "street dancer", "wandering poet", "revenge seeker", "fallen angel", "lost astronaut", "phantom thief"],
    "aesthetics": ["retro 80s", "vaporwave dreams", "dark academia", "y2k nostalgia", "minimalist void", "baroque luxury", "glitch art", "neon noir", "pastel goth", "cyberpunk"],
    "actions": ["running through rain", "dancing in fire", "flying over city", "drowning in memories", "breaking free", "searching for light", "falling through time", "rising from ashes", "chasing shadows", "embracing the void"],
    "times": ["midnight", "golden hour", "endless night", "frozen moment", "parallel timeline", "infinite loop", "last sunrise", "first snowfall", "summer's end", "dawn of chaos"],
    "trends_2025": ["AI awakening", "metaverse escape", "climate dystopia", "gen-z rebellion", "digital detox", "virtual romance", "blockchain dreams", "quantum love", "hologram memories", "synthetic emotions"]
}

def generate_trending_topic():
    """유튜브 트렌드 기반 랜덤 주제 생성"""
    templates = [
        "{character} experiencing {emotion} in a {setting} during {time}, {aesthetic} style, {action}",
        "{emotion} journey of a {character} in {setting}, {aesthetic} vibes, {trend}",
        "{action} through a {setting} at {time}, feeling {emotion}, {aesthetic} aesthetic",
        "{character} {action} in a {aesthetic} {setting}, exploring themes of {emotion} and {trend}",
        "A story of {emotion} and {trend}, featuring a {character} in a {setting} during {time}"
    ]
    
    template = random.choice(templates)
    
    topic = template.format(
        emotion=random.choice(TRENDING_KEYWORDS["emotions"]),
        setting=random.choice(TRENDING_KEYWORDS["settings"]),
        character=random.choice(TRENDING_KEYWORDS["characters"]),
        aesthetic=random.choice(TRENDING_KEYWORDS["aesthetics"]),
        action=random.choice(TRENDING_KEYWORDS["actions"]),
        time=random.choice(TRENDING_KEYWORDS["times"]),
        trend=random.choice(TRENDING_KEYWORDS["trends_2025"])
    )
    
    return topic

def get_viral_topic_with_ai(api_key, model_name):
    """AI를 사용하여 바이럴 주제 생성"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        prompt = """Generate ONE highly viral, trendy music video concept for 2025 YouTube.

Requirements:
- Emotionally compelling and visually striking
- Incorporates current trends: AI, nostalgia, mental health, climate, Gen-Z culture
- Cinematic and shareable
- 1-2 sentences maximum

Format: Just the concept, no explanation.

Example: "A lonely AI artist painting holographic memories in an abandoned metaverse gallery at midnight, searching for the last human connection before the digital apocalypse"
"""
        
        response = model.generate_content(prompt)
        return response.text.strip().strip('"')
    except:
        return generate_trending_topic()

# --- API 키 로드 ---
def get_api_key(key_name):
    if key_name in st.secrets: return st.secrets[key_name]
    elif os.getenv(key_name): return os.getenv(key_name)
    return None

# --- 장르 및 스타일 옵션 ---
VIDEO_GENRES = [
    "Action/Thriller", "Sci-Fi", "Fantasy", "Horror", "Drama", 
    "Romance", "Comedy", "Mystery", "Noir", "Cyberpunk",
    "Post-Apocalyptic", "Western", "Historical", "Documentary Style",
    "Music Video", "Abstract/Experimental", "Anime Style", "Surreal"
]

VISUAL_STYLES = [
    "Photorealistic/Cinematic", "Anime/Manga", "3D Animation", 
    "2D Animation", "Stop Motion", "Watercolor", "Oil Painting",
    "Comic Book", "Pixel Art", "Minimalist", "Baroque",
    "Impressionist", "Cyberpunk Neon", "Dark Fantasy", 
    "Pastel Dreamy", "Black & White", "Retro 80s", "Vaporwave"
]

MUSIC_GENRES = [
    "Pop", "Rock", "Hip-Hop/Rap", "Electronic/EDM", "R&B/Soul",
    "Jazz", "Classical", "Country", "Metal", "Indie",
    "K-Pop", "Lo-Fi", "Trap", "House", "Techno",
    "Ambient", "Synthwave", "Phonk", "Drill", "Afrobeat"
]

# --- 사이드바 (설정) ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    execution_mode = st.radio(
        "실행 방식",
        ["API 자동 실행", "수동 모드 (무제한)"],
        index=0
    )
    
    st.markdown("---")

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
    
    st.subheader("🎨 이미지 생성 설정")
    
    auto_generate = st.checkbox("프로젝트 생성시 자동 이미지 생성", value=True)
    infinite_retry = st.checkbox("생성 실패시 무한 재시도", value=False)
    
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
    
    engine_info = {
        "Pollinations Turbo (초고속) ⚡": "✨ 1-2초 생성, 무료, 무제한",
        "Pollinations Flux (고품질)": "✨ 고품질, 3-5초, 무료",
        "Hugging Face Schnell (빠름)": "✨ 빠른 생성, 무료",
        "Image.AI (무제한)": "✨ 완전 무제한",
        "Segmind (안정)": "✨ 안정적 (기본 추천)"
    }
    st.caption(engine_info[image_provider])
    
    if not infinite_retry:
        max_retries = st.slider("생성 실패시 재시도 횟수", 1, 10, 3)
    else:
        max_retries = 999
        st.caption("⚠️ 무한 재시도 활성화")

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

ratio_map = {
    "1:1 (Square)": (1024, 1024),
    "16:9 (Cinema)": (1024, 576),
    "9:16 (Portrait)": (576, 1024),
    "4:3 (Classic)": (1024, 768),
    "3:2 (Photo)": (1024, 683),
    "21:9 (Ultra Wide)": (1024, 439)
}

if 'scene_count' not in st.session_state:
    st.session_state.scene_count = 8
if 'total_duration' not in st.session_state:
    st.session_state.total_duration = 60
if 'seconds_per_scene' not in st.session_state:
    st.session_state.seconds_per_scene = 5
if 'random_topic' not in st.session_state:
    st.session_state.random_topic = ""

with st.expander("📝 프로젝트 설정 (터치하여 열기)", expanded=True):
    st.markdown("<div class='trend-box'>", unsafe_allow_html=True)
    st.markdown("### 🔥 바이럴 주제 생성기")
    
    col_trend1, col_trend2 = st.columns(2)
    
    with col_trend1:
        if st.button("🎲 랜덤 트렌드 주제 생성", use_container_width=True):
            st.session_state.random_topic = generate_trending_topic()
            st.toast("🔥 트렌디한 주제 생성 완료!")
            st.rerun()
    
    with col_trend2:
        if st.button("🤖 AI 바이럴 주제 생성", use_container_width=True):
            if gemini_key and gemini_model:
                with st.spinner("AI가 바이럴 주제를 생성 중..."):
                    st.session_state.random_topic = get_viral_topic_with_ai(gemini_key, gemini_model)
                    st.toast("🤖 AI 바이럴 주제 생성 완료!")
                    st.rerun()
            else:
                st.warning("API 키를 먼저 입력해주세요!")
    
    if st.session_state.random_topic:
        st.info(f"💡 생성된 주제: {st.session_state.random_topic}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    with st.form("project_form"):
        topic = st.text_area(
            "영상 주제를 입력하세요", 
            height=100, 
            value=st.session_state.random_topic if st.session_state.random_topic else "",
            placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사"
        )
        
        st.markdown("---")
        use_json_profiles = st.checkbox(
            "🎯 JSON 프로필 사용 (일관성 극대화)", 
            value=True,
            help="턴테이블의 상세 JSON 프로필을 모든 씬에 자동 적용"
        )
        if use_json_profiles:
            st.caption("✅ 디테일한 프로필이 생성되고 각 씬에 자동 적용됩니다")
        
        st.markdown("---")
        
        col_genre1, col_genre2, col_genre3 = st.columns(3)
        
        with col_genre1:
            selected_genre = st.selectbox("🎬 영상 장르", VIDEO_GENRES, index=0)
        
        with col_genre2:
            selected_visual = st.selectbox("🎨 비주얼 스타일", VISUAL_STYLES, index=0)
        
        with col_genre3:
            selected_music = st.selectbox("🎵 음악 장르", MUSIC_GENRES, index=0)
        
        col1, col2 = st.columns(2)
        
        with col1:
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
            duration_mode = st.radio(
                "⏱️ 런닝타임 설정",
                ["총 런닝타임", "씬 개수"],
                horizontal=True
            )
        
        duration_container = st.container()
        
        with duration_container:
            if duration_mode == "총 런닝타임":
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    total_duration = st.number_input("총 런닝타임 (초)", min_value=10, max_value=300, value=st.session_state.total_duration, step=10, key="total_dur")
                with col_d2:
                    seconds_per_scene = st.slider("컷당 길이 (초)", 3, 15, st.session_state.seconds_per_scene, key="sec_per_scene")
                
                scene_count = max(1, int(total_duration / seconds_per_scene))
                st.caption(f"→ 총 **{scene_count}개** 씬 생성")
                
                st.session_state.scene_count = scene_count
                st.session_state.total_duration = total_duration
                st.session_state.seconds_per_scene = seconds_per_scene
            else:
                scene_count = st.number_input("생성할 씬 개수", min_value=2, max_value=30, value=st.session_state.scene_count, step=1, key="scene_cnt")
                st.caption(f"총 **{scene_count}개** 씬")
                
                st.session_state.scene_count = scene_count
        
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
# 공통 함수 - 강화된 JSON 정제
# ------------------------------------------------------------------

def clean_json_text(text):
    """강화된 JSON 정제 함수"""
    # 1. 코드 블록 제거
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
    
    # 2. 줄바꿈과 공백 정리
    text = text.strip()
    
    # 3. 잘못된 쉼표 수정 (객체/배열 끝의 쉼표)
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    # 4. 주석 제거
    text = re.sub(r'//.*?\n', '\n', text)
    
    # 5. 싱글 쿼트를 더블 쿼트로
    # text = text.replace("'", '"')  # 조심스럽게 사용
    
    return text

def fix_json_syntax(text):
    """JSON 문법 자동 수정 시도"""
    try:
        # 기본 정제
        cleaned = clean_json_text(text)
        
        # 파싱 시도
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # 에러 위치 찾기
        lines = cleaned.split('\n')
        error_line = e.lineno - 1 if e.lineno else 0
        
        # 간단한 수정 시도
        if error_line < len(lines):
            # 해당 라인에 쉼표 추가 시도
            if not lines[error_line].strip().endswith(',') and not lines[error_line].strip().endswith('{') and not lines[error_line].strip().endswith('['):
                lines[error_line] = lines[error_line].rstrip() + ','
                fixed_text = '\n'.join(lines)
                try:
                    return json.loads(fixed_text)
                except:
                    pass
        
        raise e

def get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json_profiles):
    story_elements = []
    if options.get('use_arc'): story_elements.append("classic story arc")
    if options.get('use_trial'): story_elements.append("conflict and trials")
    if options.get('use_sensory'): story_elements.append("sensory descriptions")
    if options.get('use_dynamic'): story_elements.append("dynamic movement")
    if options.get('use_emotional'): story_elements.append("emotional progression")
    if options.get('use_climax'): story_elements.append("climactic moment")
    if options.get('use_symbolic'): story_elements.append("symbolic imagery")
    if options.get('use_twist'): story_elements.append("plot twist")
    
    story_instruction = ", ".join(story_elements) if story_elements else "cinematic storytelling"
    
    json_profile_instruction = ""
    if use_json_profiles:
        json_profile_instruction = """

CRITICAL: Include detailed json_profile for characters/locations/objects.
- Characters: age, height, skin, eyes, hair (color/length/style), clothing, accessories, distinctive features
- Locations: architecture, color_palette, lighting, weather, atmosphere
- Objects: dimensions, material, colors, design
Keep descriptions concise but specific (avoid overly long nested structures).
"""
    
    return f"""You are a Music Video Director. Create a production plan in VALID JSON format ONLY.

Theme: "{topic}"
Genre: {genre}, Visual: {visual_style}, Music: {music_genre}
Story: {story_instruction}
{json_profile_instruction}

CRITICAL JSON RULES:
- Use ONLY double quotes for strings
- NO trailing commas before }} or ]]
- NO comments (//)
- Ensure all brackets match
- Keep json_profile structures simple

Return ONLY this JSON structure:
{{
  "project_title": "Title (Korean)",
  "logline": "Concept (Korean)",
  "youtube": {{
    "title": "English title ending with | AI Generated",
    "description": "200-300 words SEO description",
    "hashtags": "keyword, separated, by, commas"
  }},
  "music": {{
    "style": "Genre and mood (Korean)",
    "suno_prompt": "Suno AI prompt with [Verse], [Chorus], [Bridge], BPM, key",
    "tags": "[genre], [mood]"
  }},
  "visual_style": {{
    "description": "{visual_style} style (Korean)",
    "character_prompt": "Main character in {visual_style}",
    "style_tags": "{visual_style}, {genre}"
  }},
  "turntable": {{
    "characters": [
      {{
        "id": "main_char",
        "name": "Name (Korean)",
        "json_profile": {{"age": "25", "hair": "silver long", "eyes": "cyan"}},
        "prompt": "360 character turnaround, {visual_style}"
      }}
    ],
    "backgrounds": [
      {{
        "id": "main_location",
        "name": "Name (Korean)",
        "json_profile": {{"lighting": "neon night", "atmosphere": "rainy"}},
        "prompt": "360 environment, {visual_style}"
      }}
    ],
    "objects": []
  }},
  "scenes": [
    {{
      "scene_num": 1,
      "timecode": "00:00-00:05",
      "action": "Scene (Korean)",
      "camera": "Shot (Korean)",
      "used_turntables": ["main_char", "main_location"],
      "image_prompt": "Scene action",
      "video_prompt": "Camera movement"
    }}
  ]
}}

Generate {scene_count} scenes. Ensure VALID JSON syntax."""

def apply_json_profiles_to_prompt(base_prompt, used_turntables, turntable_data):
    """JSON 프로필을 프롬프트에 자동 적용"""
    if not used_turntables or not turntable_data:
        return base_prompt
    
    profile_parts = []
    
    for tt_ref in used_turntables:
        for category in ['characters', 'backgrounds', 'objects']:
            if category in turntable_data:
                for item in turntable_data[category]:
                    if item.get('id') == tt_ref or f"{category[:-1]}_{item.get('name')}" == tt_ref:
                        if 'json_profile' in item:
                            profile_text = json_to_detailed_text(item['json_profile'], item.get('name', ''))
                            profile_parts.append(profile_text)
                        break
    
    if profile_parts:
        combined = ", ".join(profile_parts) + ", " + base_prompt
        return combined
    
    return base_prompt

def json_to_detailed_text(json_profile, name=""):
    """JSON 프로필을 상세 텍스트로 변환"""
    parts = []
    
    if isinstance(json_profile, dict):
        # 캐릭터
        if 'age' in json_profile:
            parts.append(f"{json_profile.get('age', '')} year old")
        if 'height' in json_profile:
            parts.append(f"{json_profile.get('height', '')} tall")
        if 'skin' in json_profile:
            parts.append(f"{json_profile['skin']} skin")
        
        # 얼굴/머리
        if 'eyes' in json_profile:
            parts.append(f"{json_profile['eyes']} eyes")
        if 'hair' in json_profile:
            parts.append(f"{json_profile['hair']} hair")
        
        # 의상
        if 'clothing' in json_profile:
            parts.append(f"wearing {json_profile['clothing']}")
        
        # 장소
        if 'lighting' in json_profile:
            parts.append(f"{json_profile['lighting']} lighting")
        if 'atmosphere' in json_profile:
            parts.append(json_profile['atmosphere'])
        
        # 오브젝트
        if 'material' in json_profile:
            parts.append(f"{json_profile['material']} material")
    
    return ", ".join([p for p in parts if p])

# 나머지 저장 함수들은 이전과 동일 (생략)
def create_json_export(plan_data):
    return json.dumps(plan_data, ensure_ascii=False, indent=2)

# ------------------------------------------------------------------
# API 실행 로직 - 강화된 에러 핸들링
# ------------------------------------------------------------------

def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    fallback_chain = [start_model, "gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", "gemini-1.0-pro"]
    
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            time.sleep(1) 
            return response.text, model_name 
        except Exception as e:
            time.sleep(0.5)
            continue
    
    raise Exception("All models failed")

def generate_plan_auto(topic, api_key, model_name, scene_count, options, genre, visual_style, music_genre, use_json_profiles):
    """강화된 JSON 파싱 with 재시도"""
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            prompt = get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json_profiles)
            response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
            
            # 강화된 JSON 파싱
            try:
                plan_data = fix_json_syntax(response_text)
                st.toast(f"✅ 기획 생성 완료 (Model: {used_model}, Attempt: {attempt+1})")
                return plan_data
            except json.JSONDecodeError as e:
                if attempt < max_attempts - 1:
                    st.warning(f"JSON 파싱 실패 (시도 {attempt+1}/{max_attempts}). 재시도 중...")
                    time.sleep(2)
                    continue
                else:
                    # 마지막 시도에서 실패시 에러 상세 표시
                    st.error(f"JSON 파싱 실패: {str(e)}")
                    with st.expander("❌ 생성된 응답 보기 (디버깅용)"):
                        st.code(response_text, language="text")
                    raise
                    
        except Exception as e:
            if attempt < max_attempts - 1:
                st.warning(f"생성 실패 (시도 {attempt+1}/{max_attempts}). 재시도 중...")
                time.sleep(2)
            else:
                st.error(f"기획안 생성 실패: {e}")
                return None
    
    return None

# 이미지 생성 함수는 동일
def try_generate_image_with_fallback(prompt, width, height, provider, max_retries=3):
    enhanced_prompt = f"{prompt}, cinematic, high quality, detailed, professional"
    
    endpoints = [{
        'name': provider,
        'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
    }]
    
    attempt = 0
    while attempt < max_retries:
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint['url'], timeout=60)
                if response.status_code == 200 and len(response.content) > 1000:
                    img = Image.open(BytesIO(response.content))
                    if img.size[0] > 100 and img.size[1] > 100:
                        return img, endpoint['name']
            except:
                continue
        attempt += 1
        if attempt < max_retries:
            time.sleep(1)
    
    return None, None

# ------------------------------------------------------------------
# 세션 스테이트 초기화
# ------------------------------------------------------------------

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {}
if 'turntable_images' not in st.session_state:
    st.session_state['turntable_images'] = {}
if 'use_json_profiles' not in st.session_state:
    st.session_state['use_json_profiles'] = True

# ------------------------------------------------------------------
# 메인 실행
# ------------------------------------------------------------------

if submit_btn and execution_mode == "API 자동 실행":
    if not gemini_key or not topic:
        st.warning("API Key와 주제를 입력해주세요.")
    else:
        st.session_state.clear()
        st.session_state['use_json_profiles'] = use_json_profiles
        
        story_opts = {
            'use_arc': use_arc, 'use_trial': use_trial,
            'use_sensory': use_sensory, 'use_dynamic': use_dynamic,
            'use_emotional': use_emotional, 'use_climax': use_climax,
            'use_symbolic': use_symbolic, 'use_twist': use_twist
        }
        
        with st.spinner("📝 AI가 기획안을 작성하고 있습니다..."):
            st.session_state['plan_data'] = generate_plan_auto(
                topic, gemini_key, gemini_model, scene_count, story_opts,
                selected_genre, selected_visual, selected_music, use_json_profiles
            )
        
        if st.session_state['plan_data']:
            st.success("✅ 기획안 생성 완료!")
            st.rerun()

# 결과 표시 (plan_data가 있을 때)
if st.session_state.get('plan_data'):
    plan = st.session_state['plan_data']
    
    st.markdown("---")
    st.markdown("### 💾 프로젝트 저장")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📋 JSON 다운로드",
            data=create_json_export(plan),
            file_name=f"{plan.get('project_title', 'project')}.json",
            mime="application/json"
        )
    
    st.markdown("---")
    
    # YouTube 정보
    if 'youtube' in plan:
        st.markdown("## 📺 YouTube 메타데이터")
        st.text_input("제목", value=plan['youtube'].get('title', ''), key="yt_t")
        st.text_area("설명", value=plan['youtube'].get('description', ''), key="yt_d", height=150)
        st.text_input("해시태그", value=plan['youtube'].get('hashtags', ''), key="yt_h")
    
    st.markdown("---")
    
    # 턴테이블
    if 'turntable' in plan:
        st.markdown("### 🎭 턴테이블")
        for cat in ['characters', 'backgrounds', 'objects']:
            if cat in plan['turntable']:
                for item in plan['turntable'][cat]:
                    with st.expander(f"{item.get('name', 'N/A')}"):
                        if 'json_profile' in item:
                            st.json(item['json_profile'])
                        st.code(item.get('prompt', ''))
    
    # 씬
    st.markdown("### 🎬 씬")
    for scene in plan.get('scenes', []):
        with st.expander(f"Scene {scene.get('scene_num', '?')}"):
            st.write(f"**액션:** {scene.get('action', '')}")
            if 'used_turntables' in scene:
                st.write(f"**턴테이블:** {', '.join(scene['used_turntables'])}")
            st.code(scene.get('image_prompt', ''))
