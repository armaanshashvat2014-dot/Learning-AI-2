import streamlit as st
import itertools, re, wikipedia, feedparser
from google import genai
from openai import OpenAI

# =========================
# 🔑 API SETUP
# =========================
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
# 💾 SESSION
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

if "last_q" not in st.session_state:
    st.session_state.last_q = ""

# =========================
# 🛡️ SAFETY (AI JSON)
# =========================
def is_safe(q):
    prompt = f"""
Classify the user query.

Respond ONLY:
{{"safe": true}} OR {{"safe": false}}

Query:
{q}
"""

    try:
        c = get_google()
        r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = (r.text or "").lower()
        if '"safe": false' in text:
            return False
        if '"safe": true' in text:
            return True
    except:
        pass

    try:
        c = get_openai()
        r = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0
        )
        text = r.choices[0].message.content.lower()
        if '"safe": false' in text:
            return False
        if '"safe": true' in text:
            return True
    except:
        pass

    return True

# =========================
# 🧠 INTENT DETECTION
# =========================
def detect_intent(q):
    ql = q.lower()

    if any(w in ql for w in ["news", "latest", "headlines", "current events"]):
        return "news"

    if any(w in ql for w in ["quiz", "test", "mcq"]):
        return "quiz"

    if any(w in ql for w in ["solve", "calculate"]):
        return "math"

    if any(w in ql for w in ["explain", "what is", "define"]):
        return "explain"

    return "general"

# =========================
# 🧠 TOPIC EXTRACTION
# =========================
def extract_topic(q):
    q = q.lower()
    for phrase in ["make a quiz on", "quiz on", "create a quiz on"]:
        q = q.replace(phrase, "")
    return q.strip().capitalize()

# =========================
# 🧮 MATH (UPGRADED)
# =========================
def normalize_expression(expr):
    # Convert [] and {} to ()
    expr = expr.replace("[", "(").replace("]", ")")
    expr = expr.replace("{", "(").replace("}", ")")

    # Remove spaces
    expr = expr.replace(" ", "")

    # Implicit multiplication
    expr = re.sub(r"(\d)(\()", r"\1*\2", expr)   # 2(3+4)
    expr = re.sub(r"(\))(\()", r"\1*\2", expr)   # (2+3)(4+5)
    expr = re.sub(r"(\))(\d)", r"\1*\2", expr)   # (2+3)4

    return expr

def extract_math(q):
    pattern = r"[0-9\+\-\*/\^\(\)\[\]\{\}\.\s]+"
    matches = re.findall(pattern, q)

    if not matches:
        return None

    expr = "".join(matches).strip()

    if not any(c.isdigit() for c in expr):
        return None

    expr = expr.replace("^", "**")
    expr = normalize_expression(expr)

    return expr

def solve_math(q):
    expr = extract_math(q)
    if not expr:
        return None

    try:
        result = eval(expr, {"__builtins__": None}, {})
        return f"🧮 {expr} = {result}"
    except:
        return None

# =========================
# 🧠 QUIZ GENERATOR
# =========================
def generate_quiz(q):
    topic = extract_topic(q)

    prompt = f"""
Create a 5-question MCQ quiz on: {topic}

Format:
Q1.
A)
B)
C)
D)
Answer:

Keep it simple.
"""

    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        if r.text and len(r.text.strip()) > 20:
            return f"🧠 Quiz on {topic}:\n\n" + r.text
    except:
        pass

    try:
        c = get_openai()
        r = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7
        )
        text = r.choices[0].message.content
        if text and len(text.strip()) > 20:
            return f"🧠 Quiz on {topic}:\n\n" + text
    except:
        pass

    return f"""🧠 Quiz on {topic}:

Q1. What is 1/2 + 1/2?
A) 1
B) 2
C) 1/2
D) 0
Answer: A
"""

# =========================
# 📰 NEWS
# =========================
def get_news():
    url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    headlines = [f"• {e.title}" for e in feed.entries[:5]]
    return "📰 Latest News:\n\n" + "\n".join(headlines)

# =========================
# 🌐 WIKI
# =========================
def search_wiki(q):
    try:
        return wikipedia.summary(q, sentences=2)
    except wikipedia.exceptions.DisambiguationError as e:
        return wikipedia.summary(e.options[0], sentences=2)
    except:
        return None

# =========================
# 🤖 AI CORE
# =========================
def ai_answer(q):

    if not is_safe(q):
        return "⚠️ I can’t help with that."

    intent = detect_intent(q)

    if intent == "news":
        return get_news()

    if intent == "quiz":
        return generate_quiz(q)

    if intent == "math":
        math = solve_math(q)
        if math:
            return math

    history = st.session_state.chats[st.session_state.current_chat][-6:]
    context = "\n".join([f"{m['role']}: {m['text']}" for m in history])

    prompt = f"""
You are SmartLoop AI.
Be clear, concise and correct.

Conversation:
{context}

User: {q}
"""

    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        if r.text and len(r.text.strip()) > 5:
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

    wiki = search_wiki(q)
    if wiki:
        return "🌐 " + wiki

    return "⚠️ I couldn't find a good answer."

# =========================
# 🎨 UI
# =========================
st.markdown("""
<style>
.stApp {background: #020617; color:white;}
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
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[st.session_state.current_chat]
        st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# =========================
# TITLE
# =========================
st.title("🧠 SmartLoop AI")
st.info("Now supports (), [], {} in math + quiz + news 🚀")

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
q = st.text_input("Ask something...")

if q and q != st.session_state.last_q:
    st.session_state.last_q = q

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"user","text":q
    })

    with st.spinner("Thinking..."):
        ans = ai_answer(q)

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"ai","text":ans
    })

    st.rerun()
