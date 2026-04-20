import streamlit as st
import os
import time
import re
import uuid
import json
import concurrent.futures
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image

from google import genai
from google.genai import types
from google.cloud import firestore
from google.oauth2 import service_account

# ReportLab PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Image as RLImage, Table, TableStyle
)
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors

# Matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# ----------------------------- #
# 1) GLOBAL CONSTANTS & STYLING #
# ----------------------------- #
st.set_page_config(page_title="helix.ai - Cambridge (CIE) Tutor", page_icon="📚", layout="centered")

# --- INTEGRATED API KEY ---
PROVIDED_API_KEY = "AIzaSyCJ5kTedYLBjbTsCt9p7NBsbE-jsfH7sxM"
api_key = os.environ.get("GOOGLE_API_KEY") or PROVIDED_API_KEY

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"🚨 GenAI Error: {e}")
    st.stop()

quiz_bg_state = st.session_state.get("quiz_bg", "default")
if quiz_bg_state == "correct":
    bg_style = "radial-gradient(circle at 50% 50%, rgba(46, 204, 113, 0.25) 0%, #0a0a1a 80%)"
elif quiz_bg_state == "wrong":
    bg_style = "radial-gradient(circle at 50% 50%, rgba(231, 76, 60, 0.25) 0%, #0a0a1a 80%)"
else:
    bg_style = "radial-gradient(800px circle at 50% 0%, rgba(0, 212, 255, 0.12), rgba(0, 212, 255, 0.00) 60%), #0a0a1a"

st.markdown(f"""
<style>
/* Core App Background & Typography */
.stApp {{ background: {bg_style} !important; transition: background 0.6s ease-in-out; color: #f5f5f7 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important; }}
/* Sidebar Glassmorphism */[data-testid="stSidebar"] {{ background: rgba(25, 25, 35, 0.4) !important; backdrop-filter: blur(40px) !important; -webkit-backdrop-filter: blur(40px) !important; border-right: 1px solid rgba(255, 255, 255, 0.08) !important; }}
/* Native Streamlit Form & Container Glass UI */[data-testid="stForm"],[data-testid="stVerticalBlockBorderWrapper"] {{ background: rgba(255, 255, 255, 0.04) !important; backdrop-filter: blur(40px) !important; -webkit-backdrop-filter: blur(40px) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; border-radius: 28px !important; padding: 24px !important; box-shadow: 0 16px 40px 0 rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important; margin: 20px 0 !important; }}

/* Glass Chat Bubbles */
[data-testid="stChatMessage"] {{ 
     background: rgba(255, 255, 255, 0.05) !important; 
     backdrop-filter: blur(24px) !important; 
     -webkit-backdrop-filter: blur(24px) !important; 
     border: 1px solid rgba(255, 255, 255, 0.12) !important; 
     border-radius: 28px !important; 
     padding: 20px !important; 
     box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important; 
     color: #fff !important; 
     margin-bottom: 16px;
     word-wrap: break-word !important;
     overflow-wrap: break-word !important;
     white-space: normal !important;
}}
[data-testid="stChatMessage"] * {{ color: #f5f5f7 !important; }}
[data-testid="stChatMessage"] table {{ display: block !important; overflow-x: auto !important; max-width: 100% !important; }}
[data-testid="stChatMessage"] pre, [data-testid="stChatMessage"] code {{ white-space: pre-wrap !important; word-break: break-word !important; }}

.stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>textarea, .stNumberInput>div>div>input {{ background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 12px !important; color: #fff !important; }}
.stChatInputContainer {{ background: transparent !important; }}
.stButton>button {{ background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.02) 100%) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 20px !important; backdrop-filter: blur(20px) !important; color: #fff !important; font-weight: 600 !important; transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important; }}

.thinking-container {{ display: flex; align-items: center; gap: 8px; padding: 12px 16px; background-color: rgba(255,255,255,0.05); border-radius: 16px; margin: 10px 0; border-left: 3px solid #fc8404; backdrop-filter: blur(10px); }}
.thinking-text {{ color: #fc8404; font-size: 14px; font-weight: 600; }}
.thinking-dots {{ display: flex; gap: 4px; }}
.thinking-dot {{ width: 6px; height: 6px; border-radius: 50%; background-color: #fc8404; animation: thinking-pulse 1.4s infinite; }}
.thinking-dot:nth-child(2){{animation-delay: 0.2s;}}
.thinking-dot:nth-child(3){{animation-delay: 0.4s;}}
@keyframes thinking-pulse {{ 0%, 60%, 100% {{ opacity: 0.3; transform: scale(0.8); }} 30% {{ opacity: 1; transform: scale(1.2); }} }}

.big-title {{ font-family: 'Inter', sans-serif; color: #00d4ff; text-align: center; font-size: 48px; font-weight: 1200; letter-spacing: -3px; margin-bottom: 0px; text-shadow: 0 0 12px rgba(0, 212, 255, 0.4); }}
.glass-container {{ background: rgba(35, 35, 45, 0.4); backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 28px; padding: 24px; margin-bottom: 20px; }}
.mastery-value {{ font-size: 48px; color: #00d4ff; font-weight: 800; line-height: 1; }}
</style> """, unsafe_allow_html=True)

if "SCHOOL_CODES" in st.secrets: SCHOOL_CODES = dict(st.secrets["SCHOOL_CODES"])
else: SCHOOL_CODES = {}

# ----------------------------- #
# 2) AI PROMPTS & LOGIC #
# ----------------------------- #
SYSTEM_INSTRUCTION = """ You are Helix, an elite Cambridge (CIE) Tutor and Examiner for Grade 6-8 students.  
### RULE 1: RAG SEARCH & STRICT SYLLABUS BOUNDARIES (CRITICAL)
- Search attached PDF textbooks using OCR FIRST.
- STRICT SCOPE: Restrict all questions/answers ONLY to requested chapters.
### RULE 2: VISUAL SYNTAX
- Use IMAGE_GEN:[Detailed description] or PIE_CHART:[Label1:Value1, Label2:Value2].
- NEVER ask the image generator for labels/text. Give educational labels in your TEXT.
"""

QUIZ_SYSTEM_INSTRUCTION = """ You are an AI Quiz Engine. Output a single, raw JSON array of objects. 
Each object: {"question": "...", "type": "MCQ", "options": ["A", "B", "C", "D"], "correct_answer": "...", "explanation": "..."}
"""
PAPER_SYSTEM = SYSTEM_INSTRUCTION + "\n\nAppend [PDF_READY] at end."

# ----------------------------- #
# 3) AUTH & DATABASE (Firestore) #
# ----------------------------- #
is_authenticated = False
if hasattr(st, "user") and st.user: is_authenticated = st.user.is_logged_in
elif hasattr(st, "experimental_user") and st.experimental_user: is_authenticated = st.experimental_user.is_logged_in

@st.cache_resource
def get_firestore_client():
    if "firebase" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(dict(st.secrets["firebase"]))
        return firestore.Client(credentials=creds)
    return None

db = get_firestore_client()

# --- Placeholder Functions ---
def get_user_profile(email):
    if not db: return {"role": "student", "display_name": email.split("@")[0], "grade": "Grade 6"}
    doc = db.collection("users").document(email).get()
    return doc.to_dict() if doc.exists else {"role": "student", "grade": "Grade 6"}

def save_chat_history(): pass # Standard logic omitted for brevity in full block

def generate_with_retry(model_target, contents, config, retries=2):
    try: return client.models.generate_content(model=model_target, contents=contents, config=config)
    except: return None

def safe_response_text(resp) -> str:
    try: return resp.text if hasattr(resp, "text") else ""
    except: return ""

# ----------------------------- #
# 4) CORE UI & APP ROUTING #
# ----------------------------- #
if "current_thread_id" not in st.session_state: st.session_state.current_thread_id = str(uuid.uuid4())
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "👋 Hey there! I'm Helix! What are we learning today?", "is_greeting": True}]

# Sidebar
with st.sidebar:
    st.title("Helix A.I.")
    if not is_authenticated:
        if st.button("Log in with Google"): st.login(provider="google")
    else:
        st.write(f"Logged in as student")
        if st.button("New Chat"):
            st.session_state.current_thread_id = str(uuid.uuid4())
            st.session_state.messages = [{"role": "assistant", "content": "New session started!", "is_greeting": True}]
        st.radio("Mode", ["💬 AI Tutor", "⚡ Interactive Quiz"], key="app_mode")

# Chat Interface
if st.session_state.get("app_mode", "💬 AI Tutor") == "💬 AI Tutor":
    st.markdown("<div class='big-title'>📚 helix.ai</div>", unsafe_allow_html=True)
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask Helix anything about CIE Grade 6-8..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            think = st.empty()
            think.markdown("Helix is thinking...")
            resp = generate_with_retry("gemini-2.0-flash", prompt, types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION))
            bot_text = safe_response_text(resp) or "I'm sorry, I couldn't process that."
            think.empty()
            st.markdown(bot_text)
            st.session_state.messages.append({"role": "assistant", "content": bot_text})

# Quiz Interface
else:
    st.title("⚡ Interactive CIE Quiz")
    with st.form("quiz_gen"):
        subj = st.selectbox("Subject", ["Math", "Science", "English"])
        chap = st.text_input("Topic")
        if st.form_submit_button("Generate Quiz"):
            with st.spinner("Generating..."):
                q_prompt = f"Topic: {chap}, Subject: {subj}"
                resp = generate_with_retry("gemini-2.0-flash", q_prompt, types.GenerateContentConfig(system_instruction=QUIZ_SYSTEM_INSTRUCTION))
                st.write("Quiz Loaded! (JSON Preview for Debug):")
                st.code(safe_response_text(resp))
