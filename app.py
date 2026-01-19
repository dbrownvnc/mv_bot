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
    
    # 무한 재시도 옵션
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
    
    # 엔진별 설명
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

# 비율 매핑
ratio_map = {
    "1:1 (Square)": (1024, 1024),
    "16:9 (Cinema)": (1024, 576),
    "9:16 (Portrait)": (576, 1024),
    "4:3 (Classic)": (1024, 768),
    "3:2 (Photo)": (1024, 683),
    "21:9 (Ultra Wide)": (1024, 439)
}

# 세션 스테이트 초기화
if 'scene_count' not in st.session_state:
    st.session_state.scene_count = 8
if 'total_duration' not in st.session_state:
    st.session_state.total_duration = 60
if 'seconds_per_scene' not in st.session_state:
    st.session_state.seconds_per_scene = 5
if 'random_topic' not in st.session_state:
    st.session_state.random_topic = ""

with st.expander("📝 프로젝트 설정 (터치하여 열기)", expanded=True):
    # 트렌드 주제 생성 버튼
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
            placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사\n\n또는 위의 '바이럴 주제 생성' 버튼을 사용하세요!"
        )
        
        # JSON 프로필 사용 옵션
        st.markdown("---")
        use_json_profiles = st.checkbox(
            "🎯 JSON 프로필 사용 (일관성 극대화)", 
            value=True,
            help="턴테이블의 상세 JSON 프로필을 모든 씬에 자동 적용하여 캐릭터/오브젝트/배경 일관성을 극대화합니다"
        )
        if use_json_profiles:
            st.caption("✅ 모든 등장 요소의 디테일한 프로필이 생성되고, 각 씬에 자동 적용됩니다")
        
        st.markdown("---")
        
        # 장르 및 스타일 선택
        col_genre1, col_genre2, col_genre3 = st.columns(3)
        
        with col_genre1:
            selected_genre = st.selectbox("🎬 영상 장르", VIDEO_GENRES, index=0)
        
        with col_genre2:
            selected_visual = st.selectbox("🎨 비주얼 스타일", VISUAL_STYLES, index=0)
        
        with col_genre3:
            selected_music = st.selectbox("🎵 음악 장르", MUSIC_GENRES, index=0)
        
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
        
        # 실시간 업데이트를 위한 컨테이너
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
                
                # 세션 스테이트 업데이트
                st.session_state.scene_count = scene_count
                st.session_state.total_duration = total_duration
                st.session_state.seconds_per_scene = seconds_per_scene
            else:
                scene_count = st.number_input("생성할 씬 개수", min_value=2, max_value=30, value=st.session_state.scene_count, step=1, key="scene_cnt")
                st.caption(f"총 **{scene_count}개** 씬")
                
                st.session_state.scene_count = scene_count
        
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

def get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json_profiles):
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
    
    json_profile_instruction = ""
    if use_json_profiles:
        json_profile_instruction = """
    
CRITICAL JSON PROFILE SYSTEM:
For MAXIMUM consistency, each turntable MUST include an EXTREMELY detailed json_profile with:

**For Characters:**
- Physical: exact age, height, weight, body type, skin tone (hex color if possible), facial structure
- Face: eye color (exact shade), eye shape, eyebrow style, nose shape, lip color/shape, cheekbone height, jawline type
- Hair: exact color (with highlights/streaks), length (in cm/inches), style, texture, how it moves
- Clothing: every piece described (brand-style if relevant), exact colors, materials, wear patterns, logos
- Accessories: jewelry (which fingers, ears), watches, bags, technology worn
- Distinctive: tattoos (exact location, size, design), scars, birthmarks, cybernetics, unique features
- Posture: how they stand, walk, move

**For Locations:**
- Architecture: exact style, materials (concrete, glass, metal), colors (hex codes), weathering
- Lighting: time of day, light sources, color temperature, shadows, atmosphere
- Weather: exact conditions, visibility, precipitation
- Details: signage, vegetation, debris, ambient elements
- Color Palette: dominant colors, accent colors, mood
- Ambience: sounds implied, smells implied, feeling

**For Objects:**
- Dimensions: exact size, weight, proportions
- Materials: primary material, secondary materials, texture, reflectivity
- Colors: exact shades, finish (matte/glossy/metallic)
- Design: shape language, brand aesthetic, wear/damage
- Function: what it does, how it's used
- Details: logos, text, buttons, screens, ornaments

THEN in scenes, reference these profiles with: "used_turntables": ["character_name", "location_name"]
And the image_prompt will AUTO-COMBINE the detailed profile + scene action.
"""
    
    return f"""
    You are a professional Music Video Director and YouTube Content Strategist specializing in EXTREME DETAIL and VISUAL CONSISTENCY.
    
    Theme: "{topic}"
    Genre: {genre}
    Visual Style: {visual_style}
    Music Genre: {music_genre}
    {json_profile_instruction}
    
    Create a comprehensive production plan with DETAILED TURNTABLES for ALL appearing elements and {scene_count} scenes in JSON format ONLY.
    
    Story Requirements: {story_instruction}
    
    JSON Structure:
    {{
      "project_title": "Creative Title (Korean)",
      "logline": "One sentence concept (Korean)",
      "youtube": {{
        "title": "Viral-optimized English title (50-60 chars) ending with '| AI Generated' in subtle way",
        "description": "Compelling English description (200-300 words) optimized for YouTube algorithm, including timestamps, key moments, and subtle AI disclosure",
        "hashtags": "trending, relevant, keywords, separated, by, commas, no, hash, symbols, 20-30, tags"
      }},
      "music": {{
        "style": "Genre and Mood (Korean)",
        "suno_prompt": "Advanced Suno AI prompt in English with [Verse], [Chorus], [Bridge] structure, BPM, key signature, mood descriptors, instrumentation details for {music_genre} genre. Make it trendy, addictive, and viral-worthy.",
        "tags": "[genre], [mood], [tempo], [style]"
      }},
      "visual_style": {{
        "description": "Visual tone in {visual_style} style (Korean)",
        "character_prompt": "Detailed English description of main character in {visual_style} aesthetic.",
        "style_tags": "{visual_style}, cinematic, {genre}"
      }},
      "turntable": {{
        "characters": [
          {{
            "id": "main_character",
            "name": "Character name (Korean)",
            "json_profile": {{
              "age": "exact age",
              "height": "in cm",
              "body_type": "specific description",
              "skin": "exact tone with hex",
              "face": {{
                "eyes": "color, shape, distinctive features",
                "eyebrows": "shape, color",
                "nose": "shape",
                "lips": "color, shape",
                "cheekbones": "height, prominence",
                "jawline": "shape"
              }},
              "hair": {{
                "color": "exact with highlights",
                "length": "exact length",
                "style": "detailed",
                "texture": "wavy/straight/curly"
              }},
              "clothing": {{
                "top": "exact description",
                "bottom": "exact description",
                "shoes": "exact description",
                "outerwear": "if any"
              }},
              "accessories": ["list all"],
              "distinctive_features": ["tattoos location/design", "scars", "cybernetics", "unique marks"]
            }},
            "prompt": "Turntable shot in {visual_style}: 360 degree character turnaround, white background, multiple angles (front/side/back/3-4), full body, USING ABOVE JSON PROFILE details..."
          }}
        ],
        "backgrounds": [
          {{
            "id": "main_location",
            "name": "Location name (Korean)",
            "json_profile": {{
              "architecture": "exact style and materials",
              "color_palette": ["primary hex", "secondary hex"],
              "lighting": {{
                "time": "exact time of day",
                "sources": ["list"],
                "color_temp": "warm/cool/neutral",
                "intensity": "bright/dim"
              }},
              "weather": "exact conditions",
              "details": ["signage", "vegetation", "objects"],
              "atmosphere": "mood description"
            }},
            "prompt": "Turntable shot in {visual_style}: environment 360 rotation, USING ABOVE JSON PROFILE..."
          }}
        ],
        "objects": [
          {{
            "id": "key_object",
            "name": "Object name (Korean)",
            "json_profile": {{
              "dimensions": "LxWxH",
              "material": "primary material",
              "colors": ["exact colors with finish"],
              "design": "exact design language",
              "details": ["logos", "text", "features"]
            }},
            "prompt": "Turntable shot in {visual_style}: 360 product view, white background, USING ABOVE JSON PROFILE..."
          }}
        ]
      }},
      "scenes": [
        {{
          "scene_num": 1,
          "timecode": "00:00-00:05",
          "action": "Scene description (Korean)",
          "camera": "Shot type (Korean)",
          "used_turntables": ["main_character", "main_location"],
          "image_prompt": "Base scene action and composition (will auto-combine with turntable JSON profiles if enabled)",
          "video_prompt": "Movement and camera motion description"
        }}
        // Create {scene_count} scenes, IDENTIFY which turntables appear in each scene
      ]
    }}
    
    CRITICAL REQUIREMENTS:
    - Create turntables for EVERY character, location, and important object that appears multiple times
    - Make json_profile EXTREMELY detailed (200+ words per character, 150+ per location)
    - In scenes, list ALL turntables used in "used_turntables" array
    - image_prompt should describe ACTION/COMPOSITION, NOT repeat full character description (that's in json_profile)
    - Ensure turntable IDs match exactly in used_turntables references
    """

def apply_json_profiles_to_prompt(base_prompt, used_turntables, turntable_data):
    """JSON 프로필을 프롬프트에 자동 적용"""
    if not used_turntables or not turntable_data:
        return base_prompt
    
    profile_parts = []
    
    # 각 턴테이블의 JSON 프로필 추출
    for tt_ref in used_turntables:
        for category in ['characters', 'backgrounds', 'objects']:
            if category in turntable_data:
                for item in turntable_data[category]:
                    if item.get('id') == tt_ref or f"{category[:-1]}_{item.get('name')}" == tt_ref:
                        if 'json_profile' in item:
                            # JSON 프로필을 텍스트로 변환
                            profile = item['json_profile']
                            profile_text = json_to_detailed_text(profile, item.get('name', ''))
                            profile_parts.append(profile_text)
                        break
    
    # 프로필 + 베이스 프롬프트 결합
    if profile_parts:
        combined = ", ".join(profile_parts) + ", " + base_prompt
        return combined
    
    return base_prompt

def json_to_detailed_text(json_profile, name=""):
    """JSON 프로필을 상세 텍스트로 변환"""
    parts = []
    
    if isinstance(json_profile, dict):
        # 캐릭터 프로필
        if 'age' in json_profile:
            parts.append(f"{json_profile.get('age', '')} year old")
        if 'height' in json_profile:
            parts.append(f"{json_profile.get('height', '')} tall")
        if 'body_type' in json_profile:
            parts.append(json_profile['body_type'])
        if 'skin' in json_profile:
            parts.append(f"{json_profile['skin']} skin")
        
        # 얼굴
        if 'face' in json_profile:
            face = json_profile['face']
            if isinstance(face, dict):
                for key, val in face.items():
                    parts.append(f"{val} {key}")
        
        # 머리
        if 'hair' in json_profile:
            hair = json_profile['hair']
            if isinstance(hair, dict):
                hair_desc = f"{hair.get('color', '')} {hair.get('texture', '')} {hair.get('style', '')} hair, {hair.get('length', '')} length"
                parts.append(hair_desc)
        
        # 의상
        if 'clothing' in json_profile:
            clothing = json_profile['clothing']
            if isinstance(clothing, dict):
                for key, val in clothing.items():
                    if val:
                        parts.append(f"wearing {val}")
        
        # 액세서리
        if 'accessories' in json_profile:
            acc = json_profile['accessories']
            if isinstance(acc, list) and acc:
                parts.append(f"with {', '.join(acc)}")
        
        # 특징
        if 'distinctive_features' in json_profile:
            feat = json_profile['distinctive_features']
            if isinstance(feat, list) and feat:
                parts.append(', '.join(feat))
        
        # 장소 프로필
        if 'architecture' in json_profile:
            parts.append(json_profile['architecture'])
        if 'color_palette' in json_profile:
            colors = json_profile['color_palette']
            if isinstance(colors, list):
                parts.append(f"color palette: {', '.join(colors)}")
        if 'lighting' in json_profile:
            lighting = json_profile['lighting']
            if isinstance(lighting, dict):
                parts.append(f"{lighting.get('time', '')} lighting, {lighting.get('color_temp', '')} tone")
        if 'weather' in json_profile:
            parts.append(json_profile['weather'])
        if 'atmosphere' in json_profile:
            parts.append(json_profile['atmosphere'])
        
        # 오브젝트 프로필
        if 'dimensions' in json_profile:
            parts.append(f"{json_profile['dimensions']} size")
        if 'material' in json_profile:
            parts.append(f"{json_profile['material']} material")
        if 'colors' in json_profile:
            colors = json_profile['colors']
            if isinstance(colors, list):
                parts.append(f"{', '.join(colors)} colored")
        if 'design' in json_profile:
            parts.append(json_profile['design'])
    
    return ", ".join([p for p in parts if p])

# ------------------------------------------------------------------
# 저장 함수들
# ------------------------------------------------------------------

def create_html_export(plan_data, images_dict=None, turntable_dict=None):
    """HTML 형식으로 전체 프로젝트 저장"""
    if images_dict is None:
        images_dict = {}
    if turntable_dict is None:
        turntable_dict = {}
        
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{plan_data['project_title']}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 15px;
                margin-bottom: 30px;
            }}
            .youtube-section {{
                background: #ff0000;
                color: white;
                padding: 30px;
                border-radius: 15px;
                margin: 30px 0;
            }}
            .section {{
                background: white;
                padding: 30px;
                border-radius: 15px;
                margin: 20px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .scene {{
                border-left: 5px solid #667eea;
                padding: 20px;
                margin: 20px 0;
                background: #f9f9f9;
            }}
            .turntable {{
                border: 3px solid #FFD700;
                padding: 20px;
                margin: 20px 0;
                background: #fffef0;
            }}
            .json-profile {{
                background: #f0f5ff;
                border: 2px solid #597ef7;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }}
            .turntable-tag {{
                display: inline-block;
                background: linear-gradient(135deg, #FFD700, #FFA500);
                color: #000;
                padding: 6px 14px;
                border-radius: 15px;
                margin: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            img {{
                max-width: 100%;
                height: auto;
                border-radius: 10px;
                margin: 10px 0;
            }}
            .prompt {{
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 15px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                overflow-x: auto;
                margin: 10px 0;
            }}
            h1, h2, h3 {{
                margin-top: 0;
            }}
            .hashtags {{
                color: #1DA1F2;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 {plan_data['project_title']}</h1>
            <p style="font-size: 1.2em;">{plan_data['logline']}</p>
            <p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
        </div>
        
        <div class="youtube-section">
            <h2>📺 YouTube Metadata</h2>
            <h3>Title:</h3>
            <p style="font-size: 1.3em; font-weight: bold;">{plan_data.get('youtube', {}).get('title', 'N/A')}</p>
            
            <h3>Description:</h3>
            <p style="white-space: pre-wrap;">{plan_data.get('youtube', {}).get('description', 'N/A')}</p>
            
            <h3>Hashtags:</h3>
            <p class="hashtags">#{plan_data.get('youtube', {}).get('hashtags', '').replace(', ', ' #')}</p>
        </div>
        
        <div class="section">
            <h2>🎵 Music Information</h2>
            <p><strong>Style:</strong> {plan_data['music']['style']}</p>
            <h3>Suno AI Prompt:</h3>
            <div class="prompt">{plan_data['music']['suno_prompt']}</div>
            {f"<p><strong>Tags:</strong> {plan_data['music'].get('tags', 'N/A')}</p>" if 'tags' in plan_data['music'] else ''}
        </div>
        
        <div class="section">
            <h2>🎨 Visual Style</h2>
            <p>{plan_data['visual_style']['description']}</p>
            <h3>Character Design:</h3>
            <div class="prompt">{plan_data['visual_style']['character_prompt']}</div>
        </div>
    """
    
    # 턴테이블
    if 'turntable' in plan_data:
        html_content += '<div class="section"><h2>🎭 Turntable References (JSON Profiles)</h2>'
        
        for category in ['characters', 'backgrounds', 'objects']:
            if category in plan_data['turntable'] and plan_data['turntable'][category]:
                html_content += f'<h3>{"👤 Characters" if category == "characters" else "🏙️ Backgrounds" if category == "backgrounds" else "📦 Objects"}</h3>'
                
                for item in plan_data['turntable'][category]:
                    tt_key = f"{category}_{item['name']}"
                    html_content += f'<div class="turntable"><h4>{item["name"]}</h4>'
                    
                    # JSON 프로필 표시
                    if 'json_profile' in item:
                        html_content += f'<div class="json-profile"><strong>JSON Profile:</strong><pre>{json.dumps(item["json_profile"], indent=2, ensure_ascii=False)}</pre></div>'
                    
                    if tt_key in turntable_dict:
                        buffered = BytesIO()
                        turntable_dict[tt_key].save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        html_content += f'<img src="data:image/png;base64,{img_str}" alt="{item["name"]}">'
                    
                    html_content += f'<div class="prompt">{item["prompt"]}</div></div>'
        
        html_content += '</div>'
    
    # 씬들
    html_content += '<div class="section"><h2>🎬 Storyboard</h2>'
    
    for scene in plan_data['scenes']:
        html_content += f'''
        <div class="scene">
            <h3>Scene {scene['scene_num']} - {scene['timecode']}</h3>
        '''
        
        # 사용된 턴테이블 태그
        if 'used_turntables' in scene and scene['used_turntables']:
            html_content += '<div style="margin: 10px 0;">'
            for tt in scene['used_turntables']:
                html_content += f'<span class="turntable-tag">🎭 {tt}</span>'
            html_content += '</div>'
        
        html_content += f'''
            <p><strong>Action:</strong> {scene['action']}</p>
            <p><strong>Camera:</strong> {scene['camera']}</p>
        '''
        
        if scene['scene_num'] in images_dict:
            buffered = BytesIO()
            images_dict[scene['scene_num']].save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            html_content += f'<img src="data:image/png;base64,{img_str}" alt="Scene {scene["scene_num"]}">'
        
        html_content += f'''
            <h4>Image Prompt:</h4>
            <div class="prompt">{scene['image_prompt']}</div>
            <h4>Video Prompt:</h4>
            <div class="prompt">{scene.get('video_prompt', 'N/A')}</div>
        </div>
        '''
    
    html_content += '''
        </div>
    </body>
    </html>
    '''
    
    return html_content

def create_json_export(plan_data):
    """JSON 형식으로 저장"""
    return json.dumps(plan_data, ensure_ascii=False, indent=2)

def create_text_export(plan_data):
    """텍스트 형식으로 저장"""
    text = f"""
{'='*80}
AI MV DIRECTOR - PROJECT EXPORT
{'='*80}

PROJECT TITLE: {plan_data['project_title']}
LOGLINE: {plan_data['logline']}
GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*80}
YOUTUBE METADATA
{'='*80}

TITLE:
{plan_data.get('youtube', {}).get('title', 'N/A')}

DESCRIPTION:
{plan_data.get('youtube', {}).get('description', 'N/A')}

HASHTAGS:
{plan_data.get('youtube', {}).get('hashtags', 'N/A')}

{'='*80}
MUSIC
{'='*80}

STYLE: {plan_data['music']['style']}

SUNO AI PROMPT:
{plan_data['music']['suno_prompt']}

{'='*80}
VISUAL STYLE
{'='*80}

{plan_data['visual_style']['description']}

CHARACTER PROMPT:
{plan_data['visual_style']['character_prompt']}

"""
    
    # 턴테이블
    if 'turntable' in plan_data:
        text += f"\n{'='*80}\nTURNTABLE REFERENCES (JSON PROFILES)\n{'='*80}\n\n"
        
        for category in ['characters', 'backgrounds', 'objects']:
            if category in plan_data['turntable'] and plan_data['turntable'][category]:
                text += f"\n{category.upper()}:\n{'-'*80}\n"
                for item in plan_data['turntable'][category]:
                    text += f"\n{item['name']}:\n"
                    if 'json_profile' in item:
                        text += f"\nJSON PROFILE:\n{json.dumps(item['json_profile'], indent=2, ensure_ascii=False)}\n"
                    text += f"\nPROMPT:\n{item['prompt']}\n\n"
    
    # 씬들
    text += f"\n{'='*80}\nSTORYBOARD\n{'='*80}\n\n"
    
    for scene in plan_data['scenes']:
        text += f"""
Scene {scene['scene_num']} - {scene['timecode']}
{'-'*80}
"""
        if 'used_turntables' in scene and scene['used_turntables']:
            text += f"USED TURNTABLES: {', '.join(scene['used_turntables'])}\n\n"
        
        text += f"""ACTION: {scene['action']}
CAMERA: {scene['camera']}

IMAGE PROMPT:
{scene['image_prompt']}

VIDEO PROMPT:
{scene.get('video_prompt', 'N/A')}

"""
    
    return text

def create_markdown_export(plan_data):
    """마크다운 형식으로 저장"""
    md_content = f"""# 🎬 {plan_data['project_title']}

> {plan_data['logline']}

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

---

## 📺 YouTube Metadata

### Title
```
{plan_data.get('youtube', {}).get('title', 'N/A')}
```

### Description
```
{plan_data.get('youtube', {}).get('description', 'N/A')}
```

### Hashtags
```
{plan_data.get('youtube', {}).get('hashtags', 'N/A')}
```

---

## 🎵 Music

**Style:** {plan_data['music']['style']}

### Suno AI Prompt
```
{plan_data['music']['suno_prompt']}
```

---

## 🎨 Visual Style

{plan_data['visual_style']['description']}

### Character Design
```
{plan_data['visual_style']['character_prompt']}
```

---

"""
    
    # 턴테이블
    if 'turntable' in plan_data:
        md_content += "## 🎭 Turntable References (JSON Profiles)\n\n"
        
        for category in ['characters', 'backgrounds', 'objects']:
            if category in plan_data['turntable'] and plan_data['turntable'][category]:
                icon = "👤" if category == "characters" else "🏙️" if category == "backgrounds" else "📦"
                md_content += f"### {icon} {category.title()}\n\n"
                
                for item in plan_data['turntable'][category]:
                    md_content += f"**{item['name']}**\n\n"
                    if 'json_profile' in item:
                        md_content += f"*JSON Profile:*\n```json\n{json.dumps(item['json_profile'], indent=2, ensure_ascii=False)}\n```\n\n"
                    md_content += f"*Prompt:*\n```\n{item['prompt']}\n```\n\n"
    
    # 씬들
    md_content += "## 🎬 Storyboard\n\n"
    
    for scene in plan_data['scenes']:
        md_content += f"### Scene {scene['scene_num']} - {scene['timecode']}\n\n"
        
        if 'used_turntables' in scene and scene['used_turntables']:
            md_content += "**Used Turntables:** "
            for tt in scene['used_turntables']:
                md_content += f"`🎭 {tt}` "
            md_content += "\n\n"
        
        md_content += f"""**Action:** {scene['action']}

**Camera:** {scene['camera']}

**Image Prompt:**
```
{scene['image_prompt']}
```

**Video Prompt:**
```
{scene.get('video_prompt', 'N/A')}
```

---

"""
    
    return md_content

def create_csv_export(plan_data):
    """CSV 형식으로 씬 정보 저장"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # 헤더
    writer.writerow(['Scene', 'Timecode', 'Used Turntables', 'Action', 'Camera', 'Image Prompt', 'Video Prompt'])
    
    # 씬 데이터
    for scene in plan_data['scenes']:
        used_tt = ', '.join(scene.get('used_turntables', [])) if 'used_turntables' in scene else ''
        writer.writerow([
            scene['scene_num'],
            scene['timecode'],
            used_tt,
            scene['action'],
            scene['camera'],
            scene['image_prompt'],
            scene.get('video_prompt', 'N/A')
        ])
    
    return output.getvalue()

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

def generate_plan_auto(topic, api_key, model_name, scene_count, options, genre, visual_style, music_genre, use_json_profiles):
    try:
        prompt = get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json_profiles)
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
    """선택된 엔진으로 이미지 생성 시도"""
    enhanced_prompt = f"{prompt}, cinematic, high quality, detailed, professional"
    
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
    else:
        endpoints = [
            {
                'name': provider,
                'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
            }
        ]
    
    fallback_endpoints = [
        {
            'name': 'Pollinations-Alt',
            'url': f"https://pollinations.ai/p/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}"
        }
    ]
    
    all_endpoints = endpoints + fallback_endpoints
    
    attempt = 0
    while attempt < max_retries:
        for endpoint in all_endpoints:
            try:
                response = requests.get(endpoint['url'], timeout=60)
                
                if response.status_code == 200 and len(response.content) > 1000:
                    img = Image.open(BytesIO(response.content))
                    if img.size[0] > 100 and img.size[1] > 100:
                        return img, endpoint['name']
            except Exception as e:
                continue
        
        attempt += 1
        if attempt < max_retries:
            time.sleep(1)
    
    return None, None

# ------------------------------------------------------------------
# 메인 실행 로직
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
if 'turntables_generated' not in st.session_state:
    st.session_state['turntables_generated'] = False
if 'use_json_profiles' not in st.session_state:
    st.session_state['use_json_profiles'] = True

# A. 실행 버튼 클릭 시
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
        st.session_state['turntables_generated'] = False
        st.session_state['use_json_profiles'] = use_json_profiles
        
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
        
        plan_container = st.empty()
        with plan_container.container():
            st.markdown("<div class='status-box'>📝 AI가 극도로 디테일한 JSON 프로필과 기획안을 작성하고 있습니다...</div>", unsafe_allow_html=True)
            
        st.session_state['plan_data'] = generate_plan_auto(
            topic, gemini_key, gemini_model, scene_count, story_opts,
            selected_genre, selected_visual, selected_music, use_json_profiles
        )
        
        if st.session_state['plan_data']:
            plan = st.session_state['plan_data']
            st.session_state['prompts_generated'] = True
            
            with plan_container.container():
                st.markdown("<div class='status-box'>✅ 디테일한 JSON 프로필 및 기획안 생성 완료!</div>", unsafe_allow_html=True)
                st.subheader(f"🎥 {plan['project_title']}")
                st.info(plan['logline'])
                
                if 'youtube' in plan:
                    with st.expander("📺 YouTube 메타데이터 미리보기", expanded=False):
                        st.markdown(f"**제목:** {plan['youtube']['title']}")
                        st.markdown("**설명:**")
                        st.text(plan['youtube']['description'])
                        st.markdown(f"**해시태그:** #{plan['youtube']['hashtags'].replace(', ', ' #')}")
                
                # 턴테이블 JSON 프로필 미리보기
                if 'turntable' in plan:
                    st.markdown("---")
                    st.markdown("### 🎭 턴테이블 JSON 프로필 미리보기")
                    
                    turntable = plan['turntable']
                    
                    if turntable.get('characters'):
                        st.markdown("**👤 캐릭터 프로필**")
                        for char in turntable['characters']:
                            with st.expander(f"🎭 {char['name']} (ID: {char.get('id', 'N/A')})", expanded=False):
                                if 'json_profile' in char:
                                    st.markdown("<div class='json-profile-box'>", unsafe_allow_html=True)
                                    st.json(char['json_profile'])
                                    st.markdown("</div>", unsafe_allow_html=True)
                                st.code(char['prompt'], language="text")
                    
                    if turntable.get('backgrounds'):
                        st.markdown("**🏙️ 배경 프로필**")
                        for bg in turntable['backgrounds']:
                            with st.expander(f"🏙️ {bg['name']} (ID: {bg.get('id', 'N/A')})", expanded=False):
                                if 'json_profile' in bg:
                                    st.markdown("<div class='json-profile-box'>", unsafe_allow_html=True)
                                    st.json(bg['json_profile'])
                                    st.markdown("</div>", unsafe_allow_html=True)
                                st.code(bg['prompt'], language="text")
                    
                    if turntable.get('objects'):
                        st.markdown("**📦 오브젝트 프로필**")
                        for obj in turntable['objects']:
                            with st.expander(f"📦 {obj['name']} (ID: {obj.get('id', 'N/A')})", expanded=False):
                                if 'json_profile' in obj:
                                    st.markdown("<div class='json-profile-box'>", unsafe_allow_html=True)
                                    st.json(obj['json_profile'])
                                    st.markdown("</div>", unsafe_allow_html=True)
                                st.code(obj['prompt'], language="text")
                
                # 씬 프롬프트 미리보기
                st.markdown("---")
                st.markdown("### 📝 씬별 사용 턴테이블")
                
                for scene in plan['scenes']:
                    with st.expander(f"🎬 Scene {scene['scene_num']} - {scene['action'][:50]}...", expanded=False):
                        st.caption(f"⏱️ {scene['timecode']}")
                        
                        # 사용된 턴테이블 표시
                        if 'used_turntables' in scene and scene['used_turntables']:
                            st.markdown("**🎭 사용된 턴테이블:**")
                            for tt in scene['used_turntables']:
                                st.markdown(f"<span class='turntable-tag'>{tt}</span>", unsafe_allow_html=True)
                            st.markdown("")
                        
                        st.write(f"**액션:** {scene['action']}")
                        st.write(f"**카메라:** {scene['camera']}")
                        
                        st.markdown("**베이스 프롬프트:**")
                        st.code(scene['image_prompt'], language="text")
                        
                        # JSON 프로필 적용 후 최종 프롬프트 미리보기
                        if use_json_profiles and 'used_turntables' in scene:
                            final_prompt = apply_json_profiles_to_prompt(
                                scene['image_prompt'],
                                scene['used_turntables'],
                                plan.get('turntable', {})
                            )
                            st.markdown("**📊 JSON 프로필 적용 후 최종 프롬프트:**")
                            st.code(final_prompt, language="text")
                        
                        if 'video_prompt' in scene:
                            st.markdown("**영상 프롬프트:**")
                            st.code(scene['video_prompt'], language="text")
            
            # 자동 이미지 생성
            if auto_generate:
                st.markdown("---")
                
                # 턴테이블 생성
                if 'turntable' in plan:
                    st.markdown("### 🎭 턴테이블 이미지 자동 생성")
                    
                    turntable = plan['turntable']
                    all_turntables = []
                    
                    if turntable.get('characters'):
                        for char in turntable['characters']:
                            all_turntables.append(('characters', char))
                    if turntable.get('backgrounds'):
                        for bg in turntable['backgrounds']:
                            all_turntables.append(('backgrounds', bg))
                    if turntable.get('objects'):
                        for obj in turntable['objects']:
                            all_turntables.append(('objects', obj))
                    
                    if all_turntables:
                        progress_bar_tt = st.progress(0)
                        status_container_tt = st.container()
                        
                        for idx, (category, tt_item) in enumerate(all_turntables):
                            tt_key = f"{category}_{tt_item['name']}"
                            
                            with status_container_tt:
                                st.markdown(f"<div class='status-box'>🎭 {tt_item['name']} 턴테이블 생성 중... ({idx+1}/{len(all_turntables)})</div>", unsafe_allow_html=True)
                            
                            # JSON 프로필을 프롬프트에 적용
                            final_tt_prompt = tt_item['prompt']
                            if use_json_profiles and 'json_profile' in tt_item:
                                json_text = json_to_detailed_text(tt_item['json_profile'], tt_item['name'])
                                final_tt_prompt = f"{json_text}, {final_tt_prompt}"
                            
                            img, provider = try_generate_image_with_fallback(
                                final_tt_prompt,
                                1024,
                                1024,
                                image_provider,
                                max_retries=max_retries
                            )
                            
                            if img:
                                st.session_state['turntable_images'][tt_key] = img
                                st.session_state['turntable_status'][tt_key] = f"✅ 성공 ({provider})"
                                st.toast(f"✅ {tt_item['name']} 완료!")
                            else:
                                st.session_state['turntable_status'][tt_key] = "❌ 생성 실패"
                            
                            progress_bar_tt.progress((idx + 1) / len(all_turntables))
                            time.sleep(0.3)
                        
                        st.session_state['turntables_generated'] = True
                        st.markdown("<div class='status-box'>✅ 턴테이블 생성 완료!</div>", unsafe_allow_html=True)
                        time.sleep(1)
                
                # 씬 이미지 생성
                st.markdown("### 🎨 씬 이미지 자동 생성 (JSON 프로필 적용)")
                total_scenes = len(plan['scenes'])
                
                progress_bar = st.progress(0)
                status_container = st.container()
                
                for idx, scene in enumerate(plan['scenes']):
                    scene_num = scene['scene_num']
                    
                    with status_container:
                        st.markdown(f"<div class='status-box'>🎬 Scene {scene_num} 이미지 생성 중... ({idx+1}/{total_scenes})</div>", unsafe_allow_html=True)
                    
                    # JSON 프로필 적용
                    if use_json_profiles and 'used_turntables' in scene:
                        final_prompt = apply_json_profiles_to_prompt(
                            scene['image_prompt'],
                            scene['used_turntables'],
                            plan.get('turntable', {})
                        )
                    else:
                        final_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    
                    img, provider = try_generate_image_with_fallback(
                        final_prompt,
                        image_width,
                        image_height,
                        image_provider,
                        max_retries=max_retries
                    )
                    
                    if img:
                        st.session_state['generated_images'][scene_num] = img
                        st.session_state['image_status'][scene_num] = f"✅ 성공 ({provider})"
                        st.toast(f"✅ Scene {scene_num} 완료!")
                    else:
                        st.session_state['image_status'][scene_num] = "❌ 생성 실패"
                        st.warning(f"⚠️ Scene {scene_num} 생성 실패")
                    
                    progress_bar.progress((idx + 1) / total_scenes)
                    time.sleep(0.3)
                
                st.markdown("<div class='status-box'>✅ 모든 이미지 생성 완료!</div>", unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
        else:
            plan_container.markdown("<div class='error-box'>❌ 기획안 생성 실패</div>", unsafe_allow_html=True)

# B. 수동 모드는 기존과 동일하므로 생략 (필요시 위 코드와 동일하게 작성)

# ------------------------------------------------------------------
# 4. 결과 표시
# ------------------------------------------------------------------

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    use_json = st.session_state.get('use_json_profiles', True)
    
    st.markdown("---")
    
    # 프롬프트만 저장
    st.markdown("### 💾 프롬프트 & JSON 프로필 저장 (이미지 없이)")
    st.caption("⚡ 이미지 생성 전에도 모든 프로필과 설정을 저장할 수 있습니다!")
    
    col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
    
    with col_p1:
        html_prompt = create_html_export(plan)
        st.download_button(
            label="📄 HTML",
            data=html_prompt,
            file_name=f"{plan['project_title']}_prompts.html",
            mime="text/html",
            use_container_width=True
        )
    
    with col_p2:
        json_prompt = create_json_export(plan)
        st.download_button(
            label="📋 JSON",
            data=json_prompt,
            file_name=f"{plan['project_title']}_prompts.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_p3:
        txt_prompt = create_text_export(plan)
        st.download_button(
            label="📝 TXT",
            data=txt_prompt,
            file_name=f"{plan['project_title']}_prompts.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_p4:
        md_prompt = create_markdown_export(plan)
        st.download_button(
            label="📑 MD",
            data=md_prompt,
            file_name=f"{plan['project_title']}_prompts.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    with col_p5:
        csv_prompt = create_csv_export(plan)
        st.download_button(
            label="📊 CSV",
            data=csv_prompt,
            file_name=f"{plan['project_title']}_scenes.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # YouTube 메타데이터
    if 'youtube' in plan:
        st.markdown("<div class='youtube-box'>", unsafe_allow_html=True)
        st.markdown("## 📺 YouTube 메타데이터")
        
        st.markdown("### 📌 제목")
        st.text_input("복사하세요", value=plan['youtube']['title'], key="yt_title", label_visibility="collapsed")
        
        st.markdown("### 📝 설명")
        st.text_area("복사하세요", value=plan['youtube']['description'], height=200, key="yt_desc", label_visibility="collapsed")
        
        st.markdown("### 🏷️ 해시태그")
        st.text_area("복사하세요", value=plan['youtube']['hashtags'], height=100, key="yt_tags", label_visibility="collapsed")
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
    
    # 음악 프롬프트
    st.markdown("### 🎵 Suno AI 음악 프롬프트")
    with st.expander("🎼 음악 생성 프롬프트", expanded=False):
        st.markdown(f"**스타일:** {plan['music']['style']}")
        st.code(plan['music']['suno_prompt'], language="text")
    
    st.markdown("---")
    
    # 이미지 포함 저장
    if st.session_state['generated_images'] or st.session_state['turntable_images']:
        st.markdown("### 💾 전체 프로젝트 저장 (이미지 포함)")
        col_save1, col_save2, col_save3 = st.columns(3)
        
        with col_save1:
            html_full = create_html_export(plan, st.session_state['generated_images'], st.session_state['turntable_images'])
            st.download_button(
                label="📄 HTML (이미지 포함)",
                data=html_full,
                file_name=f"{plan['project_title']}_full.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col_save2:
            st.download_button(
                label="📋 JSON",
                data=json_prompt,
                file_name=f"{plan['project_title']}_full.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col_save3:
            st.download_button(
                label="📝 TXT",
                data=txt_prompt,
                file_name=f"{plan['project_title']}_full.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.markdown("---")
    
    # 턴테이블 섹션
    if 'turntable' in plan:
        st.markdown("### 🎭 턴테이블 레퍼런스 (JSON 프로필)")
        
        turntable = plan['turntable']
        all_turntables = []
        
        if turntable.get('characters'):
            for char in turntable['characters']:
                all_turntables.append(('characters', char))
        if turntable.get('backgrounds'):
            for bg in turntable['backgrounds']:
                all_turntables.append(('backgrounds', bg))
        if turntable.get('objects'):
            for obj in turntable['objects']:
                all_turntables.append(('objects', obj))
        
        if all_turntables:
            if st.button("🔄 모든 턴테이블 재생성", use_container_width=True):
                st.session_state['turntable_images'] = {}
                st.session_state['turntable_status'] = {}
                st.rerun()
            
            for category, tt_item in all_turntables:
                tt_key = f"{category}_{tt_item['name']}"
                
                st.markdown(f"<div class='turntable-box'>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    icon = "👤" if category == "characters" else "🏙️" if category == "backgrounds" else "📦"
                    st.markdown(f"#### {icon} {tt_item['name']} (ID: {tt_item.get('id', 'N/A')})")
                with col2:
                    if tt_key in st.session_state['turntable_images']:
                        if st.button("🔄", key=f"regen_tt_{tt_key}", help="재생성"):
                            del st.session_state['turntable_images'][tt_key]
                            st.rerun()
                
                # JSON 프로필 표시
                if 'json_profile' in tt_item:
                    with st.expander("📊 JSON 프로필 상세", expanded=False):
                        st.json(tt_item['json_profile'])
                
                if tt_key in st.session_state['turntable_images']:
                    st.image(st.session_state['turntable_images'][tt_key], use_container_width=True)
                    if tt_key in st.session_state['turntable_status']:
                        st.caption(st.session_state['turntable_status'][tt_key])
                else:
                    if tt_key in st.session_state['turntable_status']:
                        st.markdown(f"<div class='error-box'>{st.session_state['turntable_status'][tt_key]}</div>", unsafe_allow_html=True)
                    
                    if st.button(f"📸 생성", key=f"gen_tt_{tt_key}"):
                        with st.spinner("🎨 이미지 생성 중..."):
                            final_prompt = tt_item['prompt']
                            if use_json and 'json_profile' in tt_item:
                                json_text = json_to_detailed_text(tt_item['json_profile'], tt_item['name'])
                                final_prompt = f"{json_text}, {final_prompt}"
                            
                            img, provider = try_generate_image_with_fallback(
                                final_prompt,
                                1024,
                                1024,
                                image_provider,
                                max_retries=max_retries
                            )
                            
                            if img:
                                st.session_state['turntable_images'][tt_key] = img
                                st.session_state['turntable_status'][tt_key] = f"✅ 성공 ({provider})"
                                st.rerun()
                            else:
                                st.session_state['turntable_status'][tt_key] = "❌ 생성 실패"
                                st.error("생성 실패")
                
                with st.expander("📝 프롬프트"):
                    st.code(tt_item['prompt'], language="text")
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # 스토리보드
    st.markdown("### 🖼️ 스토리보드")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 모든 씬 재생성", use_container_width=True):
            st.session_state['generated_images'] = {}
            st.session_state['image_status'] = {}
            st.rerun()
    with col_btn2:
        if st.button("📋 프롬프트 모두 보기", use_container_width=True):
            for scene in plan['scenes']:
                with st.expander(f"Scene {scene['scene_num']}", expanded=True):
                    if use_json and 'used_turntables' in scene:
                        final = apply_json_profiles_to_prompt(scene['image_prompt'], scene['used_turntables'], plan.get('turntable', {}))
                        st.code(final, language="text")
                    else:
                        st.code(scene['image_prompt'], language="text")

    for scene in plan['scenes']:
        scene_num = scene['scene_num']
        
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"#### Scene {scene_num} - {scene['timecode']}")
            
            # 사용된 턴테이블 태그
            if 'used_turntables' in scene and scene['used_turntables']:
                for tt in scene['used_turntables']:
                    st.markdown(f"<span class='turntable-tag'>🎭 {tt}</span>", unsafe_allow_html=True)
        
        with col2:
            if scene_num in st.session_state['generated_images']:
                if st.button("🔄", key=f"regen_{scene_num}", help="재생성"):
                    del st.session_state['generated_images'][scene_num]
                    st.rerun()
        
        if scene_num in st.session_state['generated_images']:
            st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
            if scene_num in st.session_state['image_status']:
                st.caption(st.session_state['image_status'][scene_num])
        else:
            if scene_num in st.session_state['image_status']:
                st.markdown(f"<div class='error-box'>{st.session_state['image_status'][scene_num]}</div>", unsafe_allow_html=True)
            
            if st.button(f"📸 촬영 (Scene {scene_num})", key=f"gen_{scene_num}"):
                with st.spinner("🎨 이미지 생성 중..."):
                    if use_json and 'used_turntables' in scene:
                        final_prompt = apply_json_profiles_to_prompt(
                            scene['image_prompt'],
                            scene['used_turntables'],
                            plan.get('turntable', {})
                        )
                    else:
                        final_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    
                    img, provider = try_generate_image_with_fallback(
                        final_prompt,
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
                        st.error("생성 실패")

        st.write(f"**액션:** {scene['action']}")
        st.write(f"**카메라:** {scene['camera']}")
        
        with st.expander("📝 프롬프트 상세"):
            st.markdown("**베이스 프롬프트:**")
            st.code(scene['image_prompt'], language="text")
            
            if use_json and 'used_turntables' in scene:
                st.markdown("**📊 JSON 프로필 적용 후 최종 프롬프트:**")
                final = apply_json_profiles_to_prompt(scene['image_prompt'], scene['used_turntables'], plan.get('turntable', {}))
                st.code(final, language="text")
            
            if 'video_prompt' in scene:
                st.markdown("**영상 프롬프트:**")
                st.code(scene['video_prompt'], language="text")
            
        st.markdown("</div>", unsafe_allow_html=True)
