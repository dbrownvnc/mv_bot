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
    .stImage {
        max-height: 400px;
    }
    .stImage img {
        max-height: 400px;
        object-fit: contain;
    }
</style>
""", unsafe_allow_html=True)

# --- 트렌드 키워드 ---
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
    templates = [
        "{character} experiencing {emotion} in a {setting} during {time}, {aesthetic} style, {action}",
        "{emotion} journey of a {character} in {setting}, {aesthetic} vibes, {trend}",
        "{action} through a {setting} at {time}, feeling {emotion}, {aesthetic} aesthetic",
    ]
    template = random.choice(templates)
    return template.format(
        emotion=random.choice(TRENDING_KEYWORDS["emotions"]),
        setting=random.choice(TRENDING_KEYWORDS["settings"]),
        character=random.choice(TRENDING_KEYWORDS["characters"]),
        aesthetic=random.choice(TRENDING_KEYWORDS["aesthetics"]),
        action=random.choice(TRENDING_KEYWORDS["actions"]),
        time=random.choice(TRENDING_KEYWORDS["times"]),
        trend=random.choice(TRENDING_KEYWORDS["trends_2025"])
    )

def get_viral_topic_with_ai(api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Generate ONE viral music video concept (1-2 sentences).")
        return response.text.strip().strip('"')
    except:
        return generate_trending_topic()

# --- API 키 ---
def get_api_key(key_name):
    if key_name in st.secrets: return st.secrets[key_name]
    elif os.getenv(key_name): return os.getenv(key_name)
    return None

# --- 장르/스타일 ---
VIDEO_GENRES = ["Action/Thriller", "Sci-Fi", "Fantasy", "Horror", "Drama", "Romance", "Comedy", "Mystery", "Noir", "Cyberpunk", "Post-Apocalyptic", "Western", "Historical", "Music Video", "Abstract/Experimental", "Anime Style", "Surreal"]
VISUAL_STYLES = ["Photorealistic/Cinematic", "Anime/Manga", "3D Animation", "2D Animation", "Stop Motion", "Watercolor", "Oil Painting", "Comic Book", "Pixel Art", "Minimalist", "Baroque", "Impressionist", "Cyberpunk Neon", "Dark Fantasy", "Pastel Dreamy", "Black & White", "Retro 80s", "Vaporwave"]
MUSIC_GENRES = ["Pop", "Rock", "Hip-Hop/Rap", "Electronic/EDM", "R&B/Soul", "Jazz", "Classical", "Country", "Metal", "Indie", "K-Pop", "Lo-Fi", "Trap", "House", "Techno", "Ambient", "Synthwave", "Phonk", "Drill", "Afrobeat"]

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
        model_options = ["gemini-1.5-flash", "gemini-2.0-flash-lite-preview-02-05", "gemini-1.5-pro", "gemini-1.0-pro"]
        gemini_model = st.selectbox("모델", model_options, index=0, label_visibility="collapsed")
    
    st.markdown("---")
    st.subheader("🎨 이미지 생성")
    auto_generate = st.checkbox("자동 이미지 생성", value=True)
    infinite_retry = st.checkbox("무한 재시도", value=False)
    image_provider = st.selectbox("엔진", ["Segmind (안정)", "Pollinations Turbo ⚡", "Pollinations Flux"], index=0)
    
    if not infinite_retry:
        max_retries = st.slider("재시도", 1, 10, 3)
    else:
        max_retries = 999

    if st.button("🗑️ 초기화"):
        st.session_state.clear()
        st.rerun()

# --- 메인 화면 ---
st.title("🎬 AI MV Director")

ratio_map = {
    "16:9 (Cinema)": (1024, 576),
    "9:16 (Portrait)": (576, 1024),
    "1:1 (Square)": (1024, 1024),
}

if 'scene_count' not in st.session_state:
    st.session_state.scene_count = 8
if 'random_topic' not in st.session_state:
    st.session_state.random_topic = ""
if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {}
if 'turntable_images' not in st.session_state:
    st.session_state['turntable_images'] = {}

with st.expander("📝 프로젝트 설정", expanded=True):
    st.markdown("<div class='trend-box'>", unsafe_allow_html=True)
    st.markdown("### 🔥 바이럴 주제 생성")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("🎲 랜덤", use_container_width=True):
            st.session_state.random_topic = generate_trending_topic()
            st.rerun()
    with col_t2:
        if st.button("🤖 AI", use_container_width=True):
            if gemini_key:
                st.session_state.random_topic = get_viral_topic_with_ai(gemini_key, gemini_model)
                st.rerun()
            else:
                st.warning("API 키 필요")
    
    if st.session_state.random_topic:
        st.info(f"💡 {st.session_state.random_topic}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    with st.form("project_form"):
        topic = st.text_area("영상 주제", height=100, value=st.session_state.random_topic, placeholder="주제 입력 또는 위 버튼 사용")
        
        st.markdown("---")
        use_json_profiles = st.checkbox("🎯 JSON 프로필 사용 (극도 디테일)", value=True, help="100번 생성해도 똑같은 결과를 위한 초정밀 프로필")
        st.markdown("---")
        
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            selected_genre = st.selectbox("🎬 장르", VIDEO_GENRES, index=0)
        with col_g2:
            selected_visual = st.selectbox("🎨 스타일", VISUAL_STYLES, index=0)
        with col_g3:
            selected_music = st.selectbox("🎵 음악", MUSIC_GENRES, index=0)
        
        col1, col2 = st.columns(2)
        with col1:
            aspect_ratio = st.selectbox("🎞️ 비율", ["16:9 (Cinema)", "9:16 (Portrait)", "1:1 (Square)"], index=0)
            image_width, image_height = ratio_map[aspect_ratio]
        with col2:
            scene_count = st.number_input("씬 개수", min_value=2, max_value=30, value=st.session_state.scene_count, step=1)
        
        st.markdown("**📖 스토리**")
        cols = st.columns(4)
        with cols[0]:
            use_arc = st.checkbox("기승전결", value=True)
            use_sensory = st.checkbox("감각적", value=True)
        with cols[1]:
            use_trial = st.checkbox("시련", value=False)
            use_dynamic = st.checkbox("역동적", value=True)
        with cols[2]:
            use_emotional = st.checkbox("감정변화", value=True)
            use_climax = st.checkbox("클라이맥스", value=True)
        with cols[3]:
            use_symbolic = st.checkbox("상징", value=False)
            use_twist = st.checkbox("반전", value=False)
        
        submit_btn = st.form_submit_button("🚀 프로젝트 시작")

# ------------------------------------------------------------------
# 공통 함수
# ------------------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
    
    text = text.strip()
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r'//.*?\n', '\n', text)
    return text

def get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json_profiles):
    story_elements = []
    if options.get('use_arc'): story_elements.append("story arc")
    if options.get('use_sensory'): story_elements.append("sensory")
    if options.get('use_dynamic'): story_elements.append("dynamic")
    if options.get('use_emotional'): story_elements.append("emotional")
    if options.get('use_climax'): story_elements.append("climax")
    
    story_instruction = ", ".join(story_elements) if story_elements else "cinematic"
    
    json_detail = ""
    if use_json_profiles:
        json_detail = """

CRITICAL - ULTRA-DETAILED JSON PROFILES (For 100% consistency):

For CHARACTERS, include:
- physical: age (number), height_cm (exact), weight_kg, body_type, skin_tone (HEX color), skin_texture
- face: shape, eyes (color HEX, shape, size, details), eyebrows (color HEX, shape, thickness), nose, lips (color HEX, shape, size), jawline, chin
- hair: color_primary (HEX), color_secondary (HEX if highlights), length_cm (exact number), style, texture, parting, movement
- clothing: top (type, color HEX, material, details, fit), bottom (same), shoes (same with height_cm)
- accessories: list with exact descriptions and measurements
- distinctive_features: exact location, size in cm, color HEX if applicable
- posture: detailed stance description
- movement: how they move

For LOCATIONS, include:
- location_type, architecture (buildings, walls, ground, details)
- lighting: time (HH:MM), primary_source, color_temperature (Kelvin), specific colors (HEX), shadows (angle), atmosphere, reflections
- weather: condition, visibility (meters), precipitation (mm/hour), humidity (%)
- ambient_elements: list with sizes/colors
- color_palette: dominant (HEX), accent_1 (HEX), accent_2 (HEX), accent_3 (HEX)
- atmosphere: detailed mood

For OBJECTS:
- dimensions: LxWxH in cm, weight_kg, material_primary, material_secondary
- colors: primary (HEX), secondary (HEX), finish (matte/glossy/metallic %)
- design_details: shape, brand_style, wear_patterns
- functional_details: what it does, how used

Use EXACT hex colors, EXACT measurements, EXACT times."""

    suno_instruction = """

CRITICAL - SUNO AI OPTIMIZED STRUCTURE:

Create professional Suno AI prompt with this EXACT structure:

[Style: Genre, Mood, BPM (80-180), Key (e.g., E minor)]
[Vocals: Type (Male/Female/Duet), Quality (Powerful/Soft/Raspy/Ethereal), Effects (Reverb/Echo/Auto-tune)]
[Instruments: Instrument1, Instrument2, Instrument3 (minimum 3, maximum 6 specific instruments)]

[Intro]
(production note: atmospheric/building/quiet)
(specific sound: synth swell/guitar riff/drum fill)

[Verse 1]
4-6 lines of lyrics
Focus on setting/situation
Natural rhyme scheme

[Pre-Chorus]
(building intensity/tempo change)
2-4 lines transitioning to chorus
Increasing emotional intensity

[Chorus]
(powerful vocals/full instrumentation/melodic hook)
4-6 lines with memorable hook
Main emotional message
Repetitive catchy element

[Verse 2]
4-6 lines developing the story
Different perspective or progression

[Bridge]
(tempo change: slow down OR speed up OR breakdown)
4-6 lines offering new perspective
Emotional peak or introspection

[Chorus]
(explosive/full power/all instruments)
Repeat with variations or ad-libs

[Outro]
(fading/whispered/instrumental)
2-4 lines or instrumental fade
Emotional resolution
(specific ending: fade out/hard stop/echo)

RULES:
- Use () for production notes
- Use [] for section markers  
- Specify exact BPM (e.g., 120 BPM not "medium tempo")
- Name exact instruments (not "strings" but "violin, cello")
- Include vocal directions (whispered), (belted), (harmonized)
- Add sound effects where appropriate (rain), (vinyl crackle), (glitch)
"""

    return f"""You are a Music Video Director. Create ULTRA-DETAILED production plan in VALID JSON.

Theme: "{topic}"
Genre: {genre}, Visual: {visual_style}, Music: {music_genre}
Story: {story_instruction}
{json_detail}
{suno_instruction}

JSON SYNTAX RULES:
- Double quotes ONLY
- NO trailing commas
- NO comments
- All brackets must match

Return ONLY this JSON:
{{
  "project_title": "Title (Korean)",
  "logline": "Concept (Korean)",
  "youtube": {{
    "title": "Viral title | AI Generated",
    "description": "SEO description 200-300 words with timestamps",
    "hashtags": "keyword, separated, commas, no hash symbols"
  }},
  "music": {{
    "style": "Genre Mood (Korean)",
    "suno_prompt": "FULL Suno structure with [Style], [Vocals], [Instruments], [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Chorus], [Outro] with lyrics and production notes",
    "tags": "[genre], [mood], [tempo]"
  }},
  "visual_style": {{
    "description": "{visual_style} (Korean)",
    "character_prompt": "Main character {visual_style}",
    "style_tags": "{visual_style}, {genre}"
  }},
  "turntable": {{
    "characters": [
      {{
        "id": "char1",
        "name": "Name (Korean)",
        "json_profile": {{
          "physical": {{"age": 25, "height_cm": 175, "skin_tone": "#F4D2B8"}},
          "face": {{"eyes": {{"color": "#00CED1", "shape": "almond"}}}},
          "hair": {{"color_primary": "#C0C0C0", "length_cm": 60, "style": "straight layered"}},
          "clothing": {{"top": {{"type": "leather jacket", "color": "#1C1C1C", "details": "LED strips #00BFFF"}}}},
          "accessories": ["silver necklace 50cm", "fingerless gloves"],
          "distinctive_features": ["tattoo left cheek 3cm x 5cm #00BFFF", "prosthetic left arm chrome"],
          "posture": "confident upright",
          "movement": "fluid graceful"
        }},
        "prompt": "360 character turnaround, white background, {visual_style}, front/side/back/3-4 view, full body"
      }}
    ],
    "backgrounds": [
      {{
        "id": "loc1",
        "name": "Name (Korean)",
        "json_profile": {{
          "location_type": "urban alley",
          "architecture": {{"buildings": "concrete 20-30 stories", "ground": "wet asphalt #2F4F4F"}},
          "lighting": {{"time": "02:00", "color_temperature": "5000K", "neon_colors": ["#FF1493", "#00CED1"]}},
          "weather": {{"condition": "light rain", "visibility": "50m"}},
          "color_palette": {{"dominant": "#2F4F4F", "accent_1": "#00CED1", "accent_2": "#FF1493"}},
          "atmosphere": "dystopian cyberpunk"
        }},
        "prompt": "360 environment rotation, {visual_style}"
      }}
    ],
    "objects": []
  }},
  "scenes": [
    {{
      "scene_num": 1,
      "timecode": "00:00-00:05",
      "action": "Action (Korean)",
      "camera": "Shot (Korean)",
      "used_turntables": ["char1", "loc1"],
      "image_prompt": "Scene composition and action",
      "video_prompt": "Camera movement and transitions"
    }}
  ]
}}

Generate {scene_count} scenes with ultra-detailed json_profiles. Ensure VALID JSON."""

def apply_json_profiles_to_prompt(base_prompt, used_turntables, turntable_data):
    """JSON 프로필을 프롬프트에 초정밀 적용"""
    if not used_turntables or not turntable_data:
        return base_prompt
    
    profile_parts = []
    
    for tt_ref in used_turntables:
        for category in ['characters', 'backgrounds', 'objects']:
            if category in turntable_data:
                for item in turntable_data[category]:
                    if item.get('id') == tt_ref:
                        if 'json_profile' in item:
                            detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                            if detailed:
                                profile_parts.append(detailed)
                        break
    
    if profile_parts:
        return ", ".join(profile_parts) + ", " + base_prompt
    return base_prompt

def json_profile_to_ultra_detailed_text(profile):
    """JSON을 극도로 상세한 텍스트로 변환"""
    parts = []
    
    if not isinstance(profile, dict):
        return ""
    
    # 캐릭터 물리적 특징
    if 'physical' in profile:
        phys = profile['physical']
        if isinstance(phys, dict):
            if 'age' in phys: parts.append(f"{phys['age']} years old")
            if 'height_cm' in phys: parts.append(f"{phys['height_cm']}cm tall")
            if 'weight_kg' in phys: parts.append(f"{phys['weight_kg']}kg")
            if 'body_type' in phys: parts.append(phys['body_type'])
            if 'skin_tone' in phys: parts.append(f"skin tone {phys['skin_tone']}")
            if 'skin_texture' in phys: parts.append(f"{phys['skin_texture']} skin")
    
    # 얼굴
    if 'face' in profile:
        face = profile['face']
        if isinstance(face, dict):
            if 'shape' in face: parts.append(f"face shape {face['shape']}")
            
            if 'eyes' in face and isinstance(face['eyes'], dict):
                eyes = face['eyes']
                eye_desc = []
                if 'color' in eyes: eye_desc.append(f"color {eyes['color']}")
                if 'shape' in eyes: eye_desc.append(f"{eyes['shape']}")
                if 'size' in eyes: eye_desc.append(f"{eyes['size']}")
                if 'details' in eyes: eye_desc.append(eyes['details'])
                if eye_desc: parts.append(f"eyes {' '.join(eye_desc)}")
            
            if 'eyebrows' in face and isinstance(face['eyebrows'], dict):
                eb = face['eyebrows']
                if 'color' in eb or 'shape' in eb or 'thickness' in eb:
                    parts.append(f"eyebrows {eb.get('color', '')} {eb.get('shape', '')} {eb.get('thickness', '')}")
            
            if 'nose' in face: parts.append(f"nose {face['nose']}")
            
            if 'lips' in face and isinstance(face['lips'], dict):
                lips = face['lips']
                if 'color' in lips or 'shape' in lips:
                    parts.append(f"lips {lips.get('color', '')} {lips.get('shape', '')} {lips.get('size', '')}")
            
            if 'jawline' in face: parts.append(f"jawline {face['jawline']}")
            if 'chin' in face: parts.append(f"chin {face['chin']}")
    
    # 머리
    if 'hair' in profile:
        hair = profile['hair']
        if isinstance(hair, dict):
            hair_desc = []
            if 'color_primary' in hair: hair_desc.append(f"color {hair['color_primary']}")
            if 'color_secondary' in hair: hair_desc.append(f"with {hair['color_secondary']} highlights")
            if 'length_cm' in hair: hair_desc.append(f"{hair['length_cm']}cm length")
            if 'style' in hair: hair_desc.append(hair['style'])
            if 'texture' in hair: hair_desc.append(f"{hair['texture']} texture")
            if 'parting' in hair: hair_desc.append(hair['parting'])
            if 'movement' in hair: hair_desc.append(hair['movement'])
            if hair_desc: parts.append(f"hair {' '.join(hair_desc)}")
    
    # 의상
    if 'clothing' in profile:
        cloth = profile['clothing']
        if isinstance(cloth, dict):
            for piece in ['top', 'bottom', 'shoes']:
                if piece in cloth and isinstance(cloth[piece], dict):
                    item = cloth[piece]
                    item_desc = []
                    if 'type' in item: item_desc.append(item['type'])
                    if 'color' in item: item_desc.append(f"color {item['color']}")
                    if 'material' in item: item_desc.append(f"{item['material']} material")
                    if 'details' in item: item_desc.append(item['details'])
                    if 'fit' in item: item_desc.append(f"{item['fit']} fit")
                    if item_desc: parts.append(f"wearing {' '.join(item_desc)}")
    
    # 액세서리
    if 'accessories' in profile:
        acc = profile['accessories']
        if isinstance(acc, list) and acc:
            parts.append(f"accessories: {', '.join(acc)}")
    
    # 특징
    if 'distinctive_features' in profile:
        feat = profile['distinctive_features']
        if isinstance(feat, list) and feat:
            parts.append(f"distinctive features: {', '.join(feat)}")
    
    # 자세/움직임
    if 'posture' in profile:
        parts.append(f"posture {profile['posture']}")
    if 'movement' in profile:
        parts.append(f"movement {profile['movement']}")
    
    # 장소
    if 'location_type' in profile:
        parts.append(f"location type {profile['location_type']}")
    
    if 'architecture' in profile:
        arch = profile['architecture']
        if isinstance(arch, dict):
            for key, val in arch.items():
                parts.append(f"{key} {val}")
    
    if 'lighting' in profile:
        light = profile['lighting']
        if isinstance(light, dict):
            light_desc = []
            if 'time' in light: light_desc.append(f"time {light['time']}")
            if 'color_temperature' in light: light_desc.append(f"color temp {light['color_temperature']}")
            if 'neon_colors' in light and isinstance(light['neon_colors'], list):
                light_desc.append(f"neon colors {', '.join(light['neon_colors'])}")
            if 'shadows' in light: light_desc.append(f"shadows {light['shadows']}")
            if 'atmosphere' in light: light_desc.append(light['atmosphere'])
            if light_desc: parts.append(f"lighting {' '.join(light_desc)}")
    
    if 'weather' in profile:
        weather = profile['weather']
        if isinstance(weather, dict):
            weather_parts = [f"{k} {v}" for k, v in weather.items()]
            if weather_parts: parts.append(f"weather {' '.join(weather_parts)}")
    
    if 'color_palette' in profile:
        palette = profile['color_palette']
        if isinstance(palette, dict):
            colors = [f"{k}: {v}" for k, v in palette.items()]
            if colors: parts.append(f"color palette {', '.join(colors)}")
    
    if 'atmosphere' in profile:
        parts.append(f"atmosphere {profile['atmosphere']}")
    
    return ", ".join([p for p in parts if p])

def create_json_export(plan_data):
    return json.dumps(plan_data, ensure_ascii=False, indent=2)

# ------------------------------------------------------------------
# API 실행
# ------------------------------------------------------------------

def generate_with_fallback(prompt, api_key, start_model):
    genai.configure(api_key=api_key)
    models = [start_model, "gemini-1.5-flash", "gemini-1.0-pro"]
    
    for model_name in models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            time.sleep(1)
            return response.text, model_name
        except:
            time.sleep(0.5)
    raise Exception("All models failed")

def generate_plan_auto(topic, api_key, model_name, scene_count, options, genre, visual_style, music_genre, use_json):
    for attempt in range(3):
        try:
            prompt = get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json)
            response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
            
            cleaned = clean_json_text(response_text)
            plan_data = json.loads(cleaned)
            st.toast(f"✅ 생성 완료 ({used_model})")
            return plan_data
        except json.JSONDecodeError as e:
            if attempt < 2:
                st.warning(f"재시도 중... ({attempt+1}/3)")
                time.sleep(2)
            else:
                st.error(f"JSON 파싱 실패: {str(e)}")
                with st.expander("생성된 응답"):
                    st.code(response_text)
                return None
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                st.error(f"생성 실패: {e}")
                return None
    return None

def try_generate_image_with_fallback(prompt, width, height, provider, max_retries=3):
    enhanced = f"{prompt}, cinematic, high quality, professional photography"
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200 and len(response.content) > 1000:
                img = Image.open(BytesIO(response.content))
                if img.size[0] > 100:
                    return img, provider
        except:
            pass
        if attempt < max_retries - 1:
            time.sleep(1)
    return None, None

# ------------------------------------------------------------------
# 메인 실행 로직
# ------------------------------------------------------------------

if submit_btn:
    if not topic:
        st.warning("주제를 입력해주세요")
    else:
        story_opts = {
            'use_arc': use_arc, 'use_trial': use_trial,
            'use_sensory': use_sensory, 'use_dynamic': use_dynamic,
            'use_emotional': use_emotional, 'use_climax': use_climax,
            'use_symbolic': use_symbolic, 'use_twist': use_twist
        }
        
        if execution_mode == "API 자동 실행":
            if not gemini_key:
                st.warning("API Key 필요")
            else:
                # 초기화
                st.session_state.clear()
                st.session_state['use_json_profiles'] = use_json_profiles
                st.session_state['image_width'] = image_width
                st.session_state['image_height'] = image_height
                st.session_state['auto_generate'] = auto_generate
                st.session_state['image_provider'] = image_provider
                st.session_state['max_retries'] = max_retries
                
                # 1. 기획안 생성
                with st.spinner("📝 AI가 극도로 디테일한 기획안을 작성 중..."):
                    st.session_state['plan_data'] = generate_plan_auto(
                        topic, gemini_key, gemini_model, scene_count, story_opts,
                        selected_genre, selected_visual, selected_music, use_json_profiles
                    )
                
                if st.session_state['plan_data']:
                    st.success("✅ 기획안 생성 완료!")
                    
                    # 2. 자동 이미지 생성
                    if auto_generate:
                        plan = st.session_state['plan_data']
                        
                        # 턴테이블 생성
                        if 'turntable' in plan:
                            all_tt = []
                            for cat in ['characters', 'backgrounds', 'objects']:
                                if cat in plan['turntable']:
                                    for item in plan['turntable'][cat]:
                                        all_tt.append((cat, item))
                            
                            if all_tt:
                                st.markdown("### 🎭 턴테이블 자동 생성")
                                progress_tt = st.progress(0)
                                status_tt = st.empty()
                                
                                for idx, (cat, item) in enumerate(all_tt):
                                    tt_key = f"{cat}_{item.get('name', '')}"
                                    status_tt.markdown(f"<div class='status-box'>🎭 {item.get('name', '')} 생성 중... ({idx+1}/{len(all_tt)})</div>", unsafe_allow_html=True)
                                    
                                    final_prompt = item.get('prompt', '')
                                    if use_json_profiles and 'json_profile' in item:
                                        detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                                        if detailed:
                                            final_prompt = f"{detailed}, {final_prompt}"
                                    
                                    img, prov = try_generate_image_with_fallback(final_prompt, 1024, 1024, image_provider, max_retries)
                                    
                                    if img:
                                        if 'turntable_images' not in st.session_state:
                                            st.session_state['turntable_images'] = {}
                                        st.session_state['turntable_images'][tt_key] = img
                                        st.toast(f"✅ {item.get('name', '')} 완료")
                                    
                                    progress_tt.progress((idx + 1) / len(all_tt))
                                    time.sleep(0.3)
                                
                                status_tt.markdown("<div class='status-box'>✅ 턴테이블 생성 완료!</div>", unsafe_allow_html=True)
                        
                        # 씬 이미지 생성
                        if 'scenes' in plan:
                            st.markdown("### 🎬 씬 이미지 자동 생성")
                            scenes = plan['scenes']
                            progress_sc = st.progress(0)
                            status_sc = st.empty()
                            
                            for idx, scene in enumerate(scenes):
                                scene_num = scene.get('scene_num', 0)
                                status_sc.markdown(f"<div class='status-box'>🎬 Scene {scene_num} 생성 중... ({idx+1}/{len(scenes)})</div>", unsafe_allow_html=True)
                                
                                base = scene.get('image_prompt', '')
                                
                                if use_json_profiles and 'used_turntables' in scene:
                                    final = apply_json_profiles_to_prompt(base, scene['used_turntables'], plan.get('turntable', {}))
                                else:
                                    final = f"{plan.get('visual_style', {}).get('character_prompt', '')}, {base}"
                                
                                img, prov = try_generate_image_with_fallback(final, image_width, image_height, image_provider, max_retries)
                                
                                if img:
                                    if 'generated_images' not in st.session_state:
                                        st.session_state['generated_images'] = {}
                                    st.session_state['generated_images'][scene_num] = img
                                    st.toast(f"✅ Scene {scene_num} 완료")
                                
                                progress_sc.progress((idx + 1) / len(scenes))
                                time.sleep(0.3)
                            
                            status_sc.markdown("<div class='status-box'>✅ 모든 이미지 생성 완료!</div>", unsafe_allow_html=True)
                    
                    time.sleep(1)
                    st.rerun()
        
        else:  # 수동 모드
            st.session_state['manual_prompt'] = get_system_prompt(
                topic, scene_count, story_opts, 
                selected_genre, selected_visual, selected_music, use_json_profiles
            )
            st.session_state['use_json_profiles'] = use_json_profiles
            st.session_state['image_width'] = image_width
            st.session_state['image_height'] = image_height
            st.rerun()

# ------------------------------------------------------------------
# 수동 모드 UI
# ------------------------------------------------------------------

if execution_mode == "수동 모드 (무제한)" and 'manual_prompt' in st.session_state:
    st.markdown("---")
    st.markdown("<div class='manual-box'>", unsafe_allow_html=True)
    st.markdown("### 📋 수동 모드")
    
    st.markdown("**1️⃣ 프롬프트 복사**")
    st.code(st.session_state['manual_prompt'], language="text")
    
    st.link_button("🚀 Gemini 열기", "https://gemini.google.com/", use_container_width=True)
    
    st.markdown("**2️⃣ 결과 붙여넣기**")
    manual_input = st.text_area("JSON 결과", height=200, placeholder='```json\n...\n```')
    
    if st.button("✅ 결과 적용", use_container_width=True):
        if not manual_input.strip():
            st.warning("결과를 붙여넣어주세요")
        else:
            try:
                cleaned = clean_json_text(manual_input)
                st.session_state['plan_data'] = json.loads(cleaned)
                st.session_state['generated_images'] = {}
                st.session_state['turntable_images'] = {}
                st.success("✅ 로드 완료!")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"JSON 파싱 실패: {str(e)}")
            except Exception as e:
                st.error(f"오류: {e}")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 결과 표시
# ------------------------------------------------------------------

if st.session_state.get('plan_data'):
    plan = st.session_state['plan_data']
    use_json = st.session_state.get('use_json_profiles', True)
    img_width = st.session_state.get('image_width', 1024)
    img_height = st.session_state.get('image_height', 576)
    
    st.markdown("---")
    
    # 저장
    st.markdown("### 💾 저장")
    st.download_button(
        "📋 JSON 다운로드",
        data=create_json_export(plan),
        file_name=f"{plan.get('project_title', 'project')}.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.markdown("---")
    
    # YouTube
    if 'youtube' in plan:
        st.markdown("## 📺 YouTube")
        st.text_input("제목", value=plan['youtube'].get('title', ''), key="yt_t")
        st.text_area("설명", value=plan['youtube'].get('description', ''), height=150, key="yt_d")
        st.text_input("태그", value=plan['youtube'].get('hashtags', ''), key="yt_h")
    
    st.markdown("---")
    
    # 음악
    if 'music' in plan:
        st.markdown("### 🎵 Suno AI 음악")
        with st.expander("🎼 최적화된 Suno 프롬프트", expanded=False):
            st.code(plan['music'].get('suno_prompt', ''), language="text")
            st.caption(f"스타일: {plan['music'].get('style', '')}")
    
    st.markdown("---")
    
    # 턴테이블
    if 'turntable' in plan:
        st.markdown("### 🎭 턴테이블 (초정밀 JSON)")
        
        all_tt = []
        for cat in ['characters', 'backgrounds', 'objects']:
            if cat in plan['turntable']:
                for item in plan['turntable'][cat]:
                    all_tt.append((cat, item))
        
        if all_tt:
            if st.button("🔄 모든 턴테이블 재생성"):
                st.session_state['turntable_images'] = {}
                st.rerun()
            
            for cat, item in all_tt:
                tt_key = f"{cat}_{item.get('name', '')}"
                
                st.markdown(f"<div class='turntable-box'>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    icon = "👤" if cat == "characters" else "🏙️" if cat == "backgrounds" else "📦"
                    st.markdown(f"**{icon} {item.get('name', '')}** (ID: {item.get('id', '')})")
                with col2:
                    if tt_key in st.session_state.get('turntable_images', {}):
                        if st.button("🔄", key=f"r_tt_{tt_key}"):
                            del st.session_state['turntable_images'][tt_key]
                            st.rerun()
                
                if 'json_profile' in item:
                    with st.expander("📊 초정밀 JSON 프로필"):
                        st.json(item['json_profile'])
                
                if tt_key in st.session_state.get('turntable_images', {}):
                    st.image(st.session_state['turntable_images'][tt_key], use_container_width=True)
                else:
                    if st.button(f"📸 생성", key=f"g_tt_{tt_key}"):
                        with st.spinner("생성 중..."):
                            final_prompt = item.get('prompt', '')
                            if use_json and 'json_profile' in item:
                                detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                                if detailed:
                                    final_prompt = f"{detailed}, {final_prompt}"
                            
                            img, _ = try_generate_image_with_fallback(final_prompt, 1024, 1024, image_provider, max_retries)
                            
                            if img:
                                if 'turntable_images' not in st.session_state:
                                    st.session_state['turntable_images'] = {}
                                st.session_state['turntable_images'][tt_key] = img
                                st.rerun()
                            else:
                                st.error("❌ 생성 실패")
                
                with st.expander("프롬프트"):
                    st.code(item.get('prompt', ''))
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # 씬
    st.markdown("### 🎬 스토리보드")
    
    if st.button("🔄 모든 씬 재생성"):
        st.session_state['generated_images'] = {}
        st.rerun()
    
    for scene in plan.get('scenes', []):
        scene_num = scene.get('scene_num', 0)
        
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**Scene {scene_num}** - {scene.get('timecode', '')}")
            if 'used_turntables' in scene and scene['used_turntables']:
                for tt in scene['used_turntables']:
                    st.markdown(f"<span class='turntable-tag'>🎭 {tt}</span>", unsafe_allow_html=True)
        with col2:
            if scene_num in st.session_state.get('generated_images', {}):
                if st.button("🔄", key=f"r_s_{scene_num}"):
                    del st.session_state['generated_images'][scene_num]
                    st.rerun()
        
        if scene_num in st.session_state.get('generated_images', {}):
            st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
        else:
            if st.button(f"📸 촬영", key=f"g_s_{scene_num}"):
                with st.spinner("생성 중..."):
                    base = scene.get('image_prompt', '')
                    
                    if use_json and 'used_turntables' in scene:
                        final = apply_json_profiles_to_prompt(base, scene['used_turntables'], plan.get('turntable', {}))
                    else:
                        final = f"{plan.get('visual_style', {}).get('character_prompt', '')}, {base}"
                    
                    img, _ = try_generate_image_with_fallback(final, img_width, img_height, image_provider, max_retries)
                    
                    if img:
                        if 'generated_images' not in st.session_state:
                            st.session_state['generated_images'] = {}
                        st.session_state['generated_images'][scene_num] = img
                        st.rerun()
                    else:
                        st.error("❌ 생성 실패")
        
        st.write(f"**액션:** {scene.get('action', '')}")
        st.write(f"**카메라:** {scene.get('camera', '')}")
        
        with st.expander("프롬프트"):
            st.code(scene.get('image_prompt', ''))
            if use_json and 'used_turntables' in scene:
                st.markdown("**JSON 적용 최종:**")
                final = apply_json_profiles_to_prompt(scene.get('image_prompt', ''), scene['used_turntables'], plan.get('turntable', {}))
                st.code(final)
        
        st.markdown("</div>", unsafe_allow_html=True)
