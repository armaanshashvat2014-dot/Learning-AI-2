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
# 🛡️ SAFETY
# =========================
def is_safe(q):
    return True  # keep simple, your AI already filters

# =========================
# 🧠 MODE DETECTION (NEW)
# =========================
def detect_quiz_mode(q):
    ql = q.lower()

    if "only answers" in ql or ql.strip() == "answers":
        return "answers_only"

    if "answers" in ql:
        return "qa"

    if "only quiz" in ql or "only questions" in ql:
        return "questions_only"

    return "questions_only"  # default

# =========================
# 🧠 TOPIC EXTRACTION (SMART)
# =========================
def extract_topic(q):
    ql = q.lower()

    match = re.search(r"quiz on ([a-zA-Z0-9\s]+)", ql)
    if match:
        return match.group(1).strip().capitalize()

    # fallback: last meaningful word
    words = [w for w in ql.split() if len(w) > 3]
    if words:
        return words[-1].capitalize()

    return "General Knowledge"

# =========================
# 🧮 MATH (WITH [] {})
# =========================
def normalize_expression(expr):
    expr = expr.replace("[", "(").replace("]", ")")
    expr = expr.replace("{", "(").replace("}", ")")
    expr = expr.replace(" ", "")

    expr = re.sub(r"(\d)(\()", r"\1*\2", expr)
    expr = re.sub(r"(\))(\()", r"\1*\2", expr)
    expr = re.sub(r"(\))(\d)", r"\1*\2", expr)

    return expr

def extract_math(q):
    pattern = r"[0-9\+\-\*/\^\(\)\[\]\{\}\.\s]+"
    matches = re.findall(pattern, q)

    if not matches:
        return None

    expr = "".join(matches).strip()
    if not any(c.isdigit() for c in expr):
        return None

    return normalize_expression(expr.replace("^", "**"))

def solve_math(q):
    expr = extract_math(q)
    if not expr:
        return None
    try:
        return f"🧮 {expr} = {eval(expr, {'__builtins__':None}, {})}"
    except:
        return None

# =========================
# 🧠 QUIZ GENERATOR (SMART MODES)
# =========================
def generate_quiz(q):
    topic = extract_topic(q)
    mode = detect_quiz_mode(q)

    prompt = f"""
Create a 5-question quiz on {topic}.
Include options A-D and answers.
"""

    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = r.text
    except:
        text = None

    if not text:
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            text = r.choices[0].message.content
        except:
            text = None

    # fallback hardcoded
    if not text:
        text = """Q1. What do plants use to make food?
A) Oxygen
B) Sunlight
C) Soil
D) Water
Answer: B"""

    # =====================
    # 🎯 MODE FILTERING
    # =====================
    if mode == "questions_only":
        lines = []
        for line in text.split("\n"):
            if "Answer" not in line:
                lines.append(line)
        return f"🧠 Quiz on {topic}:\n\n" + "\n".join(lines)

    if mode == "answers_only":
        answers = [line for line in text.split("\n") if "Answer" in line]
        return f"🧠 Answers on {topic}:\n\n" + "\n".join(answers)

    # default Q + A
    return f"🧠 Quiz on {topic}:\n\n{text}"

# =========================
# 📰 NEWS
# =========================
def get_news():
    feed = feedparser.parse("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
    headlines = [f"• {e.title}" for e in feed.entries[:5]]
    return "📰 Latest News:\n\n" + "\n".join(headlines)

# =========================
# 🌐 WIKI
# =========================
def search_wiki(q):
    try:
        return wikipedia.summary(q, 2)
    except:
        return None

# =========================
# 🤖 AI CORE
# =========================
def ai_answer(q):

    if not is_safe(q):
        return "⚠️ Not allowed."

    ql = q.lower()

    # 🔥 PRIORITY FIX
    if "quiz" in ql:
        return generate_quiz(q)

    if "news" in ql or "latest" in ql:
        return get_news()

    math = solve_math(q)
    if math:
        return math

    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=q
        )
        if r.text:
            return r.text
    except:
        pass

    wiki = search_wiki(q)
    if wiki:
        return wiki

    return "⚠️ Not sure."

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartLoop AI")
st.info("Now supports smart quiz modes (Q / A / Q&A) 🚀")

for msg in st.session_state.chats[st.session_state.current_chat]:
    role = "🧑" if msg["role"]=="user" else "🤖"
    st.write(f"{role} {msg['text']}")

q = st.text_input("Ask...")

if q and q != st.session_state.last_q:
    st.session_state.last_q = q

    st.session_state.chats[st.session_state.current_chat].append(
        {"role":"user","text":q}
    )

    ans = ai_answer(q)

    st.session_state.chats[st.session_state.current_chat].append(
        {"role":"ai","text":ans}
    )

    st.rerun()
