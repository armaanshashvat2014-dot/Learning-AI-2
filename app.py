import streamlit as st
import re, random, itertools
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
# 💾 SESSION MEMORY
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None

if "last_quiz" not in st.session_state:
    st.session_state.last_quiz = ""

# =========================
# 🧠 CLEAN INPUT
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
# 🔥 QUALITY FILTER
# =========================
def is_bad(text):
    if not text:
        return True
    bad = ["belongs to which subject", "which is important"]
    if len(text.split()) < 50:
        return True
    if any(b in text.lower() for b in bad):
        return True
    return False

# =========================
# 🔥 FALLBACK QUIZ
# =========================
def fallback(topic):
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

Q3. What is produced?
A) Protein
B) Glucose
C) Fat
D) Minerals

Q4. What absorbs sunlight?
A) Chlorophyll
B) Hemoglobin
C) DNA
D) Enzyme

Q5. Why is sunlight needed?
A) Energy
B) Cooling
C) Movement
D) Growth
"""

# =========================
# 🧠 QUIZ GENERATOR
# =========================
def generate_quiz(q):
    topic = get_topic(q)
    grade = st.session_state.grade or 6
    mode = get_mode(q)

    seed = random.randint(1, 9999)

    if mode == "questions":
        instruction = "DO NOT include answers."
    elif mode == "answers":
        instruction = "ONLY give answers like Q1: B"
    else:
        instruction = "Include answers."

    prompt = f"""
Create a HIGH QUALITY 5-question MCQ quiz on {topic} for grade {grade}.

Rules:
- No generic questions
- Cover different ideas
- Use Q1 format
- A B C D options
- Make it hard for grade {grade}

Seed: {seed}

{instruction}
"""

    text = None

    # Try Google
    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if r.text and not is_bad(r.text):
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
        text = fallback(topic)

    st.session_state.last_quiz = text
    text = text.replace("Q", "\nQ")

    return f"🧠 Quiz on {topic}:\n{text.strip()}"

# =========================
# 🧠 ANSWERS
# =========================
def get_answers():
    text = st.session_state.last_quiz
    if not text:
        return "⚠️ No quiz yet."

    answers = [l for l in text.split("\n") if "Answer" in l]

    if not answers:
        return "⚠️ No answers stored."

    return "🧠 Answers:\n" + "\n".join(answers)

# =========================
# 🧠 OFFLINE EXPLAIN
# =========================
def offline_explain(q):
    if "sound" in q:
        return "Sound is energy from vibrations that travel as waves through air."

    if "cell" in q:
        return "A cell is the smallest unit of life. All living things are made of cells."

    if "photosynthesis" in q:
        return "Photosynthesis is how plants make food using sunlight, water, and carbon dioxide."

    return f"{q.capitalize()} is an important concept. Try asking again for more detail."

# =========================
# 🧠 GENERAL ANSWER
# =========================
def general_answer(q):
    prompt = f"Explain simply: {q}"

    # Try Google
    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if r.text:
                return r.text.strip()
        except:
            continue

    # Try OpenAI
    for _ in range(2):
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
        except:
            continue

    return offline_explain(q)

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

    return general_answer(q)

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)
    st.write("🤖", ai(q))
