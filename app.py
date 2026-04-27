import streamlit as st
import re, random, itertools, math
from google import genai
from openai import OpenAI

# OPTIONAL (for algebra)
try:
    from sympy import symbols, Eq, solve
    SYMPY_AVAILABLE = True
except:
    SYMPY_AVAILABLE = False

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
if "grade" not in st.session_state:
    st.session_state.grade = None

if "last_quiz" not in st.session_state:
    st.session_state.last_quiz = ""

# =========================
# 🧠 CLEAN INPUT
# =========================
def clean(q):
    return q.lower().strip()

# =========================
# 🧠 GRADE
# =========================
def get_grade(q):
    m = re.search(r"(\d+)", q)
    if m:
        g = int(m.group(1))
        if 1 <= g <= 12:
            return g
    return None

# =========================
# 🧮 MATH ENGINE
# =========================
def normalize_expr(q):
    q = q.replace("^", "**")
    q = q.replace("[", "(").replace("]", ")")
    q = q.replace("{", "(").replace("}", ")")
    return q

def factorial_handler(expr):
    return re.sub(r"(\d+)!", r"math.factorial(\1)", expr)

def solve_algebra(q):
    if "=" not in q or not SYMPY_AVAILABLE:
        return None
    try:
        x = symbols('x')
        left, right = q.split("=")
        eq = Eq(eval(left), eval(right))
        sol = solve(eq, x)
        return f"🧮 x = {sol[0]}"
    except:
        return None

def solve_math(q):
    original = q
    q = normalize_expr(q)

    # algebra first
    algebra = solve_algebra(q)
    if algebra:
        return algebra

    # replace x with * ONLY if not algebra
    if "=" not in q:
        q = q.replace("x", "*")

    # factorial
    q = factorial_handler(q)

    # safe filter
    if not re.fullmatch(r"[0-9+\-*/().\s%*mathfactorial]+", q):
        return None

    try:
        result = eval(q, {"__builtins__": None, "math": math}, {})
        return f"🧮 {original} = {result}"
    except:
        return None

# =========================
# 🧠 TOPIC
# =========================
def get_topic(q):
    m = re.findall(r"quiz on ([a-z\s]+)", q)
    return m[-1].strip().capitalize() if m else "General Science"

# =========================
# 🧠 MODE
# =========================
def get_mode(q):
    if "answers" in q and "quiz" in q:
        return "qa"
    if "answers" in q:
        return "answers"
    return "questions"

# =========================
# 🔥 FALLBACK QUIZ
# =========================
def fallback_quiz(topic):
    return f"""Q1. Where does {topic} occur in plant cells?
A) Nucleus
B) Chloroplast
C) Ribosome
D) Cytoplasm

Q2. Which gas is used?
A) Oxygen
B) Carbon dioxide
C) Nitrogen
D) Hydrogen
"""

# =========================
# 🧠 GENERAL ANSWER
# =========================
def general_answer(q):
    prompt = f"Explain simply for a student:\n{q}"

    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if r.text:
                return r.text.strip()
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

    return "⚠️ Try again."

# =========================
# 🧠 QUIZ
# =========================
def generate_quiz(q):
    topic = get_topic(q)
    grade = st.session_state.grade or 6

    prompt = f"""
Create a 5-question MCQ quiz on {topic} for grade {grade}.
Use Q1 format with A B C D.
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
        text = fallback_quiz(topic)

    st.session_state.last_quiz = text
    return f"🧠 Quiz on {topic}:\n{text}"

# =========================
# 🧠 ANSWERS
# =========================
def get_answers():
    text = st.session_state.last_quiz
    answers = [l for l in text.split("\n") if "Answer" in l]
    return "\n".join(answers) if answers else "⚠️ No answers."

# =========================
# 🤖 MAIN AI
# =========================
def ai(q):
    q = clean(q)

    # grade
    g = get_grade(q)
    if g:
        st.session_state.grade = g

    # 🔥 math first
    math_res = solve_math(q)
    if math_res:
        return math_res

    if "answer" in q:
        return get_answers()

    if "quiz" in q:
        if not st.session_state.grade:
            return "📚 Tell me your grade."
        return generate_quiz(q)

    return general_answer(q)

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Math + AI)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)
    st.write("🤖", ai(q))
