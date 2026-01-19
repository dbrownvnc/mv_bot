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
if 'total_duration' not in st.session_state:
    st.session_state.total_duration = 60
if 'seconds_per_scene' not in st.session_state:
    st.session_state.seconds_per_scene = 5
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
        topic = st.text_area("영상 주제", height=100, value=st.session_state.random_topic, placeholder="주제 입력")
        
        st.markdown("---")
        use_json_profiles = st.checkbox("🎯 JSON 프로필 사용 (극도 디테일)", value=True)
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
            duration_mode = st.radio("⏱️ 런닝타임 설정", ["총 런닝타임", "씬 개수"], horizontal=True)
        
        if duration_mode == "총 런닝타임":
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                total_duration = st.number_input("총 런닝타임 (초)", min_value=10, max_value=300, value=st.session_state.total_duration, step=10)
            with col_d2:
                seconds_per_scene = st.slider("컷당 길이 (초)", 3, 15, st.session_state.seconds_per_scene)
            
            scene_count = max(1, int(total_duration / seconds_per_scene))
            st.caption(f"→ 총 **{scene_count}개** 씬 생성")
            
            st.session_state.scene_count = scene_count
            st.session_state.total_duration = total_duration
            st.session_state.seconds_per_scene = seconds_per_scene
        else:
            scene_count = st.number_input("씬 개수", min_value=2, max_value=30, value=st.session_state.scene_count, step=1)
            st.session_state.scene_count = scene_count
        
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
    
    # JSON 문자열 내의 제어 문자 이스케이프 처리
    def escape_control_chars_in_strings(json_str):
        result = []
        in_string = False
        escape_next = False
        
        for char in json_str:
            if escape_next:
                result.append(char)
                escape_next = False
                continue
            
            if char == '\\':
                result.append(char)
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                result.append(char)
                continue
            
            if in_string:
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                elif ord(char) < 32:  # 기타 제어 문자
                    result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
            else:
                result.append(char)
        
        return ''.join(result)
    
    text = escape_control_chars_in_strings(text)
    return text

def get_visual_style_emphasis(visual_style):
    """비주얼 스타일별 강조 프롬프트"""
    style_map = {
        "Photorealistic/Cinematic": "ULTRA REALISTIC, photorealistic, cinematic photography, shot on RED camera, 8K resolution, natural lighting, professional color grading, film grain, shallow depth of field, bokeh, lifelike textures, hyperrealistic details, actual human skin texture, real world materials, physically accurate lighting",
        "Anime/Manga": "anime style, manga illustration, cel-shaded, vibrant anime colors, expressive anime eyes, clean linework, anime aesthetic",
        "3D Animation": "3D rendered, Pixar style, CGI animation, smooth gradients, 3D modeling, ray-traced lighting",
        "2D Animation": "2D animation, hand-drawn style, traditional animation, painted backgrounds",
        "Watercolor": "watercolor painting, soft edges, color bleeding, paper texture, aquarelle",
        "Oil Painting": "oil painting, thick brushstrokes, canvas texture, classical painting technique",
        "Cyberpunk Neon": "cyberpunk, neon lights, synthwave, futuristic, glowing elements, dark with bright accents",
        "Dark Fantasy": "dark fantasy, gothic, moody atmosphere, dramatic shadows, mysterious lighting",
    }
    return style_map.get(visual_style, visual_style)

def get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json_profiles):
    story_elements = []
    if options.get('use_arc'): story_elements.append("story arc")
    if options.get('use_sensory'): story_elements.append("sensory")
    if options.get('use_dynamic'): story_elements.append("dynamic")
    if options.get('use_emotional'): story_elements.append("emotional")
    if options.get('use_climax'): story_elements.append("climax")
    
    story_instruction = ", ".join(story_elements) if story_elements else "cinematic"
    
    # 비주얼 스타일 강조
    visual_emphasis = get_visual_style_emphasis(visual_style)
    
    json_detail = ""
    if use_json_profiles:
        json_detail = f"""

CRITICAL - ULTRA-DETAILED JSON PROFILES:

For CHARACTERS:
- physical: age, height_cm, weight_kg, body_type, skin_tone (HEX), skin_texture
- face: shape, eyes (color HEX, shape, size), eyebrows (HEX, shape), nose, lips (HEX, shape), jawline
- hair: color_primary (HEX), color_secondary (HEX), length_cm, style, texture, parting
- clothing: top/bottom/shoes (type, color HEX, material, details, fit with exact measurements)
- accessories: exact descriptions with sizes
- distinctive_features: location, size in cm, color HEX
- posture & movement

For LOCATIONS:
- architecture, lighting (time HH:MM, source, Kelvin, HEX colors, shadows)
- weather (condition, visibility meters, precipitation, humidity%)
- color_palette (dominant/accent HEX codes)
- atmosphere

For OBJECTS:
- dimensions LxWxH cm, weight_kg, materials, colors (HEX), finish%, design

STYLE ENFORCEMENT: ALL prompts must include "{visual_emphasis}" to maintain visual consistency.
GENRE ENFORCEMENT: ALL scenes must reflect {genre} genre characteristics.
"""

    turntable_instruction = """

TURNTABLE CHARACTER SHEET FORMAT:
Create prompts for MULTIPLE VIEWS of each character:
- Front view (facing camera, standing straight, arms at sides)
- Side view (90-degree profile, left side, showing full body proportions)
- Back view (rear view, showing back details, hair from behind)
- 3/4 view (45-degree angle, showing face and body proportions)
- Detail shots (close-up of face, hands, clothing details, accessories)

Format: "character turnaround sheet, white background, multiple angles, T-pose or neutral stance, [front view | side view | back view | 3/4 view], character design reference"
"""

    suno_instruction = """

SUNO AI PROMPT STRUCTURE (EXACT FORMAT):

Create with proper line breaks and sections:

━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STYLE TAGS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Genre: [Specific genre from {music_genre}]
Mood: [Emotional tone]
BPM: [80-180 exact number]
Key: [Musical key, e.g., E minor, C major]

━━━━━━━━━━━━━━━━━━━━━━━━━━━
[VOCAL DIRECTION]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Voice Type: [Male/Female/Duet/Choir]
Quality: [Powerful/Soft/Raspy/Ethereal/Emotional]
Effects: [Reverb/Echo/Auto-tune/Harmonies]

━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INSTRUMENTATION]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary: [Main instrument 1, Main instrument 2]
Secondary: [Supporting instrument 1, Supporting instrument 2]
Percussion: [Drum type, Additional percussion]

━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SONG STRUCTURE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Intro]
(atmospheric build, 8 bars)
(sound: synth pad swell / guitar arpeggio / ambient texture)

[Verse 1]
Line 1 of lyrics here
Line 2 of lyrics here
Line 3 of lyrics here
Line 4 of lyrics here

[Pre-Chorus]
(building intensity, adding layers)
Line 1 transitioning to chorus
Line 2 increasing energy

[Chorus]
(powerful vocals, full instrumentation, 120% energy)
Hook line 1 - memorable melody
Hook line 2 - emotional core
Hook line 3 - repetitive catchy element
Hook line 4 - resolution

[Verse 2]
Story development line 1
Story development line 2
Story development line 3
Story development line 4

[Bridge]
(tempo change: breakdown to half-time OR double-time build)
(stripped instrumentation OR orchestral swell)
New perspective line 1
Emotional peak line 2
Introspective moment line 3
Building back to chorus line 4

[Final Chorus]
(explosive, all instruments, vocal harmonies, ad-libs)
Hook with variations
Added vocal runs
Extended resolution

[Outro]
(gradual fade / hard stop / echo effect)
Final emotional statement
(ending: fade to silence / instrumental reprise / vocal whisper)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PRODUCTION NOTES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Use (parentheses) for production directions
- Use [brackets] for section markers
- Include sound effects: (rain), (vinyl crackle), (glitch)
- Specify dynamics: (whispered), (belted), (harmonized)
"""

    return f"""You are a Music Video Director. Create ULTRA-DETAILED plan in VALID JSON.

Theme: "{topic}"
Genre: {genre} (ENFORCE genre characteristics in ALL scenes)
Visual Style: {visual_style} (CRITICAL: Use "{visual_emphasis}" in ALL visual prompts)
Music: {music_genre}
Story: {story_instruction}
{json_detail}
{turntable_instruction}
{suno_instruction}

JSON RULES:
- Double quotes ONLY
- NO trailing commas
- ALL visual prompts MUST start with: "{visual_emphasis}, {genre} aesthetic"

Return ONLY this JSON:
{{
  "project_title": "Title (Korean)",
  "logline": "Concept (Korean)",
  "youtube": {{
    "title": "Viral title | AI Generated",
    "description": "SEO 200-300 words",
    "hashtags": "keywords, comma, separated"
  }},
  "music": {{
    "style": "Style (Korean)",
    "suno_prompt": "Complete Suno structure with all sections separated by lines as shown above",
    "tags": "[genre], [mood]"
  }},
  "visual_style": {{
    "description": "{visual_style} (Korean)",
    "character_prompt": "{visual_emphasis}, {genre} aesthetic, main character",
    "style_tags": "{visual_style}, {genre}"
  }},
  "turntable": {{
    "characters": [
      {{
        "id": "char1",
        "name": "Name (Korean)",
        "json_profile": {{detailed profile}},
        "views": [
          {{
            "view_type": "front",
            "prompt": "{visual_emphasis}, character turnaround sheet, white background, front view, T-pose, full body"
          }},
          {{
            "view_type": "side",
            "prompt": "{visual_emphasis}, character turnaround sheet, white background, side profile, full body proportions"
          }},
          {{
            "view_type": "back",
            "prompt": "{visual_emphasis}, character turnaround sheet, white background, back view, showing rear details"
          }},
          {{
            "view_type": "3/4",
            "prompt": "{visual_emphasis}, character turnaround sheet, white background, 3/4 angle view"
          }}
        ]
      }}
    ],
    "backgrounds": [
      {{
        "id": "loc1",
        "name": "Name (Korean)",
        "json_profile": {{profile}},
        "prompt": "{visual_emphasis}, {genre} aesthetic, 360 environment"
      }}
    ],
    "objects": []
  }},
  "scenes": [
    {{
      "scene_num": 1,
      "timecode": "00:00-00:XX",
      "action": "Action (Korean)",
      "camera": "Shot (Korean)",
      "used_turntables": ["char1", "loc1"],
      "image_prompt": "{visual_emphasis}, {genre} aesthetic, scene description",
      "video_prompt": "Camera movement"
    }}
  ]
}}

Generate {scene_count} scenes."""

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
            if 'shape' in face: parts.append(f"{face['shape']} face shape")
            
            if 'eyes' in face:
                if isinstance(face['eyes'], dict):
                    eyes = face['eyes']
                    eye_parts = []
                    if 'color' in eyes: eye_parts.append(f"{eyes['color']} color")
                    if 'shape' in eyes: eye_parts.append(f"{eyes['shape']} shape")
                    if 'size' in eyes: eye_parts.append(f"{eyes['size']} size")
                    if eye_parts: parts.append(f"eyes: {', '.join(eye_parts)}")
            
            if 'hair' in face or 'eyebrows' in face:
                if 'eyebrows' in face and isinstance(face['eyebrows'], dict):
                    eb = face['eyebrows']
                    parts.append(f"eyebrows {eb.get('color', '')} {eb.get('shape', '')}")
            
            if 'nose' in face: parts.append(f"{face['nose']} nose")
            if 'lips' in face:
                if isinstance(face['lips'], dict):
                    lips = face['lips']
                    parts.append(f"lips {lips.get('color', '')} {lips.get('shape', '')}")
            if 'jawline' in face: parts.append(f"{face['jawline']} jawline")
    
    # 머리
    if 'hair' in profile:
        hair = profile['hair']
        if isinstance(hair, dict):
            hair_parts = []
            if 'color_primary' in hair: hair_parts.append(f"{hair['color_primary']} color")
            if 'color_secondary' in hair: hair_parts.append(f"with {hair['color_secondary']} highlights")
            if 'length_cm' in hair: hair_parts.append(f"{hair['length_cm']}cm long")
            if 'style' in hair: hair_parts.append(hair['style'])
            if 'texture' in hair: hair_parts.append(f"{hair['texture']} texture")
            if hair_parts: parts.append(f"hair: {', '.join(hair_parts)}")
    
    # 의상
    if 'clothing' in profile:
        cloth = profile['clothing']
        if isinstance(cloth, dict):
            for piece in ['top', 'bottom', 'shoes']:
                if piece in cloth and isinstance(cloth[piece], dict):
                    item = cloth[piece]
                    item_parts = [item.get('type', '')]
                    if 'color' in item: item_parts.append(f"color {item['color']}")
                    if 'material' in item: item_parts.append(f"{item['material']}")
                    if 'details' in item: item_parts.append(item['details'])
                    if item_parts and item_parts[0]: parts.append(f"{piece}: {', '.join([p for p in item_parts if p])}")
    
    # 액세서리
    if 'accessories' in profile:
        acc = profile['accessories']
        if isinstance(acc, list) and acc:
            parts.append(f"accessories: {', '.join(acc)}")
    
    # 특징
    if 'distinctive_features' in profile:
        feat = profile['distinctive_features']
        if isinstance(feat, list) and feat:
            parts.append(f"distinctive: {', '.join(feat)}")
    
    # 자세/움직임
    if 'posture' in profile: parts.append(f"{profile['posture']} posture")
    if 'movement' in profile: parts.append(f"{profile['movement']} movement")
    
    # 장소
    if 'location_type' in profile:
        parts.append(profile['location_type'])
    
    if 'lighting' in profile:
        light = profile['lighting']
        if isinstance(light, dict):
            light_parts = []
            if 'time' in light: light_parts.append(f"time {light['time']}")
            if 'color_temperature' in light: light_parts.append(f"{light['color_temperature']}")
            if light_parts: parts.append(f"lighting: {', '.join(light_parts)}")
    
    if 'atmosphere' in profile:
        parts.append(f"{profile['atmosphere']} atmosphere")
    
    return ", ".join([p for p in parts if p])

def create_json_export(plan_data):
    return json.dumps(plan_data, ensure_ascii=False, indent=2)

def create_text_export(plan_data):
    """텍스트 형식 프롬프트 저장"""
    text = f"""
{'='*80}
AI MV DIRECTOR - 프롬프트 모음
{'='*80}

프로젝트: {plan_data.get('project_title', '')}
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*80}
YOUTUBE
{'='*80}
제목: {plan_data.get('youtube', {}).get('title', '')}

설명:
{plan_data.get('youtube', {}).get('description', '')}

해시태그:
{plan_data.get('youtube', {}).get('hashtags', '')}

{'='*80}
MUSIC - SUNO AI
{'='*80}
{plan_data.get('music', {}).get('suno_prompt', '')}

{'='*80}
TURNTABLE
{'='*80}
"""
    
    if 'turntable' in plan_data:
        for cat in ['characters', 'backgrounds', 'objects']:
            if cat in plan_data['turntable']:
                text += f"\n{cat.upper()}:\n{'-'*80}\n"
                for item in plan_data['turntable'][cat]:
                    text += f"\n{item.get('name', '')}\n"
                    if 'views' in item:
                        for view in item['views']:
                            text += f"  [{view.get('view_type', '')}] {view.get('prompt', '')}\n"
                    else:
                        text += f"  {item.get('prompt', '')}\n"
    
    text += f"\n{'='*80}\nSCENES\n{'='*80}\n"
    for scene in plan_data.get('scenes', []):
        text += f"\nScene {scene.get('scene_num', '')} - {scene.get('timecode', '')}\n"
        text += f"Action: {scene.get('action', '')}\n"
        text += f"Prompt: {scene.get('image_prompt', '')}\n\n"
    
    return text

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
    enhanced = f"{prompt}, professional photography, high quality"
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
                st.session_state.clear()
                st.session_state['use_json_profiles'] = use_json_profiles
                st.session_state['image_width'] = image_width
                st.session_state['image_height'] = image_height
                st.session_state['auto_generate'] = auto_generate
                st.session_state['image_provider'] = image_provider
                st.session_state['max_retries'] = max_retries
                
                with st.spinner("📝 극도로 디테일한 기획안 생성 중..."):
                    st.session_state['plan_data'] = generate_plan_auto(
                        topic, gemini_key, gemini_model, scene_count, story_opts,
                        selected_genre, selected_visual, selected_music, use_json_profiles
                    )
                
                if st.session_state['plan_data']:
                    st.success("✅ 기획안 생성 완료!")
                    
                    if auto_generate:
                        plan = st.session_state['plan_data']
                        
                        # 턴테이블 생성
                        if 'turntable' in plan and 'characters' in plan['turntable']:
                            st.markdown("### 🎭 턴테이블 자동 생성")
                            
                            for char in plan['turntable']['characters']:
                                char_name = char.get('name', '')
                                if 'views' in char:
                                    st.markdown(f"**{char_name}**")
                                    progress_char = st.progress(0)
                                    
                                    for idx, view in enumerate(char['views']):
                                        view_type = view.get('view_type', '')
                                        tt_key = f"characters_{char_name}_{view_type}"
                                        
                                        final_prompt = view.get('prompt', '')
                                        if use_json_profiles and 'json_profile' in char:
                                            detailed = json_profile_to_ultra_detailed_text(char['json_profile'])
                                            if detailed:
                                                final_prompt = f"{detailed}, {final_prompt}"
                                        
                                        img, _ = try_generate_image_with_fallback(final_prompt, 1024, 1024, image_provider, max_retries)
                                        
                                        if img:
                                            if 'turntable_images' not in st.session_state:
                                                st.session_state['turntable_images'] = {}
                                            st.session_state['turntable_images'][tt_key] = img
                                            st.toast(f"✅ {char_name} {view_type} 완료")
                                        
                                        progress_char.progress((idx + 1) / len(char['views']))
                                        time.sleep(0.3)
                        
                        # 씬 이미지 생성
                        if 'scenes' in plan:
                            st.markdown("### 🎬 씬 이미지 자동 생성")
                            scenes = plan['scenes']
                            progress_sc = st.progress(0)
                            
                            for idx, scene in enumerate(scenes):
                                scene_num = scene.get('scene_num', 0)
                                
                                base = scene.get('image_prompt', '')
                                if use_json_profiles and 'used_turntables' in scene:
                                    final = apply_json_profiles_to_prompt(base, scene['used_turntables'], plan.get('turntable', {}))
                                else:
                                    final = base
                                
                                img, _ = try_generate_image_with_fallback(final, image_width, image_height, image_provider, max_retries)
                                
                                if img:
                                    if 'generated_images' not in st.session_state:
                                        st.session_state['generated_images'] = {}
                                    st.session_state['generated_images'][scene_num] = img
                                    st.toast(f"✅ Scene {scene_num} 완료")
                                
                                progress_sc.progress((idx + 1) / len(scenes))
                                time.sleep(0.3)
                    
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
    col_save1, col_save2 = st.columns(2)
    with col_save1:
        st.download_button(
            "📋 JSON 다운로드",
            data=create_json_export(plan),
            file_name=f"{plan.get('project_title', 'project')}.json",
            mime="application/json",
            use_container_width=True
        )
    with col_save2:
        st.download_button(
            "📝 TXT 프롬프트",
            data=create_text_export(plan),
            file_name=f"{plan.get('project_title', 'project')}_prompts.txt",
            mime="text/plain",
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
        st.markdown("### 🎵 Suno AI")
        with st.expander("🎼 Suno 프롬프트 (구조화)", expanded=False):
            st.text_area("복사하세요", value=plan['music'].get('suno_prompt', ''), height=400, key="suno_p")
    
    st.markdown("---")
    
    # 턴테이블
    if 'turntable' in plan and 'characters' in plan['turntable']:
        st.markdown("### 🎭 턴테이블")
        
        # 한번에 모든 턴테이블 생성
        if st.button("🎨 모든 턴테이블 이미지 생성", use_container_width=True, type="primary"):
            progress_all = st.progress(0)
            status_all = st.empty()
            
            total_views = sum(len(char.get('views', [])) for char in plan['turntable']['characters'])
            current = 0
            
            for char in plan['turntable']['characters']:
                if 'views' in char:
                    for view in char['views']:
                        char_name = char.get('name', '')
                        view_type = view.get('view_type', '')
                        tt_key = f"characters_{char_name}_{view_type}"
                        
                        status_all.markdown(f"<div class='status-box'>생성 중: {char_name} - {view_type}</div>", unsafe_allow_html=True)
                        
                        final_prompt = view.get('prompt', '')
                        if use_json and 'json_profile' in char:
                            detailed = json_profile_to_ultra_detailed_text(char['json_profile'])
                            if detailed:
                                final_prompt = f"{detailed}, {final_prompt}"
                        
                        img, _ = try_generate_image_with_fallback(final_prompt, 1024, 1024, image_provider, max_retries)
                        
                        if img:
                            if 'turntable_images' not in st.session_state:
                                st.session_state['turntable_images'] = {}
                            st.session_state['turntable_images'][tt_key] = img
                        
                        current += 1
                        progress_all.progress(current / total_views)
                        time.sleep(0.3)
            
            status_all.markdown("<div class='status-box'>✅ 완료!</div>", unsafe_allow_html=True)
            st.rerun()
        
        # 개별 턴테이블 표시
        for char in plan['turntable']['characters']:
            st.markdown(f"<div class='turntable-box'>", unsafe_allow_html=True)
            st.markdown(f"**👤 {char.get('name', '')}** (ID: {char.get('id', '')})")
            
            if 'json_profile' in char:
                with st.expander("📊 JSON 프로필"):
                    st.json(char['json_profile'])
            
            if 'views' in char:
                cols = st.columns(len(char['views']))
                for idx, view in enumerate(char['views']):
                    with cols[idx]:
                        view_type = view.get('view_type', '')
                        tt_key = f"characters_{char.get('name', '')}_{view_type}"
                        
                        st.caption(view_type.upper())
                        
                        if tt_key in st.session_state.get('turntable_images', {}):
                            st.image(st.session_state['turntable_images'][tt_key], use_container_width=True)
                        else:
                            if st.button(f"📸", key=f"g_{tt_key}"):
                                final_prompt = view.get('prompt', '')
                                if use_json and 'json_profile' in char:
                                    detailed = json_profile_to_ultra_detailed_text(char['json_profile'])
                                    if detailed:
                                        final_prompt = f"{detailed}, {final_prompt}"
                                
                                img, _ = try_generate_image_with_fallback(final_prompt, 1024, 1024, image_provider, max_retries)
                                if img:
                                    if 'turntable_images' not in st.session_state:
                                        st.session_state['turntable_images'] = {}
                                    st.session_state['turntable_images'][tt_key] = img
                                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # 씬
    st.markdown("### 🎬 스토리보드")
    
    # 한번에 모든 씬 생성
    if st.button("🎨 모든 씬 이미지 생성", use_container_width=True, type="primary"):
        scenes = plan.get('scenes', [])
        progress_scenes = st.progress(0)
        status_scenes = st.empty()
        
        for idx, scene in enumerate(scenes):
            scene_num = scene.get('scene_num', 0)
            status_scenes.markdown(f"<div class='status-box'>Scene {scene_num} 생성 중...</div>", unsafe_allow_html=True)
            
            base = scene.get('image_prompt', '')
            if use_json and 'used_turntables' in scene:
                final = apply_json_profiles_to_prompt(base, scene['used_turntables'], plan.get('turntable', {}))
            else:
                final = base
            
            img, _ = try_generate_image_with_fallback(final, img_width, img_height, image_provider, max_retries)
            
            if img:
                if 'generated_images' not in st.session_state:
                    st.session_state['generated_images'] = {}
                st.session_state['generated_images'][scene_num] = img
            
            progress_scenes.progress((idx + 1) / len(scenes))
            time.sleep(0.3)
        
        status_scenes.markdown("<div class='status-box'>✅ 완료!</div>", unsafe_allow_html=True)
        st.rerun()
    
    # 개별 씬 표시
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
                base = scene.get('image_prompt', '')
                if use_json and 'used_turntables' in scene:
                    final = apply_json_profiles_to_prompt(base, scene['used_turntables'], plan.get('turntable', {}))
                else:
                    final = base
                
                img, _ = try_generate_image_with_fallback(final, img_width, img_height, image_provider, max_retries)
                if img:
                    if 'generated_images' not in st.session_state:
                        st.session_state['generated_images'] = {}
                    st.session_state['generated_images'][scene_num] = img
                    st.rerun()
        
        st.write(f"**액션:** {scene.get('action', '')}")
        st.write(f"**카메라:** {scene.get('camera', '')}")
        
        with st.expander("프롬프트"):
            st.code(scene.get('image_prompt', ''))
        
        st.markdown("</div>", unsafe_allow_html=True)
