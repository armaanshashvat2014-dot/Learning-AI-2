import streamlit as st
import re, random, itertools, math
from google import genai
from openai import OpenAI

# =========================
# 🔑 SAFE MULTI API SETUP
# =========================
GOOGLE_KEYS = [
    st.secrets.get("GOOGLE_API_KEY_1"),
    st.secrets.get("GOOGLE_API_KEY_2"),
    st.secrets.get("GOOGLE_API_KEY_3"),
    st.secrets.get("GOOGLE_API_KEY_4")
]

OPENAI_KEYS = [
    st.secrets.get("OPENAI_API_KEY_1"),
    st.secrets.get("OPENAI_API_KEY_2"),
    st.secrets.get("OPENAI_API_KEY_3")
]

# remove empty keys
GOOGLE_KEYS = [k for k in GOOGLE_KEYS if k]
OPENAI_KEYS = [k for k in OPENAI_KEYS if k]

google_cycle = itertools.cycle(GOOGLE_KEYS) if GOOGLE_KEYS else None
openai_cycle = itertools.cycle(OPENAI_KEYS) if OPENAI_KEYS else None

def get_google():
    if not google_cycle:
        return None
    try:
        return genai.Client(api_key=next(google_cycle))
    except:
        return None

def get_openai():
    if not openai_cycle:
        return None
    try:
        return OpenAI(api_key=next(openai_cycle))
    except:
        return None

# =========================
# 💾 SESSION
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None
if "last_quiz" not in st.session_state:
    st.session_state.last_quiz = ""

# =========================
# 🧠 CLEAN
# =========================
def clean(q):
    return q.lower().strip()

# =========================
# 🎓 GRADE
# =========================
def get_grade(q):
    m = re.search(r"(\d+)", q)
    if m:
        g = int(m.group(1))
        if 1 <= g <= 12:
            return g
    return None

# =========================
# 🧮 MATH + ALGEBRA
# =========================
try:
    from sympy import symbols, Eq, solve, sympify
    SYMPY = True
except:
    SYMPY = False

def normalize_expr(q):
    q = q.replace("^", "**")
    q = q.replace("[", "(").replace("]", ")")
    q = q.replace("{", "(").replace("}", ")")
    return q

def factorial_handler(expr):
    return re.sub(r"(\d+)!", r"math.factorial(\1)", expr)

def solve_algebra(q):
    if "=" not in q or not SYMPY:
        return None

    try:
        q = re.sub(r"[^0-9a-zA-Z+\-*/=().]", "", q)
        parts = q.split("=")
        if len(parts) < 2:
            return None

        left, right = parts[0], parts[1]

        var_match = re.search(r"[a-zA-Z]", q)
        if not var_match:
            return None

        var_name = var_match.group()
        var = symbols(var_name)

        left = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", left)
        right = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", right)

        left_expr = sympify(left, locals={var_name: var})
        right_expr = sympify(right, locals={var_name: var})

        eq = Eq(left_expr, right_expr)
        sol = solve(eq, var)

        if sol:
            return f"🧮 {var_name} = {sol[0]}"
        return "⚠️ No solution."

    except:
        return None

def solve_math(q):
    original = q
    q = normalize_expr(q)

    algebra = solve_algebra(q)
    if algebra:
        return algebra

    if "=" not in q:
        q = q.replace("x", "*")

    q = factorial_handler(q)

    if not re.fullmatch(r"[0-9+\-*/().\s%*mathfactorial]+", q):
        return None

    try:
        result = eval(q, {"__builtins__": None, "math": math}, {})
        return f"🧮 {original} = {result}"
    except:
        return None

# =========================
# 🧠 QUIZ
# =========================
def get_topic(q):
    m = re.findall(r"quiz on ([a-z\s]+)", q)
    return m[-1].strip().capitalize() if m else "General Science"

def fallback_quiz(topic):
    return f"""Q1. What is {topic}?
A) Physics
B) Biology
C) Chemistry
D) Math
"""

def generate_quiz(q):
    topic = get_topic(q)
    grade = st.session_state.grade or 6

    prompt = f"Create a 5-question MCQ quiz on {topic} for grade {grade}."

    text = None

    for _ in range(3):
        c = get_google()
        if c:
            try:
                r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                if r.text:
                    text = r.text
                    break
            except:
                continue

    if not text:
        for _ in range(3):
            c = get_openai()
            if c:
                try:
                    r = c.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role":"user","content":prompt}]
                    )
                    text = r.choices[0].message.content
                    break
                except:
                    continue

    if not text:
        text = fallback_quiz(topic)

    st.session_state.last_quiz = text
    return f"🧠 Quiz on {topic}:\n{text}"

def get_answers():
    text = st.session_state.last_quiz
    answers = [l for l in text.split("\n") if "Answer" in l]
    return "\n".join(answers) if answers else "⚠️ No answers stored."

# =========================
# 🧠 GENERAL ANSWER
# =========================
def general_answer(q):
    prompt = f"Explain clearly:\n{q}"

    for _ in range(3):
        c = get_google()
        if c:
            try:
                r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                if r.text:
                    return r.text
            except:
                continue

    for _ in range(3):
        c = get_openai()
        if c:
            try:
                r = c.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":prompt}]
                )
                return r.choices[0].message.content
            except:
                continue

    return "⚠️ Try again."

# =========================
# 🤖 MAIN
# =========================
def ai(q):
    q = clean(q)

    g = get_grade(q)
    if g:
        st.session_state.grade = g

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
st.title("🧠 SmartBot PRO")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)
    st.write("🤖", ai(q))
