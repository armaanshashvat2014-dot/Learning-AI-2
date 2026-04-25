import streamlit as st
import itertools, re, wikipedia, random

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
# 🧠 CONSCIOUS ENGINE
# =========================
def conscious_engine(q, history):
    ql = q.lower()

    if "ice cream" in ql and ("200" in ql or "heat" in ql or "hot" in ql):
        return "❌ No. Ice cream melts at high temperatures."

    if "breathe in space" in ql:
        return "❌ No. Humans cannot breathe in space."

    if "fire cold" in ql:
        return "❌ No. Fire produces heat."

    if "hot and cold" in ql:
        return "❌ Something cannot be both hot and cold at the same time."

    # simple context use
    if history:
        last = history[-1]["text"].lower()
        if "sound" in last and "how" in ql:
            return "🔊 Sound travels as vibrations through a medium like air."

    return None

# =========================
# 🔎 SEARCH (FREE)
# =========================
def search_answer(q):
    try:
        return "🌐 " + wikipedia.summary(q, 2)
    except:
        return None

# =========================
# 🧮 MATH (ROBUST)
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\.]+", q)
    expr = "".join(matches)
    return expr.replace("^","**") if expr else None

def solve_math(q):
    expr = extract_math(q)
    if not expr:
        return None
    try:
        return str(eval(expr, {"__builtins__":None}, {}))
    except:
        return None

def math_response(q):
    ans = solve_math(q)
    if not ans:
        return None
    if any(w in q.lower() for w in ["explain","why","how"]):
        return f"🧮 The answer is {ans}.\n\nUsing BODMAS, powers are solved first, then multiplication/division, then addition/subtraction."
    return f"🧮 {ans}"

# =========================
# SUBJECT DETECTION
# =========================
def detect_subject(q):
    ql = q.lower()

    math_words = ["add","subtract","multiply","divide","fraction","decimal","algebra","indices","exponent","equation","+","-","*","/","^","bodmas","order"]
    science_words = ["sound","light","heat","force","energy","cell","atom","gravity","friction","wave","electric","current","voltage","motion","speed","mass","density","pressure","photosynthesis","respiration","digestion","ecosystem","plant","animal","human","biology","physics","chemistry","gas","liquid","solid","matter","temperature"]
    english_words = ["noun","verb","grammar","sentence","adjective","adverb","pronoun","tense","english","language","paragraph","essay","letter","comprehension","synonym","antonym","word","phrase"]

    scores = {"math":0,"science":0,"english":0}
    for w in math_words:
        if w in ql: scores["math"] += 2
    for w in science_words:
        if w in ql: scores["science"] += 2
    for w in english_words:
        if w in ql: scores["english"] += 2

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "science"

# =========================
# QUESTION GENERATORS
# =========================
def gen_math(topic, mode):
    topic = topic.lower()
    qs = []
    n = {"Quiz Mode":5,"Test Mode":6}.get(mode,4)

    for _ in range(n):
        if "indice" in topic or "power" in topic:
            a = random.randint(2,10); b = random.randint(2,4)
            qs.append(f"{a}^{b}")
        elif "fraction" in topic:
            a,b = random.randint(1,9), random.randint(1,9)
            c,d = random.randint(1,9), random.randint(1,9)
            qs.append(f"{a}/{b} + {c}/{d}")
        elif "algebra" in topic:
            x = random.randint(1,10)
            qs.append(f"Solve: x + {x} = {x+5}")
        elif "bodmas" in topic or "order" in topic:
            a,b,c = random.randint(1,10), random.randint(1,10), random.randint(1,10)
            qs.append(f"({a} + {b}) * {c}")
        else:
            a = random.randint(1,10); b = random.randint(2,5); c = random.randint(2,3)
            qs.append(f"{a} + {b}^{c}")
    return qs

def gen_science(topic):
    return [
        f"What is {topic}?",
        f"Why is {topic} important?",
        f"How does {topic} work?",
        f"Who discovered {topic}?",
        f"When is {topic} used?"
    ]

def gen_english(topic):
    return [
        f"What is {topic}?",
        f"How do you use {topic} in a sentence?",
        f"Why is {topic} important in language?"
    ]

def generate_questions(q, mode):
    sub = detect_subject(q)
    if sub == "science":
        return gen_science(q)
    if sub == "english":
        return gen_english(q)
    return gen_math(q, mode)

# =========================
# 🤖 AI ANSWER
# =========================
def ai_answer(q):
    history = st.session_state.chats[st.session_state.current_chat]

    # 1. conscious
    cs = conscious_engine(q, history)
    if cs: return cs

    # 2. math
    m = math_response(q)
    if m: return m

    # 3. search
    s = search_answer(q)
    if s: return s

    # 4. AI fallback
    prompt = f"Answer clearly and logically like a teacher:\n{q}"

    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if r.text:
                return r.text
        except:
            pass

    for _ in range(2):
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
        except:
            pass

    return "⚠️ I'm not sure. Try rephrasing."

# =========================
# 🎨 UI STYLE
# =========================
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#0a0f1f,#020617); color:white;}
.chat-user {background:#1e293b;padding:10px;border-radius:10px;margin:6px 0;}
.chat-ai {background:#111827;padding:10px;border-radius:10px;border-left:4px solid #38bdf8;margin:6px 0;}
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# =========================
# SIDEBAR (CHATS + MODES)
# =========================
st.sidebar.title("💬 Chats")

if st.sidebar.button("➕ New Chat"):
    name = f"Chat {len(st.session_state.chats)+1}"
    st.session_state.chats[name] = []
    st.session_state.current_chat = name

for chat in st.session_state.chats:
    if st.sidebar.button(chat):
        st.session_state.current_chat = chat

if st.sidebar.button("🗑 Delete Current Chat"):
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[st.session_state.current_chat]
        st.session_state.current_chat = list(st.session_state.chats.keys())[0]

st.sidebar.markdown("---")
mode = st.sidebar.selectbox("Mode", ["Tutor Mode","Teacher Mode","Quiz Mode","Test Mode"])

# =========================
# HEADER
# =========================
st.title("🧠 SmartLoop AI")
st.caption("CIE Tutor • Smart Chat")

st.info("""
👋 Hey there! I'm SmartLoop AI! 

I'm your CIE tutor here to help you ace your exams! 📚

I can answer your doubts, draw diagrams, and create quizzes! 
Attach photos, PDFs, or text files below! 📸📄
""")

# =========================
# CHAT DISPLAY
# =========================
for msg in st.session_state.chats[st.session_state.current_chat]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-user'>🧑 {msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-ai'>🤖 {msg['text']}</div>", unsafe_allow_html=True)

# =========================
# INPUT + NON-BLOCKING LOADER
# =========================
q = st.text_input("Ask SmartLoop...")

if q:
    st.session_state.chats[st.session_state.current_chat].append({"role":"user","text":q})

    with st.spinner("Thinking..."):
        # ===== Mode logic =====
        if mode == "Tutor Mode":
            ans = ai_answer(q)

        elif mode == "Teacher Mode":
            base = ai_answer(q)
            qs = generate_questions(q, "Teacher Mode")
            ans = base + "\n\n📝 Practice:\n" + "\n".join([f"- {x}" for x in qs])

        elif mode == "Quiz Mode":
            qs = generate_questions(q, "Quiz Mode")
            ans = "📝 Quiz:\n" + "\n".join([f"• {x}" for x in qs])

        elif mode == "Test Mode":
            qs = generate_questions(q, "Test Mode")
            ans = "🧪 Test:\n" + "\n".join([f"Q{i+1}. {x}" for i, x in enumerate(qs)])

    st.session_state.chats[st.session_state.current_chat].append({"role":"ai","text":ans})
    st.rerun()
