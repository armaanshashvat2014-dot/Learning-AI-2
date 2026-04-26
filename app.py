import streamlit as st
import itertools, re, wikipedia

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
# SESSION STATE
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

if "last_q" not in st.session_state:
    st.session_state.last_q = ""

# =========================
# 🧠 SAFETY (HARD GATE)
# =========================
def classify_safety(q):
    prompt = f"""
Classify the user query into ONE word:

- allowed → safe, educational
- blocked → harmful, illegal, dangerous (weapons, bombs, harm, etc.)

Be strict about harmful intent.

Query:
{q}

Answer ONLY: allowed or blocked
"""

    # Google
    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        if r.text:
            label = r.text.strip().lower()
            if "blocked" in label:
                return "blocked"
            return "allowed"
    except:
        pass

    # OpenAI fallback
    try:
        c = get_openai()
        r = c.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )
        label = r.choices[0].message.content.strip().lower()
        if "blocked" in label:
            return "blocked"
        return "allowed"
    except:
        pass

    # Fail-safe = block
    return "blocked"

# =========================
# 🧮 MATH ENGINE
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\.]+", q)
    expr = "".join(matches)
    return expr.replace("^","**") if expr else None

def solve_math_steps(q):
    expr = extract_math(q)
    if not expr:
        return None

    try:
        original = expr.replace("**", "^")
        steps = [f"Expression: {original}"]

        if "(" in expr:
            steps.append("Step 1: Solve brackets")
        if "**" in expr:
            steps.append("Step 2: Solve powers")
        if "*" in expr or "/" in expr:
            steps.append("Step 3: Multiply/Divide")

        steps.append("Step 4: Add/Subtract")

        result = eval(expr, {"__builtins__":None}, {})
        steps.append(f"Final Answer: {result}")

        return "🧮 Step-by-step:\n\n" + "\n".join(steps)

    except:
        return None

# =========================
# 🔎 WIKIPEDIA
# =========================
def search_wiki(q):
    try:
        return wikipedia.summary(q, 2)
    except:
        return None

# =========================
# 🤖 AI ANSWER
# =========================
def ai_answer(q):

    # 🚫 HARD SAFETY BLOCK (FIRST)
    if classify_safety(q) == "blocked":
        return "⚠️ I can’t help with that. It’s unsafe. But I can explain the science behind it if you want."

    # 🧮 Math
    math_steps = solve_math_steps(q)
    if math_steps:
        return math_steps

    # 🧠 Reasoning AI
    prompt = f"""
You are SmartLoop AI, a smart and logical tutor.

Rules:
- Understand intent
- Use real-world reasoning
- Be accurate and clear
- Do NOT generate random questions

Question:
{q}
"""

    # Google first
    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if r.text:
                return r.text
        except:
            pass

    # OpenAI fallback
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

    # Wikipedia fallback
    wiki = search_wiki(q)
    if wiki:
        return "🌐 " + wiki

    return "⚠️ I'm not fully sure. Try rephrasing, or you may repeat the command/request."

# =========================
# 🎨 UI
# =========================
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#0a0f1f,#020617); color:white;}
.chat-user {background:#1e293b;padding:10px;border-radius:10px;margin:6px;}
.chat-ai {background:#111827;padding:10px;border-radius:10px;border-left:4px solid #38bdf8;margin:6px;}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
st.sidebar.title("💬 Chats")

if st.sidebar.button("➕ New Chat"):
    name = f"Chat {len(st.session_state.chats)+1}"
    st.session_state.chats[name] = []
    st.session_state.current_chat = name

for chat in st.session_state.chats:
    if st.sidebar.button(chat):
        st.session_state.current_chat = chat

if st.sidebar.button("🗑 Delete Chat"):
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[st.session_state.current_chat]
        st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# =========================
# HEADER
# =========================
st.title("🧠 SmartLoop AI")
st.info("👋 Ask anything — math, science, English, or general knowledge.")

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
q = st.text_input("Ask SmartLoop...", key="input")

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
