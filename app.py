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
# SAFETY
# =========================
def is_safe(q):
    try:
        r = get_google().models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Return true or false:\n{q}"
        )
        return "true" in r.text.lower()
    except:
        return True

# =========================
# MATH
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\[\]\{\}\.]+", q)
    expr = "".join(matches)

    if not expr:
        return None

    expr = expr.replace("[", "(").replace("]", ")")
    expr = expr.replace("{", "(").replace("}", ")")

    return expr.replace("^", "**")

def solve_math_steps(q):
    expr = extract_math(q)
    if not expr:
        return None

    try:
        result = eval(expr)
        return f"🧮 Answer: {result}"
    except:
        return None

# =========================
# NEWS
# =========================
def is_news_query(q):
    return any(w in q.lower() for w in ["news","latest","headlines","update"])

def get_global_news():
    feeds = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "http://feeds.reuters.com/reuters/topNews",
        "http://rss.cnn.com/rss/edition.rss",
        "https://news.google.com/rss",
        "https://feeds.skynews.com/feeds/rss/home.xml"
    ]

    headlines = []

    for f in feeds:
        try:
            feed = feedparser.parse(f)
            for e in feed.entries[:3]:
                headlines.append(f"• {e.title}")
        except:
            pass

    return "📰 Global News:\n\n" + "\n".join(headlines[:12])

# =========================
# AI
# =========================
def ai_answer(q):

    if not is_safe(q):
        return "⚠️ Not allowed."

    if is_news_query(q):
        return get_global_news()

    math = solve_math_steps(q)
    if math:
        return math

    prompt = f"Answer clearly:\n{q}"

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
# UI
# =========================
st.markdown("""
<style>
.stApp {background: radial-gradient(circle at top, #0b1f3a, #020617); color:white;}

.title {text-align:center;margin-top:40px;}
.beta {
background: linear-gradient(135deg,#ff4d6d,#7b2ff7);
padding:5px 14px;border-radius:999px;font-size:14px;
}

.subtitle {text-align:center;opacity:0.7;}

.card {
margin-top:40px;width:55%;
background:rgba(30,40,60,0.6);
border-radius:20px;padding:25px;
border:1px solid rgba(255,255,255,0.1);
}

.input-container {
position:fixed;bottom:40px;left:25%;
width:50%;background:rgba(30,40,60,0.9);
border-radius:15px;padding:10px;
}

.chat {width:55%;margin-top:20px;}

.chat-user {background:#1e293b;padding:10px;border-radius:10px;margin:6px;}
.chat-ai {background:#111827;padding:10px;border-radius:10px;border-left:4px solid #38bdf8;margin:6px;}
</style>
""", unsafe_allow_html=True)

# HEADER
st.markdown("""
<div class="title">
<h1>SmartLoop AI <span class="beta">BETA</span></h1>
</div>
<div class="subtitle">CIE Tutor for Grade 6–8</div>
""", unsafe_allow_html=True)

# WELCOME
if len(st.session_state.chats[st.session_state.current_chat]) == 0:
    st.markdown("""
    <div class="card">
    👋 <b>Hey there! I'm SmartLoop AI!</b><br><br>
    Ask anything — math, science, or real-world news 🌍
    </div>
    """, unsafe_allow_html=True)

# CHAT
st.markdown('<div class="chat">', unsafe_allow_html=True)

for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"]=="user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# INPUT (NO ERROR VERSION)
st.markdown('<div class="input-container">', unsafe_allow_html=True)

q = st.text_input("", placeholder="Ask SmartLoop...", key="main_input")

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# LOGIC (FIXED)
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
