import streamlit as st
import re, random, itertools, math
from google import genai
from openai import OpenAI

# =========================
# 🔑 MULTI API SETUP
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
# 🧠 CLEAN (DON’T OVER-CLEAN)
# =========================
def clean(q):
    return q.lower().strip()

# =========================
# 🎓 GRADE DETECTION
# =========================
def get_grade(q):
    m = re.search(r"(\d+)", q)
    if m:
        g = int(m.group(1))
        if 1 <= g <= 12:
            return g
    return None

# =========================
# 🧮 MATH / ALGEBRA ENGINE
# =========================
# Try to import SymPy (for algebra)
try:
    from sympy import symbols, Eq, solve, sympify
    SYMPY = True
except Exception:
    SYMPY = False

def normalize_expr(q):
    q = q.replace("^", "**")
    q = q.replace("[", "(").replace("]", ")")
    q = q.replace("{", "(").replace("}", ")")
    return q

def factorial_handler(expr):
    # n! -> math.factorial(n)
    return re.sub(r"(\d+)!", r"math.factorial(\1)", expr)

def solve_algebra(q):
    """Robust linear solver: supports any variable, implicit multiplication, and messy tails."""
    if "=" not in q or not SYMPY:
        return None

    try:
        # keep only math-ish chars; drop trailing junk like '=fail'
        q = re.sub(r"[^0-9a-zA-Z+\-*/=().]", "", q)

        # split only first '='
        parts = q.split("=")
        if len(parts) < 2:
            return None
        left, right = parts[0], parts[1]

        # detect variable (first letter)
        var_match = re.search(r"[a-zA-Z]", q)
        if not var_match:
            return None
        var_name = var_match.group()
        var = symbols(var_name)

        # implicit multiplication: 2x -> 2*x, x2 -> x*2
        left = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", left)
        left = re.sub(r"([a-zA-Z])(\d)", r"\1*\2", left)
        right = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", right)
        right = re.sub(r"([a-zA-Z])(\d)", r"\1*\2", right)

        # IMPORTANT: pass variable to sympify
        left_expr = sympify(left, locals={var_name: var})
        right_expr = sympify(right, locals={var_name: var})

        eq = Eq(left_expr, right_expr)
        sol = solve(eq, var)

        if sol:
            return f"🧮 {var_name} = {sol[0]}"
        return "⚠️ No solution."

    except Exception as e:
        print("Algebra error:", e)
        return None

def solve_math(q):
    """Handles arithmetic, factorial, %, powers, brackets; falls back to algebra if '=' present."""
    original = q
    q = normalize_expr(q)

    # Algebra first (if equation present)
    algebra = solve_algebra(q)
    if algebra:
        return algebra

    # For pure arithmetic, allow 'x' as multiplication symbol
    if "=" not in q:
        q = q.replace("x", "*")

    # factorial
    q = factorial_handler(q)

    # safe whitelist
    if not re.fullmatch(r"[0-9+\-*/().\s%*mathfactorial]+", q):
        return None

    try:
        result = eval(q, {"__builtins__": None, "math": math}, {})
        return f"🧮 {original} = {result}"
    except Exception as e:
        print("Math error:", e)
        return None

# =========================
# 🧠 QUIZ SYSTEM
# =========================
def get_topic(q):
    m = re.findall(r"quiz on ([a-z\s]+)", q)
    return m[-1].strip().capitalize() if m else "General Science"

def fallback_quiz(topic):
    return f"""Q1. What is {topic} mainly about?
A) Physics
B) Biology
C) Chemistry
D) Math

Q2. Which factor is important in {topic}?
A) Light
B) Water
C) Air
D) All of these
"""

def generate_quiz(q):
    topic = get_topic(q)
    grade = st.session_state.grade or 6

    prompt = f"""
Create a HIGH-QUALITY 5-question MCQ quiz on {topic} for grade {grade}.

Rules:
- No generic questions
- Cover different concepts
- Use Q1, A), B), C), D)
"""

    text = None

    # Try Google
    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if r.text and len(r.text.split()) > 40:
                text = r.text
                break
        except:
            continue

    # Try OpenAI
    if not text:
        for _ in range(2):
            try:
                c = get_openai()
                r = c.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":prompt}]
                )
                if r.choices[0].message.content:
                    text = r.choices[0].message.content
                    break
            except:
                continue

    # Final fallback
    if not text:
        text = fallback_quiz(topic)

    st.session_state.last_quiz = text
    text = text.replace("Q", "\nQ")

    return f"🧠 Quiz on {topic}:\n{text.strip()}"

def get_answers():
    text = st.session_state.last_quiz
    if not text:
        return "⚠️ No quiz yet."
    answers = [l for l in text.split("\n") if "Answer" in l]
    return "\n".join(answers) if answers else "⚠️ No answers stored."

# =========================
# 🧠 GENERAL ANSWER (AI + RETRIES)
# =========================
def offline_explain(q):
    if "sound" in q:
        return "Sound is energy from vibrations that travel as waves through a medium like air."
    if "cell" in q:
        return "A cell is the smallest unit of life; all living things are made of cells."
    if "indices" in q or "powers" in q:
        return "Indices (powers) show repeated multiplication, e.g., 2^3 = 2×2×2 = 8."
    if "photosynthesis" in q:
        return "Photosynthesis is how plants make food using sunlight, water, and carbon dioxide."
    return "⚠️ Try again in a moment."

def general_answer(q):
    prompt = f"Explain clearly for a student:\n{q}"

    # Google tries
    for _ in range(3):
        try:
            c = get_google()
            r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if r.text and len(r.text.strip()) > 20:
                return r.text.strip()
        except:
            continue

    # OpenAI tries
    for _ in range(3):
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            text = r.choices[0].message.content
            if text and len(text.strip()) > 20:
                return text.strip()
        except:
            continue

    return offline_explain(q)

# =========================
# 🤖 MAIN ROUTER
# =========================
def ai(q):
    q = clean(q)

    # Save grade (don’t block)
    g = get_grade(q)
    if g:
        st.session_state.grade = g

    # 🔥 math first
    math_res = solve_math(q)
    if math_res:
        return math_res

    # answers
    if "answer" in q:
        return get_answers()

    # quiz
    if "quiz" in q:
        if not st.session_state.grade:
            return "📚 Tell me your grade first."
        return generate_quiz(q)

    # normal Q&A
    return general_answer(q)

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Final Stable)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)
    st.write("🤖", ai(q))
