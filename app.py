import streamlit as st
import itertools, re, wikipedia, random
from PyPDF2 import PdfReader

# =========================
# API SETUP
# =========================
from google import genai
from openai import OpenAI

GOOGLE_KEYS = [st.secrets["GOOGLE_API_KEY_1"], st.secrets["GOOGLE_API_KEY_2"]]
OPENAI_KEYS = [st.secrets["OPENAI_API_KEY_1"], st.secrets["OPENAI_API_KEY_2"]]

google_cycle = itertools.cycle(GOOGLE_KEYS)
openai_cycle = itertools.cycle(OPENAI_KEYS)

def get_google():
    return genai.Client(api_key=next(google_cycle))

def get_openai():
    return OpenAI(api_key=next(openai_cycle))

# =========================
# SESSION
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

if "pdf_chunks" not in st.session_state:
    st.session_state.pdf_chunks = []

if "last_q" not in st.session_state:
    st.session_state.last_q = ""

# =========================
# 🧠 CONSCIOUS
# =========================
def conscious_engine(q):
    q = q.lower()

    if "ice cream" in q and ("200" in q or "heat" in q):
        return "❌ Ice cream melts at high temperatures."

    if "fire cold" in q:
        return "❌ Fire produces heat."

    if "breathe in space" in q:
        return "❌ Humans cannot breathe in space."

    if "hot and cold" in q:
        return "❌ Cannot be both hot and cold."

    return None

# =========================
# 🧮 MATH
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

# =========================
# 📄 PDF SEARCH
# =========================
def search_pdf(q):
    q = q.lower()
    best = ""
    best_score = 0

    for chunk in st.session_state.pdf_chunks:
        score = sum(1 for w in q.split() if w in chunk)

        if score > best_score:
            best_score = score
            best = chunk

    if best_score > 0:
        return best[:500]

    return None

# =========================
# 🔎 WIKI
# =========================
def search_wiki(q):
    try:
        return wikipedia.summary(q, 2)
    except:
        return None

# =========================
# 🤖 AI
# =========================
def ai_answer(q):

    # 1 conscious
    cs = conscious_engine(q)
    if cs:
        return cs

    # 2 math
    m = solve_math(q)
    if m:
        return f"🧮 {m}"

    # 3 summarise PDF
    if "summarise" in q.lower() or "summarize" in q.lower():
        if st.session_state.pdf_chunks:
            text = " ".join(st.session_state.pdf_chunks[:30])
            return "📄 Summary:\n\n" + text[:1000]
        return "❌ No PDF uploaded."

    # 4 PDF search
    pdf = search_pdf(q)
    if pdf:
        return "📖 From your PDF:\n\n" + pdf

    # 5 wiki
    wiki = search_wiki(q)
    if wiki:
        return "🌐 " + wiki

    # 6 AI fallback
    prompt = f"Answer clearly:\n{q}"

    try:
        c = get_google()
        r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        if r.text:
            return r.text
    except:
        pass

    try:
        c = get_openai()
        r = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )
        return r.choices[0].message.content
    except:
        pass

    return "⚠️ AI busy"

# =========================
# GENERATORS
# =========================
def gen_math():
    qs=[]
    for _ in range(5):
        a,b,c=random.randint(1,10),random.randint(1,10),random.randint(2,3)
        qs.append(f"{a} + {b}^{c}")
    return qs

def gen_science(topic):
    return [
        f"What is {topic}?",
        f"Why is {topic} important?",
        f"How does {topic} work?"
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
    name=f"Chat {len(st.session_state.chats)+1}"
    st.session_state.chats[name]=[]
    st.session_state.current_chat=name

for chat in st.session_state.chats:
    if st.sidebar.button(chat):
        st.session_state.current_chat=chat

if st.sidebar.button("🗑 Delete Chat"):
    if len(st.session_state.chats)>1:
        del st.session_state.chats[st.session_state.current_chat]
        st.session_state.current_chat=list(st.session_state.chats.keys())[0]

st.sidebar.markdown("---")

# PDF upload
st.sidebar.markdown("### ➕ Add PDF")
pdf_file = st.sidebar.file_uploader("", type=["pdf"])

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

mode = st.sidebar.selectbox("Mode", ["Tutor Mode","Teacher Mode","Quiz Mode","Test Mode"])

# =========================
# HEADER
# =========================
st.title("🧠 SmartLoop AI")

st.info("👋 Hey there! I'm SmartLoop AI! Your CIE tutor 📚")

# =========================
# CHAT DISPLAY
# =========================
for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"]=="user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

# =========================
# INPUT (ENTER FIX)
# =========================
q = st.text_input("Ask SmartLoop...", key="input")

if q and q != st.session_state.last_q:

    st.session_state.last_q = q

    st.session_state.chats[st.session_state.current_chat].append({"role":"user","text":q})

    with st.spinner("Thinking..."):

        if mode=="Tutor Mode":
            ans = ai_answer(q)

        elif mode=="Teacher Mode":
            ans = ai_answer(q) + "\n\n📝 Practice: Try similar questions."

        elif mode=="Quiz Mode":
            ans = "\n".join(gen_math())

        elif mode=="Test Mode":
            ans = "\n".join([f"Q{i+1}. {x}" for i,x in enumerate(gen_math())])

    st.session_state.chats[st.session_state.current_chat].append({"role":"ai","text":ans})

    st.rerun()
