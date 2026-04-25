import streamlit as st
import itertools, re, wikipedia, random
from PyPDF2 import PdfReader

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
# SESSION STATE
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

if "pdf_chunks" not in st.session_state:
    st.session_state.pdf_chunks = []

# =========================
# 🧠 CONSCIOUS ENGINE
# =========================
def conscious_engine(q, history):
    ql = q.lower()

    if "ice cream" in ql and ("200" in ql or "heat" in ql):
        return "❌ Ice cream melts at high temperatures."

    if "fire cold" in ql:
        return "❌ Fire produces heat."

    if "breathe in space" in ql:
        return "❌ Humans cannot breathe in space."

    if "hot and cold" in ql:
        return "❌ Cannot be both hot and cold."

    if history:
        last = history[-1]["text"].lower()
        if "sound" in last and "how" in ql:
            return "🔊 Sound travels as vibrations through a medium."

    return None

# =========================
# 🧮 MATH ENGINE
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\.]+", q)
    expr = "".join(matches)
    return expr.replace("^","**") if expr else None

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
        return f"🧮 Answer: {ans}"
    return None

# =========================
# 📄 PDF SEARCH
# =========================
def search_pdf(q):
    q = q.lower()
    results = []

    for chunk in st.session_state.pdf_chunks:
        score = sum(1 for w in q.split() if w in chunk)
        if score > 0:
            results.append((score, chunk))

    results.sort(reverse=True)

    if results:
        return "📖 " + results[0][1][:300]

    return None

# =========================
# 🔎 SEARCH
# =========================
def search_wiki(q):
    try:
        return "🌐 " + wikipedia.summary(q, 2)
    except:
        return None

# =========================
# 🤖 AI ANSWER
# =========================
def ai_answer(q):
    history = st.session_state.chats[st.session_state.current_chat]

    # 1 conscious
    cs = conscious_engine(q, history)
    if cs:
        return cs

    # 2 math
    m = math_response(q)
    if m:
        return m

    # 3 PDF
    pdf = search_pdf(q)
    if pdf:
        return pdf

    # 4 wiki
    wiki = search_wiki(q)
    if wiki:
        return wiki

    # 5 AI fallback
    prompt = f"Answer clearly: {q}"

    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
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

    return "⚠️ AI busy."

# =========================
# QUESTION GENERATORS
# =========================
def gen_math(topic, mode):
    qs=[]
    for _ in range(5):
        a,b,c = random.randint(1,10),random.randint(1,10),random.randint(2,3)
        qs.append(f"{a} + {b}^{c}")
    return qs

def gen_science(topic):
    return [
        f"What is {topic}?",
        f"Why is {topic} important?",
        f"How does {topic} work?",
        f"Who discovered {topic}?"
    ]

def gen_english(topic):
    return [
        f"What is {topic}?",
        f"How do you use {topic}?",
        f"Why is {topic} important?"
    ]

# =========================
# UI STYLE
# =========================
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#0a0f1f,#020617); color:white;}
.chat-user {background:#1e293b;padding:10px;border-radius:10px;margin:6px;}
.chat-ai {background:#111827;padding:10px;border-radius:10px;border-left:4px solid #38bdf8;margin:6px;}
</style>
""", unsafe_allow_html=True)

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
    if len(st.session_state.chats)>1:
        del st.session_state.chats[st.session_state.current_chat]
        st.session_state.current_chat=list(st.session_state.chats.keys())[0]

st.sidebar.markdown("---")

# PDF upload
st.sidebar.markdown("### ➕ Add PDF")
pdf_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

if pdf_file:
    reader = PdfReader(pdf_file)
    text = ""

    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t

    chunks = text.split(". ")

    for c in chunks:
        if len(c) > 50:
            st.session_state.pdf_chunks.append(c.lower())

    st.sidebar.success("✅ PDF Loaded")

# Mode
mode = st.sidebar.selectbox("Mode", ["Tutor Mode","Teacher Mode","Quiz Mode","Test Mode"])

# =========================
# HEADER
# =========================
st.title("🧠 SmartLoop AI")

st.info("""
👋 Hey there! I'm SmartLoop AI! 

I'm your CIE tutor here to help you ace your exams! 📚
""")

# =========================
# CHAT DISPLAY
# =========================
for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"]=="user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

# =========================
# INPUT
# =========================
q = st.text_input("Ask SmartLoop...")

if q:
    st.session_state.chats[st.session_state.current_chat].append({"role":"user","text":q})

    with st.spinner("Thinking..."):

        if mode=="Tutor Mode":
            ans = ai_answer(q)

        elif mode=="Teacher Mode":
            ans = ai_answer(q)
            ans += "\n\n📝 Practice:\n- Try similar questions."

        elif mode=="Quiz Mode":
            ans = "\n".join(gen_math(q,mode))

        elif mode=="Test Mode":
            ans = "\n".join([f"Q{i+1}. {x}" for i,x in enumerate(gen_math(q,mode))])

    st.session_state.chats[st.session_state.current_chat].append({"role":"ai","text":ans})
    st.rerun()
