import streamlit as st
import itertools, re, wikipedia, feedparser

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
# SESSION
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

if "last_q" not in st.session_state:
    st.session_state.last_q = ""

# =========================
# 🧠 SAFETY
# =========================
def is_safe(q):
    prompt = f"Return ONLY true or false:\n{q}"

    try:
        r = get_google().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return "true" in r.text.lower()
    except:
        return True

# =========================
# 🧮 SAFE MATH
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\[\]\{\}\.]+", q)
    expr = "".join(matches)

    if not expr:
        return None

    expr = expr.replace("[", "(").replace("]", ")")
    expr = expr.replace("{", "(").replace("}", ")")

    return expr.replace("^", "**")


def safe_eval(expr):
    try:
        return eval(expr, {"__builtins__": None}, {})
    except:
        return None


def solve_math_steps(q):
    expr = extract_math(q)
    if not expr:
        return None

    try:
        original = expr.replace("**", "^")
        result = safe_eval(expr)

        if result is None:
            return None

        return f"🧮 Expression: {original}\n\nFinal Answer: {result}"

    except:
        return None

# =========================
# 📰 NEWS
# =========================
def is_news_query(q):
    return "news" in q.lower()

def get_global_news():
    feeds = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "https://news.google.com/rss"
    ]

    headlines = []

    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                headlines.append(f"• {entry.title}")
        except:
            continue

    return "📰 Latest News:\n\n" + "\n".join(headlines[:10])

# =========================
# 🔎 WIKI (CONTROLLED)
# =========================
def search_wiki(q):
    try:
        if len(q.split()) > 2:
            return wikipedia.summary(q, 2)
    except:
        return None
    return None

# =========================
# 🤖 AI
# =========================
def ai_answer(q):

    if not is_safe(q):
        return "⚠️ I can’t help with that."

    if is_news_query(q):
        return get_global_news()

    math = solve_math_steps(q)
    if math:
        return math

    prompt = f"""
You are SmartLoop AI.
Be logical, clear, correct.

Question:
{q}
"""

    try:
        r = get_google().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        if r.text:
            return r.text
    except:
        pass

    try:
        r = get_openai().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":q}]
        )
        return r.choices[0].message.content
    except:
        pass

    wiki = search_wiki(q)
    if wiki:
        return "🌐 " + wiki

    return "⚠️ Not sure."

# =========================
# 🎨 UI STYLE
# =========================
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #0b1f3a, #020617);
    color: white;
}

.header {
    text-align: center;
    margin-top: 30px;
}

.beta {
    background: linear-gradient(135deg,#ff4d6d,#7b2ff7);
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 13px;
    margin-left: 8px;
}

.chat-container {
    width: 60%;
    margin: auto;
    margin-top: 20px;
    padding-bottom: 120px;
}

.chat-user {
    background:#1e293b;
    padding:12px;
    border-radius:12px;
    margin:8px 0;
}

.chat-ai {
    background:#111827;
    padding:12px;
    border-radius:12px;
    border-left:4px solid #38bdf8;
    margin:8px 0;
}

.input-box {
    position: fixed;
    bottom: 20px;
    left: 20%;
    width: 60%;
    background: rgba(30,40,60,0.95);
    padding: 12px;
    border-radius: 14px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.markdown("""
<div class="header">
    <h1>🧠 SmartLoop AI <span class="beta">BETA</span></h1>
    <p style="opacity:0.7;">Learn smarter. Solve faster.</p>
</div>
""", unsafe_allow_html=True)

# =========================
# CHAT DISPLAY (FIXED)
# =========================
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.chats[st.session_state.current_chat]:
    text = msg.get("text") or msg.get("content") or ""

    if msg.get("role") == "user":
        st.markdown(f"<div class='chat-user'>🧑 {text}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {text}</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# INPUT
# =========================
st.markdown('<div class="input-box">', unsafe_allow_html=True)

q = st.text_input("", placeholder="Ask SmartLoop...", key="input")

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# LOGIC
# =========================
if q and q != st.session_state.last_q:

    st.session_state.last_q = q

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"user",
        "text":q
    })

    with st.spinner("Thinking..."):
        ans = ai_answer(q)

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"ai",
        "text":ans
    })

    st.rerun()
