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
# 🧮 MATH
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

        steps = []
        steps.append(f"Expression: {original}")

        working = expr

        # brackets
        if "(" in working:
            inner = re.findall(r"\([^()]+\)", working)
            for part in inner:
                val = eval(part, {"__builtins__":None}, {})
                steps.append(f"Solve {part} → {val}")
                working = working.replace(part, str(val), 1)

        # powers
        if "**" in working:
            powers = re.findall(r"\d+\*\*\d+", working)
            for p in powers:
                val = eval(p, {"__builtins__":None}, {})
                steps.append(f"{p.replace('**','^')} = {val}")
                working = working.replace(p, str(val), 1)

        # multiply/divide
        md = re.findall(r"\d+[\*/]\d+", working)
        for m in md:
            val = eval(m, {"__builtins__":None}, {})
            steps.append(f"{m} = {val}")
            working = working.replace(m, str(val), 1)

        # final
        result = eval(working, {"__builtins__":None}, {})
        steps.append(f"Final Answer: {result}")

        return "🧮 Step-by-step:\n\n" + "\n".join(steps)

    except:
        return None

# =========================
# 📰 NEWS
# =========================
def is_news_query(q):
    ql = q.lower()
    return any(word in ql for word in ["news","latest","headlines","current events"])

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
            continue

    return "📰 Latest Global News:\n\n" + "\n".join(headlines[:10])

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
No random outputs.

Question:
{q}
"""

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

    wiki = search_wiki(q)
    if wiki:
        return "🌐 " + wiki

    return "⚠️ Not sure. Please repeat/rephrase."
    # =========================
# UI STYLE (UPGRADED)
# =========================
st.markdown("""
<style>

/* Background */
.stApp {
    background: radial-gradient(circle at top, #0b1f3a, #020617);
    color: white;
}

/* Header */
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

/* Chat container */
.chat-container {
    width: 60%;
    margin: auto;
    margin-top: 20px;
    padding-bottom: 120px;
}

/* Chat bubbles */
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

/* Fixed input */
.input-box {
    position: fixed;
    bottom: 20px;
    left: 20%;
    width: 60%;
    background: rgba(30,40,60,0.95);
    padding: 12px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.1);
}

/* Thinking text */
.thinking {
    text-align:center;
    margin-top:10px;
    opacity:0.7;
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
# INPUT (FIXED)
# =========================
st.markdown('<div class="input-box">', unsafe_allow_html=True)

q = st.text_input("", placeholder="Ask SmartLoop...", key="input")

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# LOGIC (UNCHANGED)
# =========================
if q and q != st.session_state.last_q:

    st.session_state.last_q = q

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"user",
        "text":q
    })

    thinking = st.empty()
    thinking.markdown("<div class='thinking'>🤖 Thinking...</div>", unsafe_allow_html=True)

    ans = ai_answer(q)

    thinking.empty()

    st.session_state.chats[st.session_state.current_chat].append({
        "role":"ai",
        "text":ans
    })

    st.rerun()

