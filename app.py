import streamlit as st
import itertools, re, feedparser, wikipedia, uuid

from google import genai
from openai import OpenAI

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="SmartLoop AI", page_icon="🧠", layout="wide")

# =========================
# API
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

if "grade" not in st.session_state:
    st.session_state.grade = "Grade 6"

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("## 👋 Welcome Back")

    st.session_state.grade = st.selectbox(
        "🎯 Grade",
        [f"Grade {i}" for i in range(1, 11)],
        index=5
    )

    if st.button("➕ New Chat"):
        name = f"Chat {str(uuid.uuid4())[:6]}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()

    st.markdown("### 💬 Chats")

    for chat in list(st.session_state.chats.keys()):
        col1, col2 = st.columns([0.8, 0.2])

        if col1.button(chat):
            st.session_state.current_chat = chat
            st.rerun()

        if col2.button("🗑", key=chat):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[chat]
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                st.rerun()

# =========================
# 🧠 BASIC DEFINITIONS (SMART FIX)
# =========================
def basic_definitions(q):

    ql = q.lower()

    if "integer" in ql:
        return """📘 **Integers**

Integers are whole numbers:
• Positive → 1, 2, 3  
• Negative → -1, -2, -3  
• Zero → 0  

❌ No fractions or decimals.
"""

    if "fraction" in ql:
        return "A fraction represents a part of a whole (like 1/2)."

    if "multiplication" in ql:
        return "Multiplication means repeated addition."

    return None

# =========================
# QUIZ
# =========================
def is_quiz(q):
    return "quiz" in q.lower()

def generate_quiz(topic):
    return f"""📝 **Quiz on {topic}**

1. 6 × 4 = ?
2. 9 × 3 = ?
3. 7 × 8 = ?
4. 12 × 5 = ?
5. 11 × 6 = ?

Try solving them!"""

# =========================
# MATH
# =========================
def solve_math(q):
    try:
        expr = re.findall(r"[0-9\+\-\*/\^\(\)]+", q)
        if expr:
            return f"🧮 Answer: {eval(expr[0].replace('^','**'))}"
    except:
        return None

# =========================
# NEWS
# =========================
def is_news(q):
    return "news" in q.lower()

def get_news():
    feed = feedparser.parse("https://news.google.com/rss")
    return "📰 Latest News:\n\n" + "\n".join([f"• {e.title}" for e in feed.entries[:8]])

# =========================
# AI ANSWER
# =========================
def ai_answer(q, history):

    # 📘 definitions first
    definition = basic_definitions(q)
    if definition:
        return definition

    # 📝 quiz
    if is_quiz(q):
        return generate_quiz(q.replace("quiz on",""))

    # 📰 news
    if is_news(q):
        return get_news()

    # 🧮 math
    math = solve_math(q)
    if math:
        return math

    # 🧠 AI (main)
    prompt = f"""
You are SmartLoop AI.
Student grade: {st.session_state.grade}

Answer clearly and correctly.
"""

    try:
        return get_google().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt + "\n\n" + q
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

    # 🌐 fallback
    try:
        return "🌐 " + wikipedia.summary(q, 2)
    except:
        return "⚠️ Could not answer."

# =========================
# MAIN UI
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
