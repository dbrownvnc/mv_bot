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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Page Configuration ---
st.set_page_config(page_title="AI MV Director (Final)", layout="wide")

# --- CSS Styling ---
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
    .regen-btn {
        background-color: #f0f2f6;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# --- API Key Loader ---
def get_api_key(key_name):
    # 1. Check Streamlit Secrets
    if key_name in st.secrets:
        return st.secrets[key_name]
    # 2. Check Environment Variables
    elif os.getenv(key_name):
        return os.getenv(key_name)
    return None

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Settings (Final)")
    
    # 1. Google Gemini API Key
    gemini_key = get_api_key("GOOGLE_API_KEY")
    if gemini_key:
        st.success("✅ Gemini Key Connected")
    else:
        gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.markdown("---")
    
    # 2. Hugging Face Token
    hf_token = get_api_key("HF_TOKEN")
    if hf_token:
        st.success("✅ Hugging Face Token Connected")
    else:
        hf_token = st.text_input("Hugging Face Token", type="password", help="Enter a token with Write permissions.")
        st.caption("[👉 Get Token](https://huggingface.co/settings/tokens)")
    
    st.markdown("---")
    
    # 3. Model Selection
    st.subheader("🎨 Image Model Selection")
    
    hf_model_id = st.selectbox(
        "Model ID",
        [
            "black-forest-labs/FLUX.1-dev",     # Best Quality
            "black-forest-labs/FLUX.1-schnell", # Fast
            "stabilityai/stable-diffusion-xl-base-1.0", # Stable
        ],
        index=0,
        help="FLUX.1-dev offers the best quality."
    )

    st.markdown("---")
    if st.button("🗑️ Reset Project"):
        st.session_state.clear()
        st.rerun()

# --- Main Title ---
st.title("🎬 AI MV Director (Final)")
st.subheader("Seamless High-Quality Storyboards & Auto-Fallback")

topic = st.text_area("Enter Video Theme", height=80, placeholder="Ex: Cyberpunk Seoul 2050, Rainy Neon Streets, Solitary Detective")

# ---------------------------------------------------------
# [UPDATED] Robust Gemini Logic from app_final_v84.py
# ---------------------------------------------------------

def clean_json_text(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match: return match.group(1)
    return text

def generate_with_fallback(prompt, api_key, start_model="gemini-2.0-flash"):
    """
    Robust generation logic extracted from app_final_v84.py
    Handles 429 errors and automatically switches to backup models.
    """
    genai.configure(api_key=api_key)
    
    # Fallback Chain Strategy:
    # 1. Try specified start model (e.g., 2.0 Flash)
    # 2. If 429/Quota error, switch to 1.5 Flash (high quota)
    # 3. Then try lightweight or older models
    
    fallback_chain = [
        start_model,
        "gemini-1.5-flash",        # High quota, very stable
        "gemini-1.5-flash-8b",     # Lightweight
        "gemini-1.5-pro",          # High intelligence
        "gemini-1.0-pro"           # Legacy backup
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_chain = []
    for m in fallback_chain:
        if m not in seen and m:
            unique_chain.append(m)
            seen.add(m)

    last_error = None
    
    for model_name in unique_chain:
        try:
            # Attempt generation
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # Success: Wait briefly to prevent rate limits
            time.sleep(1) 
            return response.text, model_name 
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            # Handle Quota (429) errors specifically
            if "429" in error_str or "Quota" in error_str:
                print(f"⚠️ {model_name} Quota Exceeded (429). Switching to backup model.")
                time.sleep(0.5)
                continue
            
            # Handle other errors (404, etc.)
            time.sleep(0.5)
            continue
            
    # If all models fail
    raise Exception(f"All models failed. Last Error: {last_error}\nPlease check your API Key or Quota.")

def generate_plan_gemini(topic, api_key):
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
        # Using the robust fallback function
        response_text, _ = generate_with_fallback(prompt, api_key, "gemini-2.0-flash")
        return json.loads(clean_json_text(response_text))
    except Exception as e:
        st.error(f"Planning Error: {e}")
        return None

# ---------------------------------------------------------
# Hugging Face Image Generation (Your existing logic)
# ---------------------------------------------------------

def generate_image_hf(prompt, token, model_id):
    """
    Generates image using Hugging Face Inference API.
    Includes auto-wait for 503 (Model Loading) errors.
    """
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    seed = random.randint(0, 999999) 
    
    # Payload for Flux and similar models
    payload = {
        "inputs": f"{prompt}, cinematic lighting, 8k, high quality",
        "parameters": {"seed": seed} 
    }

    # Retry up to 5 times (to wake up cold models)
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            
            elif "estimated_time" in response.json():
                wait_time = response.json().get("estimated_time", 10)
                st.toast(f"😴 Waking up model... ({wait_time:.1f}s)")
                time.sleep(wait_time + 1)
                continue
            else:
                print(f"Error: {response.text}")
                break
                
        except Exception as e:
            time.sleep(1)
            
    return None

# --- Execution Logic ---

if 'plan_data' not in st.session_state:
    st.session_state['plan_data'] = None
if 'generated_images' not in st.session_state:
    st.session_state['generated_images'] = {} 

start_btn = st.button("🚀 Start Project")

if start_btn:
    if not gemini_key or not topic:
        st.warning("Please enter Google API Key and Topic.")
    elif not hf_token:
        st.warning("Hugging Face Token is required.")
    else:
        with st.status("📝 Creating Plan...", expanded=True) as status:
            st.session_state['generated_images'] = {} 
            st.session_state['plan_data'] = generate_plan_gemini(topic, gemini_key)
            status.update(label="Plan Created!", state="complete", expanded=False)

# Display Results
if st.session_state['plan_data']:
    plan = st.session_state['plan_data']
    
    st.divider()
    st.markdown(f"## 🎥 {plan['project_title']}")
    st.info(f"**Logline:** {plan['logline']}")
    
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
    st.subheader(f"🖼️ Visual Storyboard (Model: {hf_model_id.split('/')[-1]})")

    for scene in plan['scenes']:
        scene_num = scene['scene_num']
        
        with st.container():
            st.markdown(f"<div class='scene-box'>", unsafe_allow_html=True)
            st.markdown(f"#### 🎬 Scene {scene_num} <span style='font-size:0.8em; color:gray'>({scene['timecode']})</span>", unsafe_allow_html=True)
            
            col_text, col_img = st.columns([1, 1.5])
            
            with col_text:
                st.write(f"**Action:** {scene['action']}")
                st.write(f"**Shot:** {scene['camera']}")
                with st.expander("Prompt Details"):
                    st.code(scene['image_prompt'], language="text")
            
            with col_img:
                # 1. Display existing image
                if scene_num in st.session_state['generated_images']:
                    st.image(st.session_state['generated_images'][scene_num], use_container_width=True)
                else:
                    # 2. Attempt generation via HF API
                    if hf_token:
                        with st.spinner("📸 Filming..."):
                             full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                             
                             img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                             
                             if img_data:
                                 st.session_state['generated_images'][scene_num] = img_data
                                 st.image(img_data, use_container_width=True)
                             else:
                                 st.error("Generation Failed (Check Token/Model)")
                    else:
                        st.info("Please enter HF Token.")

                # 3. Regenerate Button
                if st.button(f"🔄 Retake", key=f"regen_{scene_num}"):
                     if hf_token:
                        with st.spinner("📸 Retaking..."):
                            full_prompt = f"{plan['visual_style']['character_prompt']}, {scene['image_prompt']}"
                            img_data = generate_image_hf(full_prompt, hf_token, hf_model_id)
                            
                            if img_data:
                                st.session_state['generated_images'][scene_num] = img_data
                                st.rerun()
                     else:
                         st.error("Token required.")
            
            st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state['generated_images']) == len(plan['scenes']):
        st.success("✨ Storyboard Complete!")
