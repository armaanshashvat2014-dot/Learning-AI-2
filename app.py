# =========================
# SMARTLOOP AI - FINAL SMART VERSION
# =========================
import streamlit as st
import itertools, re, wikipedia, feedparser

from google import genai
from openai import OpenAI

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="SmartLoop AI", page_icon="🧠", layout="wide")

# =========================
# API SETUP
# =========================
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

if "last_q" not in st.session_state:
    st.session_state.last_q = ""

# =========================
# 🧠 SMART DETECTION
# =========================
def is_math_topic(q):
    ql = q.lower()
    return any(w in ql for w in [
        "indices","index laws","powers","exponents"
    ])

# =========================
# 📘 MATH EXPLANATIONS
# =========================
def explain_indices():
    return """📘 **Indices (Exponents)**

Indices tell us how many times a number is multiplied by itself.

### Example
2³ = 2 × 2 × 2 = 8

### Rules
• a⁰ = 1  
• a¹ = a  
• a² × a³ = a⁵  
• a⁵ ÷ a² = a³  
• (a²)³ = a⁶  

💡 Simple: Indices = repeated multiplication.
"""

# =========================
# 🧮 MATH SOLVER
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\[\]\{\}\.]+", q)
    expr = "".join(matches)

    if not expr:
        return None

    expr = expr.replace("[","(").replace("]",")")
    expr = expr.replace("{","(").replace("}",")")
    return expr.replace("^","**")

def solve_math(q):
    expr = extract_math(q)
    if not expr:
        return None
    try:
        return f"🧮 Answer: {eval(expr)}"
    except:
        return None

# =========================
# 📰 NEWS
# =========================
def is_news(q):
    return "news" in q.lower()

def get_news():
    feed = feedparser.parse("https://news.google.com/rss")
    return "📰 News:\n\n" + "\n".join([f"• {e.title}" for e in feed.entries[:8]])

# =========================
# 🤖 AI ANSWER (SMART CORE)
# =========================
def ai_answer(q, history):

    # 🔒 safety
    if "bomb" in q.lower():
        return "⚠️ I can't help with that."

    # 📰 news
    if is_news(q):
        return get_news()

    # 🧮 math solve
    math = solve_math(q)
    if math:
        return math

    # 📘 math topic
    if is_math_topic(q):
        return explain_indices()

    # 🧠 MAIN AI (FIRST PRIORITY)
    prompt = f"""
You are SmartLoop AI — a smart tutor.

Answer clearly and correctly.
Understand the subject deeply.

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
            messages=[{"role":"user","content":q}]
        ).choices[0].message.content
    except:
        pass

    # 🌐 LAST fallback only
    try:
        return "🌐 " + wikipedia.summary(q, 2)
    except:
        return "⚠️ Could not find an answer."

# =========================
# UI
# =========================
st.title("🧠 SmartLoop AI")

messages = st.session_state.chats[st.session_state.current_chat]

for m in messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

q = st.chat_input("Ask SmartLoop...")

if q and q != st.session_state.last_q:

    st.session_state.last_q = q
    messages.append({"role":"user","content":q})

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            ans = ai_answer(q, messages[:-1])
            st.markdown(ans)

    messages.append({"role":"assistant","content":ans})
