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

# ----------------------------- #
# 1) CONFIG & API KEY #
# ----------------------------- #
st.set_page_config(page_title="helix.ai - Cambridge (CIE) Tutor", page_icon="📚", layout="wide")

# API KEY INTEGRATION
PROVIDED_API_KEY = "AIzaSyCJ5kTedYLBjbTsCt9p7NBsbE-jsfH7sxM"
api_key = PROVIDED_API_KEY # Forced for immediate use

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"🚨 API Key Error: {e}")
    st.stop()

# ----------------------------- #
# 2) STYLING (Glassmorphism) #
# ----------------------------- #
st.markdown("""
<style>
    .stApp { background: radial-gradient(800px circle at 50% 0%, rgba(0, 212, 255, 0.12), rgba(0, 212, 255, 0.00) 60%), #0a0a1a !important; color: #f5f5f7 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { background: rgba(255, 255, 255, 0.04) !important; backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 20px; }
    .big-title { color: #00d4ff; text-align: center; font-size: 40px; font-weight: 800; text-shadow: 0 0 10px rgba(0, 212, 255, 0.4); }
    .stButton>button { width: 100%; border-radius: 12px; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); transition: 0.3s; }
    .stButton>button:hover { background: #00d4ff; color: black; border-color: #00d4ff; }
</style>
""", unsafe_allow_html=True)

# ----------------------------- #
# 3) SESSION STATE & HELPERS #
# ----------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "👋 I'm Helix! I'm ready to help you with Math, Science, or English. What's on your mind?"}]
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False

def get_ai_response(prompt, system_instruction):
    try:
        # Using gemini-1.5-flash for maximum stability
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt, 
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ----------------------------- #
# 4) LOGIN / SIGN UP PANEL #
# ----------------------------- #
if st.session_state.user_data is None:
    st.markdown("<div class='big-title'>helix.ai</div>", unsafe_allow_html=True)
    with st.container():
        st.subheader("🚀 Join the Learning Revolution")
        col1, col2 = st.columns(2)
        name = col1.text_input("Name")
        email = col2.text_input("Email")
        grade = st.selectbox("Your Grade", ["Grade 6", "Grade 7", "Grade 8"])
        
        if st.button("Start Learning Now"):
            if name and email:
                st.session_state.user_data = {"name": name, "email": email, "grade": grade}
                st.rerun()
            else:
                st.warning("Please enter your name and email.")
    st.stop()

# ----------------------------- #
# 5) SIDEBAR NAVIGATION #
# ----------------------------- #
with st.sidebar:
    st.markdown(f"### 🎓 Welcome, {st.session_state.user_data['name']}!")
    st.write(f"Grade: {st.session_state.user_data['grade']}")
    st.divider()
    app_mode = st.radio("Switch Mode", ["💬 AI Tutor", "⚡ Interactive Quiz"])
    if st.button("Clear History"):
        st.session_state.messages = [{"role": "assistant", "content": "Memory cleared! How can I help?"}]
        st.rerun()
    if st.button("Logout"):
        st.session_state.user_data = None
        st.rerun()

# ----------------------------- #
# 6) AI TUTOR MODE #
# ----------------------------- #
if app_mode == "💬 AI Tutor":
    st.markdown("<div class='big-title'>📚 helix.ai Tutor</div>", unsafe_allow_html=True)
    
    # Display Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if chat_input := st.chat_input("Ask a question (e.g., 'Explain photosynthesis' or 'Solve 2x + 5 = 15')"):
        st.session_state.messages.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)
            
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                sys_inst = "You are Helix, an elite CIE tutor. Use Clear formatting, Markdown tables, and step-by-step logic."
                response = get_ai_response(chat_input, sys_inst)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# ----------------------------- #
# 7) QUIZ ENGINE MODE #
# ----------------------------- #
else:
    st.markdown("<div class='big-title'>⚡ Interactive Quiz</div>", unsafe_allow_html=True)
    
    if not st.session_state.quiz_active:
        with st.form("quiz_config"):
            st.write("Configure your practice test:")
            c1, c2 = st.columns(2)
            q_subject = c1.selectbox("Subject", ["Math", "Science", "English"])
            q_num = c2.slider("Number of Questions", 3, 10, 5)
            q_topic = st.text_input("Specific Topic (e.g. Fractions, Electricity, Grammar)")
            
            if st.form_submit_button("Generate Quiz Now"):
                with st.spinner("Helix is crafting your unique questions..."):
                    quiz_sys = "You are a quiz engine. Output a JSON array of objects. Format: [{'question':'', 'options':['A','B','C','D'], 'correct_answer':'A', 'explanation':''}]"
                    quiz_prompt = f"Create a {q_num} question {q_subject} quiz on {q_topic} for {st.session_state.user_data['grade']} students. Return ONLY raw JSON."
                    
                    raw_json = get_ai_response(quiz_prompt, quiz_sys)
                    # Clean the JSON if the AI adds markdown blocks
                    clean_json = re.sub(r'```json\n?|\n?```', '', raw_json).strip()
                    
                    try:
                        st.session_state.quiz_questions = json.loads(clean_json)
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_active = True
                        st.session_state.current_q_idx = 0
                        st.rerun()
                    except:
                        st.error("Failed to generate quiz. Often happens if the AI is busy. Please try again.")

    else:
        # Display Current Question
        idx = st.session_state.current_q_idx
        questions = st.session_state.quiz_questions
        
        if idx < len(questions):
            q_data = questions[idx]
            st.subheader(f"Question {idx + 1} of {len(questions)}")
            st.write(q_data['question'])
            
            # Use buttons for options
            for option in q_data['options']:
                if st.button(option, key=f"opt_{idx}_{option}"):
                    if option == q_data['correct_answer']:
                        st.success(f"Correct! 🎉 {q_data.get('explanation', '')}")
                        st.session_state.quiz_score += 1
                        time.sleep(2)
                    else:
                        st.error(f"Wrong! The correct answer was: {q_data['correct_answer']}. {q_data.get('explanation', '')}")
                        time.sleep(3)
                    
                    st.session_state.current_q_idx += 1
                    st.rerun()
        else:
            st.balloons()
            st.markdown(f"### 🏁 Quiz Complete!")
            st.markdown(f"## Your Score: {st.session_state.quiz_score} / {len(questions)}")
            if st.button("Start New Quiz"):
                st.session_state.quiz_active = False
                st.rerun()
