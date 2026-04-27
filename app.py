import streamlit as st
import random, re, itertools
from google import genai
from openai import OpenAI

# =========================
# 🔑 MULTI API SYSTEM
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
# 💾 SESSION MEMORY
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None

if "last_quiz" not in st.session_state:
    st.session_state.last_quiz = ""

if "last_topic" not in st.session_state:
    st.session_state.last_topic = None

# =========================
# 🧠 INPUT CLEANING
# =========================
def clean(q):
    q = q.lower()
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    return re.sub(r"\s+", " ", q).strip()

# =========================
# 🧠 GRADE DETECTION
# =========================
def get_grade(q):
    m = re.search(r"(\d+)", q)
    if m:
        g = int(m.group(1))
        if 1 <= g <= 12:
            return g
    return None

# =========================
# 🧠 TOPIC EXTRACTION
# =========================
def get_topic(q):
    matches = re.findall(r"quiz on ([a-z\s]+)", q)
    if matches:
        return matches[-1].strip().capitalize()
    return "General Science"

# =========================
# 🧠 MODE DETECTION
# =========================
def get_mode(q):
    if "answers" in q and "quiz" in q:
        return "qa"
    if "answers" in q:
        return "answers"
    return "questions"

# =========================
# 🔥 QUALITY FILTER
# =========================
def is_bad(text):
    bad = ["belongs to which subject", "which is important"]
    if len(text.split()) < 50:
        return True
    if any(b in text.lower() for b in bad):
        return True
    return False

# =========================
# 🔥 FALLBACK QUIZ (GOOD)
# =========================
def fallback(topic):
    return f"""Q1. Where in the plant cell does {topic} mainly occur?
A) Nucleus
B) Chloroplast
C) Mitochondria
D) Ribosome

Q2. Which gas is absorbed during {topic}?
A) Oxygen
B) Carbon dioxide
C) Nitrogen
D) Hydrogen

Q3. What is produced as food?
A) Protein
B) Glucose
C) Fat
D) Salt

Q4. What pigment captures sunlight?
A) Hemoglobin
B) Chlorophyll
C) Melanin
D) Keratin

Q5. Why is sunlight needed?
A) Energy
B) Cooling
C) Growth
D) Waste removal
"""

# =========================
# 🧠 QUIZ GENERATOR
# =========================
def generate_quiz(q):
    topic = get_topic(q)
    grade = st.session_state.grade or 6
    mode = get_mode(q)

    seed = random.randint(1,10000)

    if mode == "questions":
        instruction = "DO NOT include answers."
    elif mode == "answers":
        instruction = "ONLY give answers like Q1: B"
    else:
        instruction = "Include answers."

    prompt = f"""
Create a HIGH QUALITY 5 question quiz on {topic} for grade {grade}.

Rules:
- No basic questions
- No repetition
- Use Q1 format
- MCQ with A B C D

Seed: {seed}

{instruction}
"""

    text = None

    # TRY GOOGLE
    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = r.text
            if text and not is_bad(text):
                break
        except:
            pass

    # FALLBACK OPENAI
    if not text or is_bad(text):
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            text = r.choices[0].message.content
        except:
            pass

    # FINAL FALLBACK
    if not text or is_bad(text):
        text = fallback(topic)

    st.session_state.last_quiz = text
    st.session_state.last_topic = topic

    return f"🧠 Quiz on {topic}:\n{text}"

# =========================
# 🧠 ANSWERS
# =========================
def get_answers():
    text = st.session_state.last_quiz
    if not text:
        return "⚠️ No quiz yet."

    lines = [l for l in text.split("\n") if "Answer" in l]

    if not lines:
        return "⚠️ This quiz had no stored answers."

    return "\n".join(lines)

# =========================
# 🤖 MAIN AI
# =========================
def ai(q):
    q = clean(q)

    g = get_grade(q)
    if g:
        st.session_state.grade = g
        return f"✅ Grade {g} saved."

    if "answer" in q:
        return get_answers()

    if "quiz" in q:
        if not st.session_state.grade:
            return "📚 Tell me your grade first."
        return generate_quiz(q)

    return "🤖 Ask me to make a quiz!"

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)
    st.write("🤖", ai(q))
