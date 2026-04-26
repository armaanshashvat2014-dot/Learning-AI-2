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
    prompt = f"""
Return ONLY one word:
true = safe
false = unsafe

Query:
{q}
"""
    try:
        c = get_google()
        r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return "true" in r.text.lower()
    except:
        pass

    try:
        c = get_openai()
        r = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )
        return "true" in r.choices[0].message.content.lower()
    except:
        pass

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
        original = expr.replace("**", "^")
        steps = [f"Expression: {original}"]
        working = expr

        if "(" in working:
            inner = re.findall(r"\([^()]+\)", working)
            for part in inner:
                val = eval(part, {"__builtins__":None}, {})
                steps.append(f"{part} → {val}")
                working = working.replace(part, str(val), 1)

        if "**" in working:
            powers = re.findall(r"\d+\*\*\d+", working)
            for p in powers:
                val = eval(p, {"__builtins__":None}, {})
                steps.append(f"{p.replace('**','^')} = {val}")
                working = working.replace(p, str(val), 1)

        md = re.findall(r"\d+[\*/]\d+", working)
        for m in md:
            val = eval(m, {"__builtins__":None}, {})
            steps.append(f"{m} = {val}")
            working = working.replace(m, str(val), 1)

        result = eval(working, {"__builtins__":None}, {})
        steps.append(f"Final Answer: {result}")

        return "🧮 Step-by-step:\n\n" + "\n".join(steps)

    except:
        return None

# =========================
# NEWS
# =========================
def is_news_query(q):
    return any(word in q.lower() for word in ["news","latest","headlines"])

def get_global_news():
    feeds = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "http://feeds.reuters.com/reuters/topNews",
        "http://rss.cnn.com/rss/edition.rss",
        "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
    ]

    headlines = []

    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                headlines.append(f"• {entry.title}")
        except:
            pass

    return "📰 Latest News:\n\n" + "\n".join(headlines[:10])

# =========================
# AI
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
        return get_google().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        ).text
    except:
        pass

    try:
        r = get_openai().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )
        return r.choices[0].message.content
    except:
        pass

    return "⚠️ Not sure."

# =========================
# UI STYLE
# =========================
st.markdown("""
<style>

.stApp {
    background: radial-gradient(circle at top, #0a1a2f, #020617);
    color:white;
}

/* Header */
.header {
    text-align:center;
    margin-top:40px;
}

/* Card */
.center-card {
    margin:40px auto;
    width:60%;
    background:rgba(20,30,50,0.6);
    padding:25px;
    border-radius:20px;
    border:1px solid rgba(255,255,255,0.1);
    text-align:center;
}

/* Chat */
.chat-container {
    max-height:60vh;
    overflow-y:auto;
    padding-bottom:100px;
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

/* Fixed input */
.fixed-input {
    position:fixed;
    bottom:20px;
    left:20%;
    width:60%;
    background:rgba(30,40,60,0.95);
    padding:10px;
    border-radius:15px;
}

/* Thinking dots */
.thinking {
    text-align:center;
    margin:20px;
}

.dot {
    display:inline-block;
    width:8px;
    height:8px;
    margin:3px;
    border-radius:50%;
    background:#38bdf8;
    animation:bounce 1.4s infinite;
}

.dot:nth-child(2){animation-delay:0.2s;}
.dot:nth-child(3){animation-delay:0.4s;}

@keyframes bounce {
    0%,80%,100%{transform:scale(0.5);}
    40%{transform:scale(1.4);}
}

</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.markdown("""
<div class="header">
<h1>🧠 SmartLoop AI 
<span style="background:linear-gradient(135deg,#ff4d6d,#7b2ff7);
padding:5px 12px;border-radius:999px;font-size:14px;">BETA</span>
</h1>
<p style="opacity:0.7;">CIE Tutor for Grade 6–8</p>
</div>
""", unsafe_allow_html=True)

# =========================
# WELCOME CARD
# =========================
if len(st.session_state.chats[st.session_state.current_chat]) == 0:
    st.markdown("""
    <div class="center-card">
    👋 <b>Hey there! I'm SmartLoop AI!</b><br><br>
    Ask anything—math, science, or real-world questions 🌍
    </div>
    """, unsafe_allow_html=True)

# =========================
# CHAT DISPLAY
# =========================
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# INPUT
# =========================
st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
q = st.text_input("", placeholder="Ask SmartLoop...", key="input")
st.markdown('</div>', unsafe_allow_html=True)

if q and q != st.session_state.last_q:
    st.session_state.last_q = q
    st.session_state.chats[st.session_state.current_chat].append({"role":"user","text":q})

    st.markdown("""
    <div class="thinking">
    Thinking 
    <span class="dot"></span>
    <span class="dot"></span>
    <span class="dot"></span>
    </div>
    """, unsafe_allow_html=True)

    ans = ai_answer(q)

    st.session_state.chats[st.session_state.current_chat].append({"role":"ai","text":ans})
    st.rerun()
