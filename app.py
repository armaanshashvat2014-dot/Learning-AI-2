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
    prompt = f"Return ONLY true or false.\n\nQuery:\n{q}"
    try:
        return "true" in get_google().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        ).text.lower()
    except:
        pass
    return True

# =========================
# 🧮 MATH
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\[\]\{\}\.]+", q)
    expr = "".join(matches)
    if not expr:
        return None

    expr = expr.replace("[", "(").replace("]", ")")
    expr = expr.replace("{", "(").replace("}", ")")

    return expr.replace("^","**")

def solve_math_steps(q):
    expr = extract_math(q)
    if not expr:
        return None

    try:
        original = expr.replace("**","^")
        working = expr
        steps = [f"Expression: {original}"]

        # brackets
        for part in re.findall(r"\([^()]+\)", working):
            val = eval(part)
            steps.append(f"{part} → {val}")
            working = working.replace(part, str(val), 1)

        # powers
        for p in re.findall(r"\d+\*\*\d+", working):
            val = eval(p)
            steps.append(f"{p.replace('**','^')} = {val}")
            working = working.replace(p, str(val), 1)

        result = eval(working)
        steps.append(f"Final Answer: {result}")

        return "\n".join(steps)
    except:
        return None

# =========================
# 📰 NEWS
# =========================
def is_news_query(q):
    return any(w in q.lower() for w in ["news","latest","headlines"])

def get_global_news():
    feeds = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "http://feeds.reuters.com/reuters/topNews",
        "http://rss.cnn.com/rss/edition.rss",
        "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
    ]
    headlines = []
    for f in feeds:
        try:
            feed = feedparser.parse(f)
            for e in feed.entries[:3]:
                headlines.append(f"• {e.title}")
        except:
            pass
    return "📰 Latest News:\n\n" + "\n".join(headlines[:8])

# =========================
# 😄 / 😐 PERSONALITY
# =========================
def get_personality(q, unsafe=False):

    ql = q.lower()

    if unsafe:
        return "strict"

    if any(w in ql for w in ["wrong","fake","stupid"]):
        return "strict"

    return "happy"

# =========================
# 🤖 AI
# =========================
def ai_answer(q):

    unsafe = not is_safe(q)
    personality = get_personality(q, unsafe)

    if unsafe:
        return "⚠️ I won’t help with that."

    if is_news_query(q):
        return get_global_news()

    math = solve_math_steps(q)
    if math:
        if personality == "happy":
            return "😄 Let’s solve this!\n\n" + math
        else:
            return "Focus.\n\n" + math

    style = "friendly and enthusiastic" if personality=="happy" else "strict and direct"

    prompt = f"""
Answer clearly. Be {style}.

Question:
{q}
"""

    try:
        return get_google().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        ).text
    except:
        pass

    try:
        return get_openai().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        ).choices[0].message.content
    except:
        pass

    return "Not sure."

# =========================
# 🎨 HELIX-STYLE UI (EXACT)
# =========================
st.markdown("""
<style>

/* Background */
.stApp {
    background: radial-gradient(circle at top, #0b1f3a, #020617);
    color: white;
}

/* Center everything */
.main {
    display: flex;
    flex-direction: column;
    align-items: center;
}

/* Title */
.title {
    text-align: center;
    margin-top: 40px;
}

.title h1 {
    font-size: 42px;
    font-weight: 700;
}

/* Beta badge */
.beta {
    background: linear-gradient(135deg, #ff4d6d, #7b2ff7);
    padding: 5px 14px;
    border-radius: 999px;
    font-size: 14px;
    margin-left: 10px;
}

/* Subtitle */
.subtitle {
    text-align: center;
    opacity: 0.7;
    margin-top: 5px;
}

/* Card */
.card {
    margin-top: 40px;
    width: 55%;
    background: rgba(30, 40, 60, 0.6);
    border-radius: 20px;
    padding: 25px;
    border: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
}

/* Input bar */
.input-container {
    position: fixed;
    bottom: 40px;
    left: 25%;
    width: 50%;
    background: rgba(30,40,60,0.9);
    border-radius: 15px;
    padding: 10px;
    border: 1px solid rgba(255,255,255,0.1);
}

/* Chat messages */
.chat {
    width: 55%;
    margin-top: 20px;
}

.chat-user {
    background:#1e293b;
    padding:10px;
    border-radius:10px;
    margin:6px;
}

.chat-ai {
    background:#111827;
    padding:10px;
    border-radius:10px;
    border-left:4px solid #38bdf8;
    margin:6px;
}

</style>
""", unsafe_allow_html=True)

# =========================
# 🧠 HEADER
# =========================
st.markdown("""
<div class="title">
    <h1> SmartLoop AI <span class="beta">BETA</span></h1>
</div>
<div class="subtitle">
    CIE Tutor for Grade 6-8.
</div>
""", unsafe_allow_html=True)

# =========================
# 💬 WELCOME CARD
# =========================
if len(st.session_state.chats[st.session_state.current_chat]) == 0:
    st.markdown("""
    <div class="card">
        <b>👋 Hey there! I'm SmartLoop AI!</b><br><br>
        I'm your CIE tutor here to help you ace your exams! 📚<br><br>
        I can answer your doubts, solve math, and explain concepts clearly.<br>
        Ask anything below!
    </div>
    """, unsafe_allow_html=True)

# =========================
# 💬 CHAT DISPLAY
# =========================
st.markdown('<div class="chat">', unsafe_allow_html=True)

for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ⌨️ INPUT (FLOATING LIKE IMAGE)
# =========================
st.markdown('<div class="input-container">', unsafe_allow_html=True)

q = st.text_input("", placeholder="Ask Helix...", key="input")

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ⚡ LOGIC (NO DARKENING)
# =========================
if q and q != st.session_state.last_q:

    st.session_state.last_q = q

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"user","text":q
    })

    ans = ai_answer(q)

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"ai","text":ans
    })

    st.rerun()

# =========================
# HEADER
# =========================
st.markdown("""
<h2>🧠 SmartLoop AI <span style="color:#ff4d6d;">BETA</span></h2>
""", unsafe_allow_html=True)

# =========================
# CHAT DISPLAY
# =========================
for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"]=="user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

# =========================
# INPUT (FIXED)
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
        "role":"user","text":q
    })

    thinking = st.empty()
    thinking.markdown("🤖 Thinking...")

    ans = ai_answer(q)

    thinking.empty()

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"ai","text":ans
    })

    st.rerun()
