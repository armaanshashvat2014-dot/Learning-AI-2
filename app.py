import streamlit as st
import itertools, re, random, wikipedia, feedparser
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

if "grade" not in st.session_state:
    st.session_state.grade = None

# 🔥 NEW MEMORY
if "last_quiz_topic" not in st.session_state:
    st.session_state.last_quiz_topic = None

if "last_quiz_text" not in st.session_state:
    st.session_state.last_quiz_text = None

# =========================
# 🧠 GRADE DETECTION
# =========================
def extract_grade(q):
    match = re.search(r"(\d+)\s*(st|nd|rd|th)?\s*(grade|graders)?", q.lower())
    if match:
        g = int(match.group(1))
        if 1 <= g <= 12:
            return g
    return None

# =========================
# 🧠 TOPIC EXTRACTION
# =========================
def extract_topic(q):
    ql = q.lower()

    matches = re.findall(r"quiz on ([a-zA-Z\s]+)", ql)
    topic = matches[-1] if matches else ql

    stop_words = {
        "make","easier","harder","later","regenerate",
        "quiz","answers","only","for","grade","graders",
        "and","it","the"
    }

    words = [w for w in topic.split() if w not in stop_words]
    topic = " ".join(words)

    if len(topic.strip()) < 3:
        return "General Science"

    return topic.strip().capitalize()

# =========================
# 🧮 MATH
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
# 🔥 FALLBACK QUIZ
# =========================
def fallback_quiz(topic):
    return f"""Q1. {topic} is related to which subject?
A) Physics
B) Biology
C) Math
D) History
Answer: B

Q2. Which factor is important in {topic}?
A) Light
B) Water
C) Air
D) All of these
Answer: D
"""

# =========================
# 🧠 QUIZ GENERATOR
# =========================
def generate_quiz(q):
    topic = extract_topic(q)
    grade = st.session_state.grade or 6

    seed = random.randint(1, 10000)

    prompt = f"""
Create a 5-question MCQ quiz on {topic} for Grade {grade} students.

Variation seed: {seed}

Rules:
- No repetition
- Use Q1, A), B), C), D)
- Include answers
"""

    text = None

    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = r.text
    except:
        pass

    if not text:
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            text = r.choices[0].message.content
        except:
            pass

    if not text or len(text.strip()) < 20:
        text = fallback_quiz(topic)

    # 🔥 SAVE MEMORY
    st.session_state.last_quiz_topic = topic
    st.session_state.last_quiz_text = text

    return f"🧠 Quiz on {topic}:\n{text.strip()}"

# =========================
# 🧠 ANSWER HANDLER
# =========================
def get_last_answers():
    text = st.session_state.last_quiz_text

    if not text:
        return "⚠️ No quiz found. Ask for a quiz first."

    answers = []
    for line in text.split("\n"):
        if "Answer" in line:
            answers.append(line.strip())

    if not answers:
        return "⚠️ No answers available."

    return "🧠 Answers:\n" + "\n".join(answers)

# =========================
# 📰 NEWS
# =========================
def get_news():
    feed = feedparser.parse("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
    headlines = [f"• {e.title}" for e in feed.entries[:5]]
    return "📰 Latest News:\n" + "\n".join(headlines)

# =========================
# 🤖 AI CORE
# =========================
def ai_answer(q):

    grade = extract_grade(q)
    if grade:
        st.session_state.grade = grade
        return f"✅ Got it! Grade {grade} saved."

    ql = q.lower()

    # 🔥 ANSWERS FIX
    if "answer" in ql:
        return get_last_answers()

    if "quiz" in ql:
        if st.session_state.grade is None:
            return "📚 What grade are you in?"
        return generate_quiz(q)

    if "news" in ql or "latest" in ql:
        return get_news()

    math = solve_math(q)
    if math:
        return math

    return "⚠️ Not sure."

# =========================
# 🎨 UI
# =========================
st.markdown("""
<style>
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
    white-space: pre-line;
}
</style>
""", unsafe_allow_html=True)

st.title("🧠 SmartLoop AI")
st.caption("Memory + Quiz + Answers System 🚀")

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
    
