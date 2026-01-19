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

with st.expander("📝 프로젝트 설정 (터치하여 열기)", expanded=True):
    with st.form("project_form"):
        topic = st.text_area("영상 주제를 입력하세요", height=80, placeholder="예: 2050년 사이버펑크 서울, 비 오는 밤, 고독한 형사")
        
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

def get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre):
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
    You are a professional Music Video Director and YouTube Content Strategist.
    
    Theme: "{topic}"
    Genre: {genre}
    Visual Style: {visual_style}
    Music Genre: {music_genre}
    
    Create a comprehensive production plan with {scene_count} scenes in JSON format ONLY.
    
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
            "name": "Character name (Korean)",
            "prompt": "Turntable shot in {visual_style} style: full body character turnaround, white background, 360 degree view, character design sheet, multiple angles, front view, side view, back view, 3/4 view, detailed character description for {genre} genre..."
          }}
        ],
        "backgrounds": [
          {{
            "name": "Location name (Korean)",
            "prompt": "Turntable shot in {visual_style} style: environment 360 rotation, detailed {genre} location, architectural details, lighting, atmosphere..."
          }}
        ],
        "objects": [
          {{
            "name": "Object name (Korean)",
            "prompt": "Turntable shot in {visual_style} style: product photography, 360 degree rotation, white background, detailed object for {genre} setting..."
          }}
        ]
      }},
      "scenes": [
        {{
          "scene_num": 1,
          "timecode": "00:00-00:05",
          "action": "Scene description (Korean)",
          "camera": "Shot type (Korean)",
          "image_prompt": "{visual_style} style, {genre} aesthetic, highly detailed English prompt for image generation.",
          "video_prompt": "Detailed English prompt for video generation in {visual_style} style describing movement, camera motion, and transitions for {genre} feel."
        }}
        // Create {scene_count} scenes with proper timing
      ]
    }}
    
    CRITICAL REQUIREMENTS:
    - YouTube title must be viral-optimized with power words, emotional triggers, under 60 characters
    - Description must include timestamps and be SEO-optimized
    - Hashtags: NO # symbols, comma-separated, trending keywords
    - Suno prompt: Include [Verse], [Chorus], [Bridge] markers, BPM (e.g., "130 BPM"), key (e.g., "E minor"), specific instruments
    - All visual prompts must incorporate {visual_style} aesthetic
    - Genre-appropriate tone throughout: {genre}
    """

def get_youtube_metadata_prompt(plan_data):
    """유튜브 메타데이터만 별도 생성"""
    return f"""
    Create viral-optimized YouTube metadata for this AI-generated music video:
    
    Title: {plan_data['project_title']}
    Concept: {plan_data['logline']}
    
    Generate JSON:
    {{
      "title": "Viral English title (50-60 chars) with emotional hook + '| AI Generated' at end",
      "description": "SEO-optimized description (250-300 words) including: hook paragraph, scene timestamps, emotional journey, technical details, call-to-action, subtle AI disclosure",
      "hashtags": "30, viral, trending, keywords, separated, by, commas, no, hash, symbols, optimized, for, discovery"
    }}
    
    Title formula: [Emotional Hook] + [Core Concept] + [Intrigue] | AI Generated
    Example: "Lost in Neon Dreams - A Cyberpunk Love Story That Will Break Your Heart | AI Generated"
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

def generate_plan_auto(topic, api_key, model_name, scene_count, options, genre, visual_style, music_genre):
    try:
        prompt = get_system_prompt(topic, scene_count, options, genre, visual_style, music_genre)
        response_text, used_model = generate_with_fallback(prompt, api_key, model_name)
        st.toast(f"✅ 기획 생성 완료 (Used: {used_model})")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"기획안 생성 실패: {e}")
        return None

# ------------------------------------------------------------------
# 2. 향상된 이미지 생성 로직 (무한 재시도 지원)
# ------------------------------------------------------------------

def try_generate_image_with_fallback(prompt, width, height, provider, max_retries=3):
    """
    선택된 엔진으로 이미지 생성 시도 (무한 재시도 지원)
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
    else:  # Image.AI, Segmind
        endpoints = [
            {
                'name': provider,
                'url': f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width={width}&height={height}&nologo=true&seed={random.randint(0,999999)}"
            }
        ]
    
    # 공통 폴백
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
# 3. 저장 기능
# ------------------------------------------------------------------

def create_html_export(plan_data, images_dict, turntable_dict):
    """HTML 형식으로 전체 프로젝트 저장"""
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
        html_content += '<div class="section"><h2>🎭 Turntable References</h2>'
        
        for category in ['characters', 'backgrounds', 'objects']:
            if category in plan_data['turntable'] and plan_data['turntable'][category]:
                html_content += f'<h3>{"👤 Characters" if category == "characters" else "🏙️ Backgrounds" if category == "backgrounds" else "📦 Objects"}</h3>'
                
                for item in plan_data['turntable'][category]:
                    tt_key = f"{category}_{item['name']}"
                    html_content += f'<div class="turntable"><h4>{item["name"]}</h4>'
                    
                    if tt_key in turntable_dict:
                        # 이미지를 base64로 인코딩
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
        text += f"\n{'='*80}\nTURNTABLE REFERENCES\n{'='*80}\n\n"
        
        for category in ['characters', 'backgrounds', 'objects']:
            if category in plan_data['turntable'] and plan_data['turntable'][category]:
                text += f"\n{category.upper()}:\n{'-'*80}\n"
                for item in plan_data['turntable'][category]:
                    text += f"\n{item['name']}:\n{item['prompt']}\n\n"
    
    # 씬들
    text += f"\n{'='*80}\nSTORYBOARD\n{'='*80}\n\n"
    
    for scene in plan_data['scenes']:
        text += f"""
Scene {scene['scene_num']} - {scene['timecode']}
{'-'*80}
ACTION: {scene['action']}
CAMERA: {scene['camera']}

IMAGE PROMPT:
{scene['image_prompt']}

VIDEO PROMPT:
{scene.get('video_prompt', 'N/A')}

"""
    
    return text

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
        st.session_state['turntables_generated'] = False
        
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
            
        st.session_state['plan_data'] = generate_plan_auto(
            topic, gemini_key, gemini_model, scene_count, story_opts,
            selected_genre, selected_visual, selected_music
        )
        
        if st.session_state['plan_data']:
            plan = st.session_state['plan_data']
            st.session_state['prompts_generated'] = True
            
            # 기획안 표시
            with plan_container.container():
                st.markdown("<div class='status-box'>✅ 기획안 및 프롬프트 생성 완료!</div>", unsafe_allow_html=True)
                st.subheader(f"🎥 {plan['project_title']}")
                st.info(plan['logline'])
                
                # YouTube 메타데이터 미리보기
                if 'youtube' in plan:
                    with st.expander("📺 YouTube 메타데이터 미리보기", expanded=True):
                        st.markdown(f"**제목:** {plan['youtube']['title']}")
                        st.markdown("**설명:**")
                        st.text(plan['youtube']['description'])
                        st.markdown(f"**해시태그:** #{plan['youtube']['hashtags'].replace(', ', ' #')}")
                
                with st.expander("📋 전체 기획안 보기", expanded=False):
                    st.markdown(f"**음악 스타일:** {plan['music']['style']}")
                    st.code(plan['music']['suno_prompt'], language="text")
                    st.markdown(f"**비주얼 스타일:** {plan['visual_style']['description']}")
                    st.code(plan['visual_style']['character_prompt'], language="text")
                
                # 턴테이블 프롬프트
                if 'turntable' in plan:
                    st.markdown("---")
                    st.markdown("### 🎭 턴테이블 레퍼런스 프롬프트")
                    
                    turntable = plan['turntable']
                    
                    if turntable.get('characters'):
                        st.markdown("**👤 캐릭터**")
                        for char in turntable['characters']:
                            with st.expander(f"🎭 {char['name']}", expanded=False):
                                st.code(char['prompt'], language="text")
                    
                    if turntable.get('backgrounds'):
                        st.markdown("**🏙️ 배경**")
                        for bg in turntable['backgrounds']:
                            with st.expander(f"🏙️ {bg['name']}", expanded=False):
                                st.code(bg['prompt'], language="text")
                    
                    if turntable.get('objects'):
                        st.markdown("**📦 오브젝트**")
                        for obj in turntable['objects']:
                            with st.expander(f"📦 {obj['name']}", expanded=False):
                                st.code(obj['prompt'], language="text")
                
                # 씬 프롬프트
                st.markdown("---")
                st.markdown("### 📝 씬 프롬프트 미리보기")
                
                for scene in plan['scenes']:
                    with st.expander(f"🎬 Scene {scene['scene_num']} - {scene['action'][:50]}...", expanded=False):
                        st.caption(f"⏱️ {scene['timecode']}")
                        st.write(f"**액션:** {scene['action']}")
                        st.write(f"**카메라:** {scene['camera']}")
                        
                        st.markdown("**이미지 프롬프트:**")
                        full_img_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                        st.code(full_img_prompt, language="text")
                        
                        if 'video_prompt' in scene:
                            st.markdown("**영상 프롬프트:**")
                            st.code(scene['video_prompt'], language="text")
            
            # 2. 자동 이미지 생성
            if auto_generate:
                st.markdown("---")
                
                # 턴테이블 자동 생성
                if 'turntable' in plan:
                    st.markdown("### 🎭 턴테이블 이미지 자동 생성")
                    
                    turntable = plan['turntable']
                    all_turntables = []
                    
                    if turntable.get('characters'):
                        for char in turntable['characters']:
                            all_turntables.append(('character', char))
                    if turntable.get('backgrounds'):
                        for bg in turntable['backgrounds']:
                            all_turntables.append(('background', bg))
                    if turntable.get('objects'):
                        for obj in turntable['objects']:
                            all_turntables.append(('object', obj))
                    
                    if all_turntables:
                        progress_bar_tt = st.progress(0)
                        status_container_tt = st.container()
                        
                        for idx, (tt_type, tt_item) in enumerate(all_turntables):
                            tt_key = f"{tt_type}_{tt_item['name']}"
                            
                            with status_container_tt:
                                st.markdown(f"<div class='status-box'>🎭 {tt_item['name']} 턴테이블 생성 중... ({idx+1}/{len(all_turntables)})</div>", unsafe_allow_html=True)
                            
                            img, provider = try_generate_image_with_fallback(
                                tt_item['prompt'],
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
                
                # 씬 이미지 자동 생성
                st.markdown("### 🎨 씬 이미지 자동 생성")
                total_scenes = len(plan['scenes'])
                
                progress_bar = st.progress(0)
                status_container = st.container()
                
                for idx, scene in enumerate(plan['scenes']):
                    scene_num = scene['scene_num']
                    
                    with status_container:
                        st.markdown(f"<div class='status-box'>🎬 Scene {scene_num} 이미지 생성 중... ({idx+1}/{total_scenes})</div>", unsafe_allow_html=True)
                    
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
    
    selected_genre_manual = selected_genre if 'selected_genre' in locals() else VIDEO_GENRES[0]
    selected_visual_manual = selected_visual if 'selected_visual' in locals() else VISUAL_STYLES[0]
    selected_music_manual = selected_music if 'selected_music' in locals() else MUSIC_GENRES[0]
    
    prompt_to_copy = get_system_prompt(
        topic, st.session_state.scene_count, story_opts,
        selected_genre_manual, selected_visual_manual, selected_music_manual
    ) if topic else "주제를 먼저 입력해주세요."
    
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
# 4. 결과 표시
# ------------------------------------------------------------------

if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    
    st.markdown("---")
    
    # YouTube 메타데이터 섹션
    if 'youtube' in plan:
        st.markdown("<div class='youtube-box'>", unsafe_allow_html=True)
        st.markdown("## 📺 YouTube 메타데이터")
        
        st.markdown("### 📌 제목")
        st.text_input("복사하세요", value=plan['youtube']['title'], key="yt_title", label_visibility="collapsed")
        
        st.markdown("### 📝 설명")
        st.text_area("복사하세요", value=plan['youtube']['description'], height=200, key="yt_desc", label_visibility="collapsed")
        
        st.markdown("### 🏷️ 해시태그")
        hashtags_formatted = plan['youtube']['hashtags']
        st.text_area("복사하세요 (쉼표로 구분)", value=hashtags_formatted, height=100, key="yt_tags", label_visibility="collapsed")
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
    
    # 음악 프롬프트 섹션
    st.markdown("### 🎵 Suno AI 음악 프롬프트")
    with st.expander("🎼 음악 생성 프롬프트 보기", expanded=False):
        st.markdown(f"**스타일:** {plan['music']['style']}")
        st.code(plan['music']['suno_prompt'], language="text")
        if 'tags' in plan['music']:
            st.caption(f"태그: {plan['music']['tags']}")
    
    st.markdown("---")
    
    # 저장 버튼들
    st.markdown("### 💾 프로젝트 저장")
    col_save1, col_save2, col_save3 = st.columns(3)
    
    with col_save1:
        # HTML 저장
        html_content = create_html_export(plan, st.session_state['generated_images'], st.session_state['turntable_images'])
        st.download_button(
            label="📄 HTML 다운로드",
            data=html_content,
            file_name=f"{plan['project_title']}_project.html",
            mime="text/html",
            use_container_width=True
        )
    
    with col_save2:
        # JSON 저장
        json_content = create_json_export(plan)
        st.download_button(
            label="📋 JSON 다운로드",
            data=json_content,
            file_name=f"{plan['project_title']}_project.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_save3:
        # TXT 저장
        txt_content = create_text_export(plan)
        st.download_button(
            label="📝 TXT 다운로드",
            data=txt_content,
            file_name=f"{plan['project_title']}_project.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 턴테이블 섹션
    if 'turntable' in plan:
        st.markdown("### 🎭 턴테이블 레퍼런스")
        
        turntable = plan['turntable']
        all_turntables = []
        
        if turntable.get('characters'):
            for char in turntable['characters']:
                all_turntables.append(('character', char))
        if turntable.get('backgrounds'):
            for bg in turntable['backgrounds']:
                all_turntables.append(('background', bg))
        if turntable.get('objects'):
            for obj in turntable['objects']:
                all_turntables.append(('object', obj))
        
        if all_turntables:
            if st.button("🔄 모든 턴테이블 재생성", use_container_width=True):
                st.session_state['turntable_images'] = {}
                st.session_state['turntable_status'] = {}
                st.rerun()
            
            for tt_type, tt_item in all_turntables:
                tt_key = f"{tt_type}_{tt_item['name']}"
                
                st.markdown(f"<div class='turntable-box'>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    icon = "👤" if tt_type == "character" else "🏙️" if tt_type == "background" else "📦"
                    st.markdown(f"#### {icon} {tt_item['name']}")
                with col2:
                    if tt_key in st.session_state['turntable_images']:
                        if st.button("🔄", key=f"regen_tt_{tt_key}", help="재생성"):
                            del st.session_state['turntable_images'][tt_key]
                            st.rerun()
                
                if tt_key in st.session_state['turntable_images']:
                    st.image(st.session_state['turntable_images'][tt_key], use_container_width=True)
                    if tt_key in st.session_state['turntable_status']:
                        st.caption(st.session_state['turntable_status'][tt_key])
                else:
                    if tt_key in st.session_state['turntable_status']:
                        st.markdown(f"<div class='error-box'>{st.session_state['turntable_status'][tt_key]}</div>", unsafe_allow_html=True)
                    
                    if st.button(f"📸 생성", key=f"gen_tt_{tt_key}"):
                        with st.spinner("🎨 이미지 생성 중..."):
                            img, provider = try_generate_image_with_fallback(
                                tt_item['prompt'],
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
                                st.error("이미지 생성 실패")
                
                with st.expander("📝 프롬프트 보기"):
                    st.code(tt_item['prompt'], language="text")
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # 스토리보드 섹션
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
                    full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                    st.code(full_prompt, language="text")

    for scene in plan['scenes']:
        scene_num = scene['scene_num']
        
        st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"#### Scene {scene_num} - {scene['timecode']}")
        with col2:
            if scene_num in st.session_state['generated_images']:
                if st.button("🔄", key=f"regen_{scene_num}", help="이미지 재생성"):
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
                        st.error("이미지 생성 실패")

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
