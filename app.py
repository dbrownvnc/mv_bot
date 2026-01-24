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
    .suno-section {
        background-color: #f5f0ff;
        border: 1px solid #722ed1;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
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

# --- 확장된 트렌드 키워드 (대폭 확장) ---
TRENDING_KEYWORDS = {
    "emotions": [
        "heartbreak", "hope", "nostalgia", "euphoria", "melancholy", "rage", "peace", "anxiety", "joy", "loneliness",
        "obsession", "liberation", "despair", "ecstasy", "bittersweet", "rebellion", "serenity", "madness", "yearning", "triumph",
        "betrayal", "redemption", "devotion", "confusion", "enlightenment", "paranoia", "bliss", "grief", "wonder", "defiance"
    ],
    "settings": [
        "neon city", "abandoned subway", "rooftop at dawn", "underwater palace", "desert highway", "floating islands",
        "dystopian Tokyo", "cyberpunk Seoul", "ancient temple", "space station", "frozen tundra", "volcanic landscape",
        "bioluminescent forest", "steampunk factory", "art deco ballroom", "post-apocalyptic wasteland", "crystal cave",
        "holographic nightclub", "zero gravity station", "ancient ruins", "mirror dimension", "time-frozen city",
        "neon-lit rain street", "abandoned amusement park", "underground bunker", "floating market", "digital void",
        "cherry blossom garden", "brutalist architecture", "venetian canals", "himalayan monastery"
    ],
    "characters": [
        "lonely hacker", "rebel artist", "time traveler", "android musician", "street dancer", "wandering poet",
        "revenge seeker", "fallen angel", "lost astronaut", "phantom thief", "cursed immortal", "dimension hopper",
        "memory collector", "dream architect", "soul merchant", "reality bender", "shadow assassin", "light keeper",
        "chaos agent", "harmony seeker", "digital ghost", "analog soul", "future prophet", "past hunter",
        "emotion vampire", "hope dealer", "fear eater", "love warrior", "death dancer", "life singer"
    ],
    "aesthetics": [
        "retro 80s", "vaporwave dreams", "dark academia", "y2k nostalgia", "minimalist void", "baroque luxury",
        "glitch art", "neon noir", "pastel goth", "cyberpunk", "afrofuturism", "solarpunk", "dieselpunk",
        "cottagecore nightmare", "liminal space", "dreamcore", "weirdcore", "ethereal maximalism", "brutalist elegance",
        "bio-organic tech", "crystal punk", "holographic minimalism", "dark romanticism", "neo-tokyo", "cyber-shamanic",
        "quantum aesthetic", "retro-futurism", "analog horror", "digital baroque", "neon gothic"
    ],
    "actions": [
        "running through rain", "dancing in fire", "flying over city", "drowning in memories", "breaking free",
        "searching for light", "falling through time", "rising from ashes", "chasing shadows", "embracing the void",
        "shattering reality", "rebuilding self", "transcending dimension", "merging with machine", "escaping simulation",
        "fighting inner demon", "reuniting souls", "sacrificing everything", "discovering truth", "accepting fate",
        "defying gravity", "manipulating time", "bending light", "controlling elements", "summoning power"
    ],
    "times": [
        "midnight", "golden hour", "endless night", "frozen moment", "parallel timeline", "infinite loop",
        "last sunrise", "first snowfall", "summer's end", "dawn of chaos", "twilight zone", "eternal dusk",
        "moment before impact", "second after rebirth", "edge of tomorrow", "yesterday's future", "timeless now",
        "quantum midnight", "fractal dawn", "crystallized second"
    ],
    "trends_2025": [
        "AI awakening", "metaverse escape", "climate dystopia", "gen-z rebellion", "digital detox", "virtual romance",
        "blockchain dreams", "quantum love", "hologram memories", "synthetic emotions", "neural link love", "avatar identity",
        "deep fake reality", "algorithmic fate", "carbon zero future", "biohacked beauty", "crypto collapse", "VR addiction",
        "AI companion bond", "simulation theory", "consciousness upload", "memory marketplace", "emotion NFT", "dream streaming"
    ],
    "cinematic_styles": [
        "Christopher Nolan epic", "Denis Villeneuve atmosphere", "David Fincher darkness", "Wes Anderson symmetry",
        "Wong Kar-wai romance", "Park Chan-wook intensity", "Bong Joon-ho social", "Ridley Scott sci-fi",
        "Guillermo del Toro fantasy", "Terrence Malick poetry", "Nicolas Winding Refn neon", "Gaspar Noé chaos",
        "Kubrick precision", "Tarkovsky meditation", "Lynch surrealism", "Tarantino stylization"
    ],
    "music_moods": [
        "anthemic euphoria", "melancholic beauty", "aggressive energy", "dreamy float", "dark intensity",
        "playful chaos", "intimate whisper", "epic grandeur", "haunting mystery", "rebellious defiance",
        "nostalgic warmth", "futuristic cold", "organic warmth", "synthetic precision", "raw emotion"
    ]
}

def generate_trending_topic():
    """더욱 다양한 주제 생성"""
    templates = [
        "{character} experiencing {emotion} in a {setting} during {time}, {aesthetic} style, {action}",
        "{emotion} journey of a {character} in {setting}, {aesthetic} vibes, {trend}",
        "{cinematic} inspired: {character} {action} in {setting}, {aesthetic} aesthetic",
        "{trend} era: {character} feeling {emotion}, {setting}, {time}",
        "{aesthetic} music video: {character} in {setting}, {emotion} meets {music_mood}",
        "Visual poem: {character} {action}, {setting} at {time}, {cinematic} cinematography",
        "{music_mood} energy: {character} confronts {emotion} in {setting}, {trend}",
        "Experimental: {character} trapped in {setting}, {aesthetic} meets {cinematic}",
    ]
    template = random.choice(templates)
    return template.format(
        emotion=random.choice(TRENDING_KEYWORDS["emotions"]),
        setting=random.choice(TRENDING_KEYWORDS["settings"]),
        character=random.choice(TRENDING_KEYWORDS["characters"]),
        aesthetic=random.choice(TRENDING_KEYWORDS["aesthetics"]),
        action=random.choice(TRENDING_KEYWORDS["actions"]),
        time=random.choice(TRENDING_KEYWORDS["times"]),
        trend=random.choice(TRENDING_KEYWORDS["trends_2025"]),
        cinematic=random.choice(TRENDING_KEYWORDS["cinematic_styles"]),
        music_mood=random.choice(TRENDING_KEYWORDS["music_moods"])
    )

def get_viral_topic_with_ai(api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = """Generate ONE highly creative, viral-worthy music video concept. 
        Be specific, cinematic, and emotionally compelling. Include:
        - Unique character/protagonist
        - Vivid setting/location
        - Core emotion/theme
        - Visual style reference
        Keep it to 2-3 sentences. Make it feel like a blockbuster movie pitch."""
        response = model.generate_content(prompt)
        return response.text.strip().strip('"')
    except:
        return generate_trending_topic()

# --- API 키 ---
def get_api_key(key_name):
    if key_name in st.secrets: return st.secrets[key_name]
    elif os.getenv(key_name): return os.getenv(key_name)
    return None

# --- 장르/스타일 (확장) ---
VIDEO_GENRES = [
    "Action/Thriller", "Sci-Fi Epic", "Dark Fantasy", "Psychological Horror", "Romantic Drama", 
    "Neo-Noir", "Cyberpunk", "Post-Apocalyptic", "Surreal/Abstract", "Music Video (Performance)",
    "Music Video (Narrative)", "Experimental Art Film", "Anime/Animation", "Documentary Style",
    "Found Footage", "One-Shot/Long Take", "Dance Film", "Visual Poem", "Social Commentary",
    "Cosmic Horror", "Magical Realism", "Dystopian Future", "Historical Epic", "Slice of Life"
]

VISUAL_STYLES = [
    "Photorealistic/Cinematic", "Hyperrealistic 8K", "Anime/Manga", "3D Pixar Style", 
    "2D Traditional Animation", "Watercolor Painting", "Oil Painting Classical", "Cyberpunk Neon",
    "Dark Fantasy Gothic", "Pastel Dreamy", "Black & White Film Noir", "Retro 80s VHS",
    "Vaporwave Aesthetic", "Lo-Fi Indie", "High Fashion Editorial", "Gritty Documentary",
    "Surrealist Art", "Minimalist Clean", "Maximalist Baroque", "Glitch Art Digital"
]

MUSIC_GENRES = [
    "Pop", "Rock", "Hip-Hop/Rap", "Electronic/EDM", "R&B/Soul", "Jazz", "Classical", 
    "Metal", "Indie", "K-Pop", "Lo-Fi", "Trap", "House", "Techno", "Ambient",
    "Synthwave", "Phonk", "Drill", "Afrobeat", "Latin", "Folk", "Country",
    "Orchestral/Cinematic", "Experimental", "Post-Rock", "Dream Pop", "Shoegaze"
]

# --- 비주얼 스타일 강조 (포토리얼리스틱 대폭 강화) ---
def get_visual_style_emphasis(visual_style):
    # 포토리얼리스틱 계열 강력한 프롬프트
    photo_emphasis = """(EXTREMELY DETAILED REAL PHOTO:1.5), (8k resolution:1.2), (photorealistic:1.4), 
RAW photo, Fujifilm XT3, shot on 50mm lens, f/1.8, natural skin texture, visible pores, soft lighting, 
detailed eyes, distinct facial features, hyper-detailed, no CGI, no 3D render look, 
authentic human imperfections, cinematic lighting, masterpiece, best quality"""

    style_map = {
        "Photorealistic/Cinematic": photo_emphasis,
        "Hyperrealistic 8K": photo_emphasis + ", RED V-RAPTOR 8K, documentary style",
        
        "Anime/Manga": """anime style, manga illustration, cel-shaded, vibrant anime colors, 
expressive anime eyes, clean linework, anime aesthetic, Studio Ghibli quality,
Makoto Shinkai lighting, detailed anime backgrounds""",
        
        "3D Pixar Style": """3D rendered, Pixar Animation Studios quality, CGI animation, 
smooth gradients, subsurface scattering, ray-traced lighting, 
Disney/Pixar character design, expressive 3D characters""",
        
        "Cyberpunk Neon": """cyberpunk aesthetic, neon lights, synthwave colors, 
futuristic cityscape, rain-slicked streets, holographic advertisements,
Blade Runner 2049 cinematography, volumetric fog, RGB lighting,
dark with vibrant neon accents, tech-noir atmosphere""",
        
        "Dark Fantasy Gothic": """dark fantasy, gothic architecture, moody atmosphere, 
dramatic chiaroscuro lighting, mysterious fog, medieval dark aesthetics,
Game of Thrones visual quality, dark romanticism, ominous shadows""",
        
        "Black & White Film Noir": """black and white cinematography, high contrast,
dramatic shadows, film noir lighting, 1940s Hollywood style,
venetian blind shadows, fog-filled streets, classic cinema look""",
        
        "Retro 80s VHS": """1980s aesthetic, VHS quality, scan lines, chromatic aberration,
neon colors, analog warmth, retro futurism, Stranger Things vibe,
practical effects look, vintage film grain""",
        
        "High Fashion Editorial": """high fashion photography, Vogue editorial quality,
dramatic fashion lighting, avant-garde styling, luxury aesthetic,
shot by Mario Testino, couture fashion, editorial composition""",
        
        "Surrealist Art": """surrealist art style, Salvador Dali inspired, 
dreamlike imagery, impossible geometry, melting reality,
symbolic visual metaphors, subconscious imagery, Magritte influence"""
    }
    return style_map.get(visual_style, f"{visual_style}, high quality, professional")

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    execution_mode = st.radio("실행 방식", ["API 자동 실행", "수동 모드 (무제한)"], index=0)
    st.markdown("---")

    gemini_key = None
    gemini_model = None
    segmind_key = None
    
    if execution_mode == "API 자동 실행":
        # Gemini Key
        gemini_key = get_api_key("GOOGLE_API_KEY") or get_api_key("GEMINI_API_KEY")
        if gemini_key:
            st.success("✅ Gemini Key 연결됨")
        else:
            gemini_key = st.text_input("Gemini API Key", type="password")
        
        # Segmind Key (추가됨)
        segmind_key = get_api_key("SEGMIND_API_KEY")
        if segmind_key:
            st.success("✅ Segmind Key 연결됨")
        else:
            segmind_key = st.text_input("Segmind API Key (선택)", type="password")
            
        model_options = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
        gemini_model = st.selectbox("모델", model_options, index=0)
    
    st.markdown("---")
    st.subheader("🎨 이미지 생성")
    auto_generate = st.checkbox("자동 이미지 생성", value=False)
    infinite_retry = st.checkbox("무한 재시도", value=False)
    
    # 이미지 공급자 선택 (Segmind 복구 및 기본값 설정)
    image_provider = st.selectbox("엔진", ["Segmind (기본/안정)", "Pollinations Flux", "Pollinations Turbo ⚡"], index=0)
    
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
st.caption("업계 최고 수준의 뮤직비디오 기획 시스템")

ratio_map = {
    "16:9 (Cinema)": (1024, 576),
    "9:16 (Portrait)": (576, 1024),
    "1:1 (Square)": (1024, 1024),
    "21:9 (Ultrawide)": (1024, 439),
    "4:3 (Classic)": (1024, 768),
}

# 세션 상태 초기화
defaults = {
    'scene_count': 8,
    'total_duration': 60,
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
    # 바이럴 주제 생성
    st.markdown("<div class='trend-box'>", unsafe_allow_html=True)
    st.markdown("### 🔥 바이럴 주제 생성기")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        if st.button("🎲 랜덤 생성", use_container_width=True):
            st.session_state.random_topic = generate_trending_topic()
            st.rerun()
    with col_t2:
        if st.button("🎲🎲 5개 생성", use_container_width=True):
            topics = [generate_trending_topic() for _ in range(5)]
            st.session_state.random_topic = "\n---\n".join(topics)
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
        topic = st.text_area("🎯 영상 주제/컨셉", height=120, 
                            value=st.session_state.random_topic if st.session_state.random_topic else "",
                            placeholder="뮤직비디오의 주제, 스토리, 분위기를 상세히 입력하세요...")
        
        st.markdown("---")
        
        # JSON 프로필 옵션
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            use_json_profiles = st.checkbox("🎯 JSON 프로필 (극도 디테일)", value=True)
        with col_opt2:
            expert_mode = st.checkbox("🏆 전문가 모드 (심층 분석)", value=True)
        
        st.markdown("---")
        
        # 장르/스타일 선택
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            selected_genre = st.selectbox("🎬 영상 장르", VIDEO_GENRES, index=0)
        with col_g2:
            selected_visual = st.selectbox("🎨 비주얼 스타일", VISUAL_STYLES, index=0)
        with col_g3:
            selected_music = st.selectbox("🎵 음악 장르", MUSIC_GENRES, index=0)
        
        st.markdown("---")
        
        # 비율 및 런닝타임
        col1, col2 = st.columns(2)
        with col1:
            aspect_ratio = st.selectbox("🎞️ 화면 비율", list(ratio_map.keys()), index=0)
            image_width, image_height = ratio_map[aspect_ratio]
        
        with col2:
            duration_mode = st.radio("⏱️ 런닝타임 설정 방식", ["총 런닝타임 기준", "씬 개수 직접 지정"], horizontal=True)
        
        # 런닝타임/씬 설정 (실시간 동기화)
        st.markdown("#### ⏱️ 타임라인 설정")
        
        if duration_mode == "총 런닝타임 기준":
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                total_duration = st.number_input("총 런닝타임 (초)", min_value=10, max_value=600, 
                                                value=st.session_state.total_duration, step=5)
            with col_d2:
                seconds_per_scene = st.slider("컷당 길이 (초)", 2, 20, st.session_state.seconds_per_scene)
            with col_d3:
                scene_count = max(1, int(total_duration / seconds_per_scene))
                st.markdown(f"""
                <div class='realtime-calc'>
                    📊 총 {scene_count}개 씬<br>
                    <small>{total_duration}초 ÷ {seconds_per_scene}초</small>
                </div>
                """, unsafe_allow_html=True)
            
            st.session_state.scene_count = scene_count
            st.session_state.total_duration = total_duration
            st.session_state.seconds_per_scene = seconds_per_scene
        else:
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                scene_count = st.number_input("씬 개수", min_value=2, max_value=50, 
                                             value=st.session_state.scene_count, step=1)
            with col_s2:
                seconds_per_scene = st.slider("컷당 길이 (초)", 2, 20, st.session_state.seconds_per_scene)
            with col_s3:
                total_duration = scene_count * seconds_per_scene
                st.markdown(f"""
                <div class='realtime-calc'>
                    ⏱️ 총 {total_duration}초<br>
                    <small>({total_duration//60}분 {total_duration%60}초)</small>
                </div>
                """, unsafe_allow_html=True)
            
            st.session_state.scene_count = scene_count
            st.session_state.seconds_per_scene = seconds_per_scene
        
        st.markdown("---")
        
        # 스토리 옵션
        st.markdown("**📖 스토리 구성 요소**")
        cols = st.columns(4)
        with cols[0]:
            use_arc = st.checkbox("기승전결 구조", value=True)
            use_sensory = st.checkbox("감각적 묘사", value=True)
        with cols[1]:
            use_trial = st.checkbox("시련/갈등", value=True)
            use_dynamic = st.checkbox("역동적 전개", value=True)
        with cols[2]:
            use_emotional = st.checkbox("감정 변화곡선", value=True)
            use_climax = st.checkbox("클라이맥스 구축", value=True)
        with cols[3]:
            use_symbolic = st.checkbox("상징/메타포", value=True)
            use_twist = st.checkbox("반전 요소", value=False)
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 프로젝트 생성", use_container_width=True, type="primary")

# ------------------------------------------------------------------
# JSON 정리 함수
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
                elif ord(char) < 32:
                    result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
            else:
                result.append(char)
        
        return ''.join(result)
    
    text = escape_control_chars_in_strings(text)
    return text

# ------------------------------------------------------------------
# 시스템 프롬프트 (전문가 수준 - 수정됨)
# ------------------------------------------------------------------
def get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json, expert_mode, seconds_per_scene):
    story_elements = []
    if options.get('use_arc'): story_elements.append("three-act structure with setup-confrontation-resolution")
    if options.get('use_sensory'): story_elements.append("rich sensory details (visual, auditory, tactile)")
    if options.get('use_dynamic'): story_elements.append("dynamic pacing with rhythm variations")
    if options.get('use_emotional'): story_elements.append("emotional arc with clear beats")
    if options.get('use_climax'): story_elements.append("building tension to powerful climax")
    if options.get('use_trial'): story_elements.append("protagonist trials and obstacles")
    if options.get('use_symbolic'): story_elements.append("symbolic imagery and visual metaphors")
    if options.get('use_twist'): story_elements.append("unexpected twist or revelation")
    
    story_instruction = ", ".join(story_elements) if story_elements else "cinematic narrative flow"
    visual_emphasis = get_visual_style_emphasis(visual_style)
    
    expert_instruction = ""
    if expert_mode:
        expert_instruction = """

EXPERT MODE - INDUSTRY PROFESSIONAL STANDARDS:

You are working at the level of top-tier music video directors (Hype Williams, Dave Meyers, Joseph Kahn, CHEZ, Woogie Kim).

CINEMATOGRAPHY MASTERY:
- Camera movements: Specify exact dolly/crane/steadicam/gimbal movements with timing
- Lens choices: Indicate focal length (14mm wide, 50mm standard, 85mm portrait, 200mm telephoto)
- Depth of field: Specify f-stop for each shot (f/1.4 shallow, f/8 deep)
- Lighting setups: Key, fill, rim, practical lights with color temperature (2700K warm, 5600K daylight)

COLOR SCIENCE:
- Color palette: Specify exact HEX codes for dominant, secondary, accent colors
- LUT reference: Reference specific color grades (Teal & Orange, Film Noir, Kodak Vision3)
- Contrast ratio: Specify shadow/highlight relationship
"""

    # 실사 강조 (강력한 규칙 추가)
    photorealistic_extra = ""
    if "Photorealistic" in visual_style or "Hyperrealistic" in visual_style:
        photorealistic_extra = """

CRITICAL - PHOTOREALISTIC REQUIREMENTS (MUST FOLLOW):
ALL prompts MUST include:
- "RAW photo, 8k resolution, photorealistic, dslr, soft lighting, high quality, film grain"
- "REAL HUMAN, natural skin texture, visible pores, imperfections, peach fuzz, realistic eyes"
- "No CGI, No 3D render look, No illustration style"
- "Shot on Fujifilm XT3 or ARRI Alexa"
"""

    json_detail = ""
    if use_json:
        json_detail = f"""

ULTRA-DETAILED JSON PROFILES (SOURCE OF TRUTH - STRONGEST ENFORCEMENT):

1. **SOURCE OF TRUTH RULE**: The 'json_profile' field is the ONLY valid source for physical appearance.
2. **NEGATIVE CONSTRAINT FOR SCENES**: In the 'scenes' -> 'image_prompt' field, you MUST NOT describe the character's appearance (hair color, clothes, face). 
   - **WRONG**: "A handsome man with blue hair and a leather jacket running in the rain."
   - **CORRECT**: "A man running in the rain, dynamic angle, intense expression."
   (The system will automatically INJECT the detailed description from 'json_profile' at the beginning of the prompt. If you repeat it, it causes conflicts.)

3. **MANDATORY**: You MUST generate a turntable entry for **EVERY** single character, location, prop, and vehicle that appears.
4. **DETAIL**: Provide specific HEX codes, materials, brands, and exact measurements.

For CHARACTERS:
{{
  "physical": {{ "age": "exact age", "height_cm": number, "body_type": "detailed", "skin_tone": "#HEX", "skin_texture": "pores/freckles/scars" }},
  "face": {{ "shape": "...", "eyes": {{"color": "#HEX", "shape": "..."}}, "nose": "...", "lips": "...", "hair": {{"color": "#HEX", "style": "..."}} }},
  "clothing": {{ "top": {{"color": "#HEX", "material": "..."}}, "bottom": "...", "shoes": "...", "accessories": "..." }},
  "expression": "default emotional state"
}}

For LOCATIONS:
{{
  "location_type": "exact place",
  "architecture": "style and materials",
  "lighting": {{"time": "HH:MM", "source": "sun/neon", "color_temp": "K"}},
  "palette": {{"dominant": "#HEX", "accent": "#HEX"}}
}}
"""

    turntable_instruction = """

TURNTABLE REFERENCE SHEETS (COMPREHENSIVE & MANDATORY):

You MUST create turntable entries for ALL distinct elements.

FOR EACH CHARACTER (Mandatory Views):
- View 1: "full_turntable" -> PROMPT MUST BE: "character sheet, split screen, 4 distinct views, front view, side view, back view, 3/4 view, same character in all views, full body shot, white background, high resolution"
- View 2: "face_detail" (Extreme close-up, pore details, eyes)
- View 3: "expression_sheet" (Neutral, Joy, Anger, Sorrow, Surprise)
- View 4: "fashion_detail" (Clothing texture, shoes, accessories)
- View 5: "cinematic_portrait" (Best lighting, shallow depth of field)

FOR EACH LOCATION:
- View 1: "establishing_shot" (Wide angle, entire scale)
- View 2: "lighting_study" (Same angle, Day vs Night vs Golden Hour)
- View 3: "texture_details" (Wall materials, floor, key props)

FOR OBJECTS/VEHICLES:
- View 1: "studio_product_shot" (Clean background, 3 angles)
- View 2: "in_situ" (Object in the scene environment)
"""

    video_prompt_instruction = """
VIDEO PROMPT UPGRADE (CRITICAL):
The 'video_prompt' field must be highly detailed for AI Video Generators (Runway Gen-2, Pika, Kling).
Format: "[Camera Movement] + [Subject Action] + [Physics/Environment] + [Technical Specs]"
Example: "Slow dolly zoom in on character's eye, tear rolling down cheek, hair blowing gently in wind, rain falling in background, volumetric lighting, 8k resolution, high fidelity, 120fps smooth motion, shallow depth of field."
NEVER use simple phrases like "Man walking". Be specific about speed, weight, lighting changes, and atmosphere.
"""

    return f"""You are an ELITE music video director working at the highest industry standards.
Create an ULTRA-DETAILED production plan in VALID JSON format.

PROJECT BRIEF:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Theme: "{topic}"
Genre: {genre}
Visual Style: {visual_style}
Music Genre: {music_genre}
Duration: {scene_count} scenes × {seconds_per_scene} seconds
Story Elements: {story_instruction}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VISUAL STYLE ENFORCEMENT:
ALL image prompts MUST begin with: "{visual_emphasis}"
{photorealistic_extra}
{expert_instruction}
{json_detail}
{turntable_instruction}
{video_prompt_instruction}

JSON FORMAT RULES:
- Use double quotes ONLY
- NO trailing commas
- NO comments
- Escape special characters

RETURN THIS EXACT JSON STRUCTURE:
{{
  "project_title": "Title in Korean",
  "project_title_en": "Title in English",
  "logline": "One-sentence concept in Korean",
  "logline_en": "One-sentence concept in English",
  "director_vision": "2-3 sentences about artistic vision",
  
  "youtube": {{
    "title": "Viral title",
    "description": "SEO description",
    "hashtags": "tags..."
  }},
  
  "music": {{
    "style": "Korean description",
    "style_tags": "genre, mood, bpm",
    "vocal_direction": "details...",
    "instrumentation": "details...",
    "song_structure": "intro-verse-chorus...",
    "lyrics_full": "lyrics...",
    "suno_prompt_combined": "full prompt..."
  }},
  
  "turntable": {{
    "characters": [
      {{
        "id": "char1",
        "name": "Name",
        "name_en": "Name English",
        "json_profile": {{ ...FULL PHYSICAL/CLOTHING PROFILE... }},
        "views": [
            {{ "view_type": "full_turntable", "prompt": "{visual_emphasis}, character sheet, split screen, 4 distinct views, front view, side view, back view, 3/4 view, same character, full body, white background" }},
            {{ "view_type": "face_detail", "prompt": "{visual_emphasis}, extreme close up, face detail..." }},
            {{ "view_type": "expression_sheet", "prompt": "..." }},
            {{ "view_type": "fashion_detail", "prompt": "..." }},
            {{ "view_type": "cinematic_portrait", "prompt": "..." }}
        ]
      }}
      // GENERATE OBJECTS FOR ALL CHARACTERS
    ],
    "locations": [
      {{
        "id": "loc1",
        "name": "Name",
        "json_profile": {{ ...FULL LOCATION PROFILE... }},
        "views": [
            {{ "view_type": "establishing_shot", "prompt": "..." }},
            {{ "view_type": "lighting_study", "prompt": "..." }},
            {{ "view_type": "texture_details", "prompt": "..." }}
        ]
      }}
      // GENERATE OBJECTS FOR ALL LOCATIONS
    ],
    "props": [
      {{
        "id": "prop1",
        "name": "Name",
        "json_profile": {{ ... }},
        "views": [ ... ]
      }}
    ],
    "vehicles": []
  }},
  
  "scenes": [
    {{
      "scene_num": 1,
      "timecode": "00:00-...",
      "act": "1",
      "action": "Description in Korean",
      "emotion": "Emotion",
      "camera": {{ "shot_type": "...", "movement": "...", "lens": "..." }},
      "used_turntables": ["char1", "loc1"],
      "image_prompt": "{visual_emphasis}, [SCENE ACTION], [CAMERA ANGLE]. (DO NOT describe appearance here. Focus on action.)",
      "video_prompt": "CRITICAL: Highly detailed prompt for Runway/Pika. Camera movement + Action + Physics + Technicals. Minimum 20 words."
    }}
  ]
}}

Generate exactly {scene_count} scenes.
ENSURE ALL CHARACTERS/LOCATIONS mentioned in scenes have a corresponding entry in 'turntable'.
"""

# ------------------------------------------------------------------
# JSON 프로필 텍스트 변환 (개선된 버전)
# ------------------------------------------------------------------
def json_profile_to_ultra_detailed_text(profile):
    """JSON 프로필의 모든 중첩 필드를 상세 텍스트로 변환"""
    parts = []
    
    if not isinstance(profile, dict):
        return ""
    
    # 1. PHYSICAL (Physical Appearance)
    if 'physical' in profile and isinstance(profile['physical'], dict):
        phys = profile['physical']
        phys_desc = []
        if 'age' in phys: phys_desc.append(f"Age: {phys['age']}")
        if 'height_cm' in phys: phys_desc.append(f"Height: {phys['height_cm']}cm")
        if 'body_type' in phys: phys_desc.append(f"Body: {phys['body_type']}")
        if 'skin_tone' in phys: phys_desc.append(f"Skin Tone: {phys['skin_tone']}")
        if 'skin_texture' in phys: phys_desc.append(f"Skin Texture: {phys['skin_texture']}")
        if phys_desc: parts.append("PHYSICAL[" + ", ".join(phys_desc) + "]")
    
    # 2. FACE (Facial Details)
    if 'face' in profile and isinstance(profile['face'], dict):
        face = profile['face']
        face_desc = []
        if 'shape' in face: face_desc.append(f"Face Shape: {face['shape']}")
        
        if 'eyes' in face and isinstance(face['eyes'], dict):
            eyes = face['eyes']
            eye_str = []
            if 'color' in eyes: eye_str.append(f"{eyes['color']}")
            if 'shape' in eyes: eye_str.append(eyes['shape'])
            if 'size' in eyes: eye_str.append(eyes['size'])
            if 'special' in eyes: eye_str.append(eyes['special'])
            face_desc.append(f"Eyes: {' '.join(eye_str)}")
            
        if 'lips' in face and isinstance(face['lips'], dict):
            lips = face['lips']
            lip_str = []
            if 'color' in lips: lip_str.append(lips['color'])
            if 'shape' in lips: lip_str.append(lips['shape'])
            if 'texture' in lips: lip_str.append(lips['texture'])
            face_desc.append(f"Lips: {' '.join(lip_str)}")
            
        if 'nose' in face: face_desc.append(f"Nose: {face['nose']}")
        if 'jawline' in face: face_desc.append(f"Jawline: {face['jawline']}")
        if 'skin_details' in face: face_desc.append(f"Face Details: {face['skin_details']}")
        
        if 'hair' in face: # Handle nested hair in face if structured that way
             if isinstance(face['hair'], dict):
                 h = face['hair']
                 face_desc.append(f"Hair: {h.get('color', '')} {h.get('style', '')}")
        
        if face_desc: parts.append("FACE[" + ", ".join(face_desc) + "]")
    
    # 3. HAIR (Hair Details - Main)
    if 'hair' in profile and isinstance(profile['hair'], dict):
        hair = profile['hair']
        hair_desc = []
        if 'color_primary' in hair: hair_desc.append(f"Color: {hair['color_primary']}")
        if 'color_secondary' in hair: hair_desc.append(f"Highlights: {hair['color_secondary']}")
        if 'length_cm' in hair: hair_desc.append(f"Length: {hair['length_cm']}cm")
        if 'style' in hair: hair_desc.append(f"Style: {hair['style']}")
        if 'texture' in hair: hair_desc.append(f"Texture: {hair['texture']}")
        if hair_desc: parts.append("HAIR[" + ", ".join(hair_desc) + "]")
    
    # 4. CLOTHING (Detailed Outfit)
    if 'clothing' in profile and isinstance(profile['clothing'], dict):
        cloth = profile['clothing']
        outfit_desc = []
        for piece in ['top', 'bottom', 'shoes', 'outerwear']:
            if piece in cloth and isinstance(cloth[piece], dict):
                item = cloth[piece]
                item_details = []
                if 'color' in item: item_details.append(item['color'])
                if 'material' in item: item_details.append(item['material'])
                if 'type' in item: item_details.append(item['type'])
                if 'fit' in item: item_details.append(f"fit: {item['fit']}")
                if 'details' in item: item_details.append(f"detail: {item['details']}")
                if item_details:
                    outfit_desc.append(f"{piece.upper()}: {' '.join(item_details)}")
        if outfit_desc: parts.append("OUTFIT[" + ", ".join(outfit_desc) + "]")
    
    # 5. ACCESSORIES & FEATURES
    if 'accessories' in profile and isinstance(profile['accessories'], list) and profile['accessories']:
        parts.append("ACCESSORIES[" + ", ".join(profile['accessories']) + "]")
    
    if 'distinctive_features' in profile and isinstance(profile['distinctive_features'], list) and profile['distinctive_features']:
        parts.append("FEATURES[" + ", ".join(profile['distinctive_features']) + "]")
        
    # 6. LOCATION / ENVIRONMENT
    if 'location_type' in profile:
        loc_desc = [f"Type: {profile['location_type']}"]
        
        if 'architecture' in profile and isinstance(profile['architecture'], dict):
            arch = profile['architecture']
            if 'style' in arch: loc_desc.append(f"Style: {arch['style']}")
            if 'materials' in arch and isinstance(arch['materials'], list): 
                loc_desc.append(f"Materials: {', '.join(arch['materials'])}")
        
        if 'lighting' in profile and isinstance(profile['lighting'], dict):
            light = profile['lighting']
            light_strs = []
            if 'time' in light: light_strs.append(f"Time: {light['time']}")
            if 'color_temperature' in light: light_strs.append(light['color_temperature'])
            if 'key_color' in light: light_strs.append(f"Key: {light['key_color']}")
            if 'fill_color' in light: light_strs.append(f"Fill: {light['fill_color']}")
            if 'special_effects' in light: light_strs.append(light['special_effects'])
            loc_desc.append(f"LIGHTING: {' '.join(light_strs)}")
            
        if 'weather' in profile and isinstance(profile['weather'], dict):
            w = profile['weather']
            w_strs = []
            if 'condition' in w: w_strs.append(w['condition'])
            if 'humidity_percent' in w: w_strs.append(f"Humidity: {w['humidity_percent']}%")
            loc_desc.append(f"WEATHER: {' '.join(w_strs)}")
            
        if 'color_palette' in profile and isinstance(profile['color_palette'], dict):
            cp = profile['color_palette']
            cp_strs = []
            if 'dominant' in cp: cp_strs.append(f"Dom: {cp['dominant']}")
            if 'secondary' in cp: cp_strs.append(f"Sec: {cp['secondary']}")
            if 'accent' in cp: cp_strs.append(f"Acc: {cp['accent']}")
            loc_desc.append(f"PALETTE: {' '.join(cp_strs)}")
            
        if 'atmosphere' in profile: loc_desc.append(f"Mood: {profile['atmosphere']}")
        parts.append("LOCATION[" + " | ".join(loc_desc) + "]")

    # 7. PROPS / VEHICLES
    if 'make' in profile and 'model' in profile: # Vehicle
        veh_desc = f"VEHICLE[{profile.get('color', '')} {profile.get('make', '')} {profile.get('model', '')}, {profile.get('year', '')}]"
        parts.append(veh_desc)
        
    if 'dimensions' in profile: # Prop
        prop_desc = f"PROP[{profile.get('color', '')} {profile.get('material', '')} {profile.get('name', '')}, {profile.get('finish', '')} finish]"
        parts.append(prop_desc)
    
    return " ".join(parts)

def apply_json_profiles_to_prompt(base_prompt, used_turntables, turntable_data):
    """JSON 프로필을 프롬프트에 강력하게 주입"""
    if not used_turntables or not turntable_data:
        return base_prompt
    
    character_profiles = []
    location_profiles = []
    object_profiles = []
    
    for tt_ref in used_turntables:
        found = False
        # 캐릭터
        if 'characters' in turntable_data:
            for item in turntable_data['characters']:
                if item.get('id') == tt_ref:
                    name = item.get('name_en', item.get('name', 'Character'))
                    if 'json_profile' in item:
                        detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                        if detailed:
                            # 캐릭터 이름과 상세 스펙을 묶어서 전달
                            character_profiles.append(f"({name}: {detailed})")
                    found = True
                    break
        if found: continue

        # 장소
        if 'locations' in turntable_data:
            for item in turntable_data['locations']:
                if item.get('id') == tt_ref:
                    if 'json_profile' in item:
                        detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                        if detailed:
                            location_profiles.append(detailed)
                    found = True
                    break
        if found: continue
        
        # 소품/차량
        for cat in ['props', 'vehicles']:
            if cat in turntable_data:
                for item in turntable_data[cat]:
                    if item.get('id') == tt_ref:
                         if 'json_profile' in item:
                            detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                            if detailed:
                                object_profiles.append(detailed)
                         break

    # 프롬프트 조합: 캐릭터 스펙 -> 장소 스펙 -> 액션(기본 프롬프트)
    final_parts = []
    
    if character_profiles:
        final_parts.append("**CHARACTERS:** " + ", ".join(character_profiles))
    
    if location_profiles:
        final_parts.append("**LOCATION:** " + " | ".join(location_profiles))
        
    if object_profiles:
        final_parts.append("**OBJECTS:** " + ", ".join(object_profiles))
        
    final_parts.append("**SCENE ACTION:** " + base_prompt)
    
    return "\n".join(final_parts)

# ------------------------------------------------------------------
# 내보내기 함수들
# ------------------------------------------------------------------
def create_json_export(plan_data):
    return json.dumps(plan_data, ensure_ascii=False, indent=2)

def create_text_export(plan_data):
    """텍스트 형식 내보내기"""
    lines = []
    lines.append("=" * 80)
    lines.append("AI MV DIRECTOR PRO - 프로젝트 기획서")
    lines.append("=" * 80)
    lines.append(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    lines.append(f"프로젝트: {plan_data.get('project_title', '')}")
    lines.append(f"Project: {plan_data.get('project_title_en', '')}")
    lines.append(f"컨셉: {plan_data.get('logline', '')}")
    lines.append(f"Concept: {plan_data.get('logline_en', '')}")
    lines.append("")
    
    if 'director_vision' in plan_data:
        lines.append("-" * 40)
        lines.append("DIRECTOR'S VISION")
        lines.append("-" * 40)
        lines.append(plan_data['director_vision'])
        lines.append("")
    
    if 'youtube' in plan_data:
        yt = plan_data['youtube']
        lines.append("-" * 40)
        lines.append("YOUTUBE")
        lines.append("-" * 40)
        lines.append(f"제목: {yt.get('title', '')}")
        lines.append(f"설명:\n{yt.get('description', '')}")
        lines.append(f"태그: {yt.get('hashtags', '')}")
        lines.append("")
    
    if 'music' in plan_data:
        music = plan_data['music']
        lines.append("-" * 40)
        lines.append("MUSIC / SUNO AI")
        lines.append("-" * 40)
        lines.append(f"스타일: {music.get('style', '')}")
        lines.append("")
        lines.append("[STYLE TAGS]")
        lines.append(music.get('style_tags', ''))
        lines.append("")
        lines.append("[VOCAL DIRECTION]")
        lines.append(music.get('vocal_direction', ''))
        lines.append("")
        lines.append("[INSTRUMENTATION]")
        lines.append(music.get('instrumentation', ''))
        lines.append("")
        lines.append("[PRODUCTION]")
        lines.append(music.get('production', ''))
        lines.append("")
        lines.append("[SONG STRUCTURE]")
        lines.append(music.get('song_structure', ''))
        lines.append("")
        lines.append("[COMPLETE LYRICS]")
        lines.append(music.get('lyrics_full', ''))
        lines.append("")
    
    if 'turntable' in plan_data:
        tt = plan_data['turntable']
        lines.append("-" * 40)
        lines.append("TURNTABLE SHEETS")
        lines.append("-" * 40)
        
        for cat in ['characters', 'locations', 'props', 'vehicles']:
            if cat in tt and tt[cat]:
                lines.append(f"\n[{cat.upper()}]")
                for item in tt[cat]:
                    lines.append(f"\n  {item.get('name', '')} ({item.get('id', '')})")
                    if 'views' in item:
                        for view in item['views']:
                            lines.append(f"    - {view.get('view_type', '')}: {view.get('prompt', '')}")
        lines.append("")
    
    if 'scenes' in plan_data:
        lines.append("-" * 40)
        lines.append("STORYBOARD")
        lines.append("-" * 40)
        for scene in plan_data['scenes']:
            lines.append(f"\n[SCENE {scene.get('scene_num', '')}] {scene.get('timecode', '')}")
            lines.append(f"  액션: {scene.get('action', '')}")
            if 'camera' in scene and isinstance(scene['camera'], dict):
                cam = scene['camera']
                lines.append(f"  카메라: {cam.get('shot_type', '')} / {cam.get('movement', '')} / {cam.get('lens', '')}")
            lines.append(f"  이미지 프롬프트: {scene.get('image_prompt', '')}")
            lines.append(f"  비디오 프롬프트: {scene.get('video_prompt', '')}")
    
    return "\n".join(lines)

def create_html_export(plan_data):
    """HTML 형식 내보내기"""
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{plan_data.get('project_title', 'MV Project')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', -apple-system, sans-serif; background: #0a0a0a; color: #fff; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ font-size: 3em; margin-bottom: 10px; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        h2 {{ font-size: 1.8em; margin: 40px 0 20px; padding-bottom: 10px; border-bottom: 2px solid #333; }}
        h3 {{ font-size: 1.3em; margin: 20px 0 10px; color: #667eea; }}
        .section {{ background: #111; border-radius: 12px; padding: 25px; margin: 20px 0; border: 1px solid #222; }}
        .meta {{ color: #888; font-size: 0.9em; margin-bottom: 30px; }}
        .prompt-box {{ background: #1a1a2e; border-left: 4px solid #667eea; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; font-family: monospace; font-size: 0.9em; white-space: pre-wrap; word-break: break-all; }}
        .scene {{ background: #0f0f1a; border-radius: 8px; padding: 20px; margin: 15px 0; border: 1px solid #1a1a2e; }}
        .scene-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .scene-num {{ background: linear-gradient(135deg, #667eea, #764ba2); padding: 5px 15px; border-radius: 20px; font-weight: bold; }}
        .timecode {{ color: #888; font-family: monospace; }}
        .tag {{ display: inline-block; background: #222; padding: 4px 12px; border-radius: 15px; margin: 4px; font-size: 0.85em; }}
        .turntable {{ background: #1a1a0a; border: 2px solid #ffd700; border-radius: 12px; padding: 20px; margin: 15px 0; }}
        .copy-btn {{ background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 0.85em; }}
        .copy-btn:hover {{ background: #764ba2; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
        .suno-section {{ background: #1a0a1a; border: 1px solid #722ed1; border-radius: 8px; padding: 15px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 {plan_data.get('project_title', '')}</h1>
        <p class="meta">{plan_data.get('project_title_en', '')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        
        <div class="section">
            <h2>📋 프로젝트 개요</h2>
            <p><strong>컨셉:</strong> {plan_data.get('logline', '')}</p>
            <p><strong>Concept:</strong> {plan_data.get('logline_en', '')}</p>
            <p><strong>Director's Vision:</strong> {plan_data.get('director_vision', '')}</p>
        </div>
"""
    
    # YouTube
    if 'youtube' in plan_data:
        yt = plan_data['youtube']
        html += f"""
        <div class="section">
            <h2>📺 YouTube</h2>
            <h3>제목</h3>
            <div class="prompt-box">{yt.get('title', '')}</div>
            <h3>설명</h3>
            <div class="prompt-box">{yt.get('description', '')}</div>
            <h3>해시태그</h3>
            <div class="prompt-box">{yt.get('hashtags', '')}</div>
        </div>
"""
    
    # Music
    if 'music' in plan_data:
        music = plan_data['music']
        html += f"""
        <div class="section">
            <h2>🎵 Music / Suno AI</h2>
            <div class="suno-section">
                <h3>Style Tags</h3>
                <div class="prompt-box">{music.get('style_tags', '')}</div>
            </div>
            <div class="suno-section">
                <h3>Vocal Direction</h3>
                <div class="prompt-box">{music.get('vocal_direction', '')}</div>
            </div>
            <div class="suno-section">
                <h3>Instrumentation</h3>
                <div class="prompt-box">{music.get('instrumentation', '')}</div>
            </div>
            <div class="suno-section">
                <h3>Production</h3>
                <div class="prompt-box">{music.get('production', '')}</div>
            </div>
            <div class="suno-section">
                <h3>Song Structure</h3>
                <div class="prompt-box">{music.get('song_structure', '')}</div>
            </div>
            <div class="suno-section">
                <h3>Complete Lyrics</h3>
                <div class="prompt-box">{music.get('lyrics_full', '')}</div>
            </div>
            <div class="suno-section">
                <h3>🎹 Complete Suno Prompt (Copy All)</h3>
                <div class="prompt-box">{music.get('suno_prompt_combined', '')}</div>
            </div>
        </div>
"""
    
    # Turntable
    if 'turntable' in plan:
        tt = plan_data['turntable']
        html += """
        <div class="section">
            <h2>🎭 Turntable Reference Sheets</h2>
"""
        for cat in ['characters', 'locations', 'props', 'vehicles']:
            if cat in tt and tt[cat]:
                html += f"<h3>{cat.upper()}</h3><div class='grid'>"
                for item in tt[cat]:
                    html += f"""
                    <div class="turntable">
                        <h4>{item.get('name', '')} ({item.get('id', '')})</h4>
"""
                    if 'views' in item:
                        for view in item['views']:
                            html += f"""
                        <p><strong>{view.get('view_type', '')}:</strong></p>
                        <div class="prompt-box">{view.get('prompt', '')}</div>
"""
                    html += "</div>"
                html += "</div>"
        html += "</div>"
    
    # Scenes
    if 'scenes' in plan_data:
        html += """
        <div class="section">
            <h2>🎬 Storyboard</h2>
"""
        for scene in plan_data['scenes']:
            camera_info = ""
            if 'camera' in scene and isinstance(scene['camera'], dict):
                cam = scene['camera']
                camera_info = f"{cam.get('shot_type', '')} | {cam.get('movement', '')} | {cam.get('lens', '')} | {cam.get('angle', '')}"
            
            html += f"""
            <div class="scene">
                <div class="scene-header">
                    <span class="scene-num">Scene {scene.get('scene_num', '')}</span>
                    <span class="timecode">{scene.get('timecode', '')}</span>
                </div>
                <p><strong>Action:</strong> {scene.get('action', '')}</p>
                <p><strong>Camera:</strong> {camera_info}</p>
                <p><strong>Emotion:</strong> {scene.get('emotion', '')}</p>
                <h4>Image Prompt:</h4>
                <div class="prompt-box">{scene.get('image_prompt', '')}</div>
                <h4>Video Prompt:</h4>
                <div class="prompt-box">{scene.get('video_prompt', '')}</div>
            </div>
"""
        html += "</div>"
    
    html += """
    </div>
    <script>
        document.querySelectorAll('.prompt-box').forEach(box => {{
            box.style.cursor = 'pointer';
            box.title = 'Click to copy';
            box.addEventListener('click', () => {{
                navigator.clipboard.writeText(box.textContent);
                const original = box.style.borderColor;
                box.style.borderColor = '#00ff00';
                setTimeout(() => box.style.borderColor = original, 500);
            }});
        }});
    </script>
</body>
</html>"""
    return html

# ------------------------------------------------------------------
# 이미지 생성 (Segmind 추가)
# ------------------------------------------------------------------
def generate_image_segmind(prompt, width, height, api_key):
    """Segmind API를 사용한 이미지 생성"""
    if not api_key:
        return None
    
    # SDXL 1.0 모델 엔드포인트
    url = "https://api.segmind.com/v1/sdxl1.0-txt2img"
    
    payload = {
        "prompt": prompt,
        "negative_prompt": "ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, blurry, bad anatomy, blurred, watermark, grainy, signature, cut off, draft",
        "style": "cinematic",
        "samples": 1,
        "scheduler": "UniPC",
        "num_inference_steps": 25,
        "guidance_scale": 7.5,
        "seed": random.randint(1, 10000000),
        "img_width": width,
        "img_height": height,
        "base64": False
    }
    
    headers = {'x-api-key': api_key}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Segmind Error: {e}")
    return None

def try_generate_image_with_fallback(prompt, width, height, provider, max_retries=3):
    """이미지 생성 시도 및 폴백 로직"""
    enhanced = f"{prompt}, masterpiece, best quality, highly detailed"
    
    # 1. Segmind 우선 시도 (선택된 경우)
    if "Segmind" in provider:
        # 사이드바에서 설정한 segmind_key 가져오기 (전역변수 활용)
        if 'segmind_key' in globals() and segmind_key:
            img = generate_image_segmind(enhanced, width, height, segmind_key)
            if img: return img, "Segmind"
        # 키가 없거나 실패하면 Pollinations로 폴백하되 로그 남김
    
    # 2. Pollinations (기본 또는 폴백)
    if "Flux" in provider:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width={width}&height={height}&model=flux&nologo=true&seed={random.randint(0,999999)}"
    else: # Turbo or Fallback
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=90)
            if response.status_code == 200 and len(response.content) > 1000:
                img = Image.open(BytesIO(response.content))
                if img.size[0] > 100:
                    return img, provider
        except Exception as e:
            pass
        if attempt < max_retries - 1:
            time.sleep(2)
            
    return None, None

# ------------------------------------------------------------------
# API 생성
# ------------------------------------------------------------------
def generate_with_fallback(prompt, api_key, model_name):
    genai.configure(api_key=api_key)
    models_to_try = [model_name, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config={"temperature": 0.8, "max_output_tokens": 8192})
            return response.text, model_name
        except Exception as e:
            time.sleep(1)
    raise Exception("All models failed")

def generate_plan_auto(topic, api_key, model_name, scene_count, options, genre, visual_style, music_genre, use_json, expert_mode, seconds_per_scene):
    for attempt in range(3):
        try:
            prompt = get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre, use_json, expert_mode, seconds_per_scene)
            response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
            
            cleaned = clean_json_text(response_text)
            plan_data = json.loads(cleaned)
            st.toast(f"✅ 생성 완료 ({used_model})")
            return plan_data
        except json.JSONDecodeError as e:
            if attempt < 2:
                st.warning(f"JSON 파싱 재시도 중... ({attempt+1}/3) - {str(e)[:50]}")
                time.sleep(2)
            else:
                st.error(f"JSON 파싱 실패: {str(e)}")
                with st.expander("🔍 생성된 원본 응답 확인"):
                    st.code(response_text[:3000] + "..." if len(response_text) > 3000 else response_text)
                return None
        except Exception as e:
            if attempt < 2:
                st.warning(f"재시도 중... ({attempt+1}/3)")
                time.sleep(2)
            else:
                st.error(f"생성 실패: {e}")
                return None
    return None

# ------------------------------------------------------------------
# 메인 실행
# ------------------------------------------------------------------
if submit_btn:
    if not topic:
        st.warning("⚠️ 주제를 입력해주세요")
    else:
        story_opts = {
            'use_arc': use_arc, 'use_trial': use_trial,
            'use_sensory': use_sensory, 'use_dynamic': use_dynamic,
            'use_emotional': use_emotional, 'use_climax': use_climax,
            'use_symbolic': use_symbolic, 'use_twist': use_twist
        }
        
        if execution_mode == "API 자동 실행":
            if not gemini_key:
                st.warning("⚠️ API Key가 필요합니다")
            else:
                # 세션 초기화 (이미지 제외)
                st.session_state['plan_data'] = None
                st.session_state['use_json_profiles'] = use_json_profiles
                st.session_state['expert_mode'] = expert_mode
                st.session_state['image_width'] = image_width
                st.session_state['image_height'] = image_height
                st.session_state['seconds_per_scene'] = seconds_per_scene
                
                with st.spinner("🎬 전문가 수준의 기획안 생성 중... (30초-2분 소요)"):
                    st.session_state['plan_data'] = generate_plan_auto(
                        topic, gemini_key, gemini_model, scene_count, story_opts,
                        selected_genre, selected_visual, selected_music, 
                        use_json_profiles, expert_mode, seconds_per_scene
                    )
                
                if st.session_state['plan_data']:
                    st.success("✅ 기획안 생성 완료!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
        else:
            # 수동 모드
            st.session_state['manual_prompt'] = get_system_prompt(
                topic, scene_count, story_opts,
                selected_genre, selected_visual, selected_music,
                use_json_profiles, expert_mode, seconds_per_scene
            )
            st.session_state['show_manual'] = True

# 수동 모드 표시 (수정됨: 결과 붙여넣기 창 외부 노출)
if st.session_state.get('show_manual') and 'manual_prompt' in st.session_state:
    st.markdown("---")
    
    # 1. AI 프롬프트 (접을 수 있음)
    with st.expander("📋 수동 모드 - AI 프롬프트 (클릭하여 펼치기)", expanded=False):
        col_guide, col_gemini = st.columns([6, 1])
        with col_guide:
            st.caption("👇 아래 프롬프트의 우측 상단 '복사(📄)' 아이콘을 클릭하여 AI에게 전달하세요.")
        with col_gemini:
            st.link_button("🚀 Gemini", "https://gemini.google.com/app", use_container_width=True)
        
        st.code(st.session_state['manual_prompt'], language="text")
    
    # 2. 결과 붙여넣기 (항상 보임)
    st.markdown("### 📥 결과 붙여넣기 (JSON)")
    manual_result = st.text_area("AI 응답 JSON을 여기에 붙여넣으세요:", height=300, key="manual_json_input")
    
    if st.button("✅ JSON 적용", type="primary"):
        if manual_result:
            try:
                cleaned = clean_json_text(manual_result)
                st.session_state['plan_data'] = json.loads(cleaned)
                st.session_state['show_manual'] = False
                st.success("✅ 적용 완료!")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"JSON 파싱 오류: {e}")

# ------------------------------------------------------------------
# 결과 표시
# ------------------------------------------------------------------
if st.session_state.get('plan_data'):
    plan = st.session_state['plan_data']
    use_json = st.session_state.get('use_json_profiles', True)
    img_width = st.session_state.get('image_width', 1024)
    img_height = st.session_state.get('image_height', 576)
    
    st.markdown("---")
    st.header(f"🎬 {plan.get('project_title', 'Project')}")
    if 'project_title_en' in plan:
        st.caption(plan['project_title_en'])
    
    st.markdown(f"**컨셉:** {plan.get('logline', '')}")
    if 'director_vision' in plan:
        st.info(f"🎥 **Director's Vision:** {plan['director_vision']}")
    
    # 내보내기 버튼들
    st.markdown("### 💾 프로젝트 저장")
    col_save1, col_save2, col_save3, col_save4 = st.columns(4)
    with col_save1:
        st.download_button(
            "📄 JSON",
            data=create_json_export(plan),
            file_name=f"{plan.get('project_title', 'project')}.json",
            mime="application/json",
            use_container_width=True
        )
    with col_save2:
        st.download_button(
            "📝 TXT",
            data=create_text_export(plan),
            file_name=f"{plan.get('project_title', 'project')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    with col_save3:
        st.download_button(
            "🌐 HTML",
            data=create_html_export(plan),
            file_name=f"{plan.get('project_title', 'project')}.html",
            mime="text/html",
            use_container_width=True
        )
    with col_save4:
        # Markdown 형식
        md_content = f"# {plan.get('project_title', '')}\n\n{create_text_export(plan)}"
        st.download_button(
            "📋 Markdown",
            data=md_content,
            file_name=f"{plan.get('project_title', 'project')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # YouTube
    if 'youtube' in plan:
        st.markdown("## 📺 YouTube")
        yt = plan['youtube']
        st.text_input("제목", value=yt.get('title', ''), key="yt_title")
        st.text_area("설명", value=yt.get('description', ''), height=150, key="yt_desc")
        st.text_input("태그", value=yt.get('hashtags', ''), key="yt_tags")
        if 'thumbnail_concept' in yt:
            st.info(f"🖼️ 썸네일 컨셉: {yt['thumbnail_concept']}")
    
    st.markdown("---")
    
    # 음악 / Suno (탭으로 분리)
    if 'music' in plan:
        st.markdown("## 🎵 Music / Suno AI")
        music = plan['music']
        
        suno_tabs = st.tabs(["🎹 통합 프롬프트", "🏷️ Style Tags", "🎤 Vocal", "🎸 Instruments", "🎛️ Production", "📜 Structure", "📝 Lyrics"])
        
        with suno_tabs[0]:
            st.text_area("Suno 전체 프롬프트 (복사용)", 
                        value=music.get('suno_prompt_combined', music.get('suno_prompt', '')), 
                        height=400, key="suno_all")
        
        with suno_tabs[1]:
            st.text_area("Style Tags", value=music.get('style_tags', ''), height=100, key="suno_style")
        
        with suno_tabs[2]:
            st.text_area("Vocal Direction", value=music.get('vocal_direction', ''), height=100, key="suno_vocal")
        
        with suno_tabs[3]:
            st.text_area("Instrumentation", value=music.get('instrumentation', ''), height=100, key="suno_inst")
        
        with suno_tabs[4]:
            st.text_area("Production", value=music.get('production', ''), height=100, key="suno_prod")
        
        with suno_tabs[5]:
            st.text_area("Song Structure", value=music.get('song_structure', ''), height=300, key="suno_struct")
        
        with suno_tabs[6]:
            st.text_area("Complete Lyrics", value=music.get('lyrics_full', ''), height=300, key="suno_lyrics")
    
    st.markdown("---")
    
    # 턴테이블
    if 'turntable' in plan:
        st.markdown("## 🎭 Turntable Reference Sheets")
        
        # 전체 생성 버튼
        if st.button("🎨 모든 턴테이블 이미지 생성", use_container_width=True, type="primary", key="gen_all_tt"):
            progress = st.progress(0)
            status = st.empty()
            
            total_views = 0
            for cat in ['characters', 'locations', 'props', 'vehicles']:
                if cat in plan['turntable']:
                    for item in plan['turntable'][cat]:
                        if 'views' in item:
                            total_views += len(item['views'])
            
            current = 0
            for cat in ['characters', 'locations', 'props', 'vehicles']:
                if cat in plan['turntable']:
                    for item in plan['turntable'][cat]:
                        if 'views' in item:
                            for view in item['views']:
                                item_name = item.get('name', '')
                                view_type = view.get('view_type', '')
                                tt_key = f"{cat}_{item.get('id', '')}_{view_type}"
                                
                                status.markdown(f"<div class='status-box'>생성 중: {item_name} - {view_type}</div>", unsafe_allow_html=True)
                                
                                final_prompt = view.get('prompt', '')
                                if use_json and 'json_profile' in item:
                                    detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                                    if detailed:
                                        final_prompt = f"{detailed}, {final_prompt}"
                                
                                img, _ = try_generate_image_with_fallback(final_prompt, 1024, 1024, image_provider, max_retries)
                                
                                if img:
                                    if 'turntable_images' not in st.session_state:
                                        st.session_state['turntable_images'] = {}
                                    st.session_state['turntable_images'][tt_key] = img
                                
                                current += 1
                                progress.progress(current / total_views)
                                time.sleep(0.5)
            
            status.markdown("<div class='status-box'>✅ 턴테이블 생성 완료!</div>", unsafe_allow_html=True)
            st.rerun()
        
        # 카테고리별 표시
        for cat in ['characters', 'locations', 'props', 'vehicles']:
            if cat in plan['turntable'] and plan['turntable'][cat]:
                st.markdown(f"### {'👤' if cat=='characters' else '🏠' if cat=='locations' else '📦' if cat=='props' else '🚗'} {cat.upper()}")
                
                for item in plan['turntable'][cat]:
                    st.markdown(f"<div class='turntable-box'>", unsafe_allow_html=True)
                    st.markdown(f"**{item.get('name', '')}** (ID: {item.get('id', '')})")
                    
                    if 'json_profile' in item:
                        with st.expander("📊 JSON 프로필"):
                            st.json(item['json_profile'])
                    
                    if 'views' in item:
                        cols = st.columns(min(len(item['views']), 4))
                        for idx, view in enumerate(item['views']):
                            with cols[idx % 4]:
                                view_type = view.get('view_type', '')
                                tt_key = f"{cat}_{item.get('id', '')}_{view_type}"
                                
                                st.caption(view_type.upper())
                                
                                if tt_key in st.session_state.get('turntable_images', {}):
                                    st.image(st.session_state['turntable_images'][tt_key], use_container_width=True)
                                else:
                                    if st.button(f"📸", key=f"g_{tt_key}"):
                                        final_prompt = view.get('prompt', '')
                                        if use_json and 'json_profile' in item:
                                            detailed = json_profile_to_ultra_detailed_text(item['json_profile'])
                                            if detailed:
                                                final_prompt = f"{detailed}, {final_prompt}"
                                        
                                        with st.spinner("생성 중..."):
                                            img, _ = try_generate_image_with_fallback(final_prompt, 1024, 1024, image_provider, max_retries)
                                        if img:
                                            if 'turntable_images' not in st.session_state:
                                                st.session_state['turntable_images'] = {}
                                            st.session_state['turntable_images'][tt_key] = img
                                            st.rerun()
                                
                                with st.expander("프롬프트"):
                                    st.code(view.get('prompt', ''), language=None)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 씬/스토리보드
    if 'scenes' in plan:
        st.markdown("## 🎬 Storyboard")
        
        # 전체 씬 생성 버튼
        if st.button("🎨 모든 씬 이미지 생성", use_container_width=True, type="primary", key="gen_all_scenes"):
            scenes = plan['scenes']
            progress = st.progress(0)
            status = st.empty()
            
            for idx, scene in enumerate(scenes):
                scene_num = scene.get('scene_num', idx+1)
                status.markdown(f"<div class='status-box'>Scene {scene_num} 생성 중...</div>", unsafe_allow_html=True)
                
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
                
                progress.progress((idx + 1) / len(scenes))
                time.sleep(0.5)
            
            status.markdown("<div class='status-box'>✅ 씬 이미지 생성 완료!</div>", unsafe_allow_html=True)
            st.rerun()
        
        # 개별 씬 표시
        for scene in plan.get('scenes', []):
            scene_num = scene.get('scene_num', 0)
            
            st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**Scene {scene_num}** - {scene.get('timecode', '')}")
                if 'act' in scene:
                    st.caption(f"Act {scene['act']} | {scene.get('beat', '')}")
                if 'used_turntables' in scene and scene['used_turntables']:
                    for tt in scene['used_turntables']:
                        st.markdown(f"<span class='turntable-tag'>🎭 {tt}</span>", unsafe_allow_html=True)
            with col2:
                if scene_num in st.session_state.get('generated_images', {}):
                    if st.button("🔄", key=f"r_s_{scene_num}"):
                        del st.session_state['generated_images'][scene_num]
                        st.rerun()
            
            # 이미지 표시 또는 생성 버튼
            if scene_num in st.session_state.get('generated_images', {}):
                st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
            else:
                if st.button(f"📸 이미지 생성", key=f"g_s_{scene_num}"):
                    base = scene.get('image_prompt', '')
                    if use_json and 'used_turntables' in scene:
                        final = apply_json_profiles_to_prompt(base, scene['used_turntables'], plan.get('turntable', {}))
                    else:
                        final = base
                    
                    with st.spinner("생성 중..."):
                        img, _ = try_generate_image_with_fallback(final, img_width, img_height, image_provider, max_retries)
                    if img:
                        if 'generated_images' not in st.session_state:
                            st.session_state['generated_images'] = {}
                        st.session_state['generated_images'][scene_num] = img
                        st.rerun()
            
            # 씬 정보
            st.write(f"**액션:** {scene.get('action', '')}")
            if 'camera' in scene:
                if isinstance(scene['camera'], dict):
                    cam = scene['camera']
                    st.write(f"**카메라:** {cam.get('shot_type', '')} | {cam.get('movement', '')} | {cam.get('lens', '')} | {cam.get('angle', '')}")
                else:
                    st.write(f"**카메라:** {scene['camera']}")
            if 'emotion' in scene:
                st.write(f"**감정:** {scene['emotion']}")
            
            with st.expander("🖼️ 이미지 프롬프트"):
                # 실제 생성에 사용될 최종 프롬프트 표시
                final_debug = scene.get('image_prompt', '')
                if use_json and 'used_turntables' in scene:
                    final_debug = apply_json_profiles_to_prompt(final_debug, scene['used_turntables'], plan.get('turntable', {}))
                st.code(final_debug)
            
            with st.expander("🎬 비디오 프롬프트 (Runway/Pika/Kling 용)"):
                st.code(scene.get('video_prompt', ''))
            
            st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("🎬 AI MV Director Pro | Powered by Gemini & Segmind & Pollinations")
