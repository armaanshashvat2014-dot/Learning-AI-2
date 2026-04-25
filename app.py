import streamlit as st
import itertools, re, wikipedia

# =========================
# API SETUP
# =========================
from google import genai
from openai import OpenAI

GOOGLE_KEYS = [
    st.secrets["GOOGLE_API_KEY_1"],
    st.secrets["GOOGLE_API_KEY_2"]
]

OPENAI_KEYS = [
    st.secrets["OPENAI_API_KEY_1"],
    st.secrets["OPENAI_API_KEY_2"]
]

google_cycle = itertools.cycle(GOOGLE_KEYS)
openai_cycle = itertools.cycle(OPENAI_KEYS)

def get_google():
    return genai.Client(api_key=next(google_cycle))

def get_openai():
    return OpenAI(api_key=next(openai_cycle))

# =========================
# 🧠 CONSCIOUS ENGINE
# =========================
def conscious_engine(q, history):
    q = q.lower()

    if "ice cream" in q and ("200" in q or "heat" in q):
        return "❌ No. Ice cream melts at high temperatures."

    if "breathe in space" in q:
        return "❌ No. Humans cannot breathe in space."

    if "fire cold" in q:
        return "❌ No. Fire produces heat."

    if "hot and cold" in q:
        return "❌ Something cannot be both hot and cold at the same time."

    if history:
        last = history[-1]["text"].lower()

        if "sound" in last and "how" in q:
            return "🔊 Sound travels as vibrations through a medium like air."

    return None

# =========================
# 🔎 SEARCH
# =========================
def search_answer(q):
    try:
        return "🌐 " + wikipedia.summary(q, 2)
    except:
        return None

# =========================
# 🧮 MATH ENGINE (FIXED)
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\.]+", q)
    expr = "".join(matches)
    if expr:
        return expr.replace("^", "**")
    return None

def solve_math(q):
    expr = extract_math(q)
    if not expr:
        return None
    try:
        return str(eval(expr, {"__builtins__":None}, {}))
    except:
        return None

def math_response(q):
    ans = solve_math(q)

    if ans:
        if any(w in q.lower() for w in ["explain","why","how"]):
            return f"🧮 The answer is {ans}.\n\nUsing BODMAS, powers are solved first, then addition/subtraction."
        return f"🧮 {ans}"

    return None

# =========================
# 🤖 AI ENGINE
# =========================
def ai_answer(q):

    history = st.session_state.chats[st.session_state.current_chat]

    # 1. conscious
    cs = conscious_engine(q, history)
    if cs:
        return cs

    # 2. math
    m = math_response(q)
    if m:
        return m

    # 3. search
    s = search_answer(q)
    if s:
        return s

    # 4. AI fallback
    prompt = f"Answer logically and clearly:\n{q}"

    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if r.text:
                return r.text
        except:
            pass

    for _ in range(2):
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
        except:
            pass

    return "⚠️ I'm not sure. Try again."

# =========================
# 🎨 UI STYLE
# =========================
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#0a0f1f,#020617); color:white;}
.chat-user {background:#1e293b;padding:10px;border-radius:10px;margin:5px;}
.chat-ai {background:#111827;padding:10px;border-radius:10px;border-left:4px solid #38bdf8;margin:5px;}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# =========================
# SIDEBAR
# =========================
st.sidebar.title("💬 Chats")

if st.sidebar.button("➕ New Chat"):
    name = f"Chat {len(st.session_state.chats)+1}"
    st.session_state.chats[name] = []
    st.session_state.current_chat = name

for chat in st.session_state.chats:
    if st.sidebar.button(chat):
        st.session_state.current_chat = chat

if st.sidebar.button("🗑 Delete Chat"):
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[st.session_state.current_chat]
        st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# =========================
# HEADER
# =========================
st.title("🧠 SmartLoop AI")

st.info("""
👋 Hey there! I'm SmartLoop AI! 

I'm your CIE tutor here to help you ace your exams! 📚

I can answer your doubts, draw diagrams, and create quizzes! 
Attach photos, PDFs, or text files below! 📸📄
""")

# =========================
# CHAT DISPLAY
# =========================
for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

# =========================
# INPUT
# =========================
q = st.text_input("Ask SmartLoop...")

if q:
    st.session_state.chats[st.session_state.current_chat].append({"role":"user","text":q})

    ans = ai_answer(q)

    st.session_state.chats[st.session_state.current_chat].append({"role":"ai","text":ans})

    st.rerun()
