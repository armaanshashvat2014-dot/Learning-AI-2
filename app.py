import streamlit as st
import itertools, re, random, feedparser
from difflib import get_close_matches
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
if "grade" not in st.session_state:
    st.session_state.grade = None

if "last_quiz_topic" not in st.session_state:
    st.session_state.last_quiz_topic = None

if "last_quiz_text" not in st.session_state:
    st.session_state.last_quiz_text = None

# =========================
# 🧠 SPELL CORRECTION
# =========================
KNOWN_TOPICS = [
    "photosynthesis", "plants", "fractions",
    "decimals", "gravity", "cells", "atoms"
]

def correct_spelling(word):
    match = get_close_matches(word, KNOWN_TOPICS, n=1, cutoff=0.6)
    return match[0] if match else word

# =========================
# 🧠 CLEAN INPUT
# =========================
def clean_input(q):
    q = q.lower()
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    q = re.sub(r"\s+", " ", q)
    return q.strip()

# =========================
# 🧠 EXTRACT GRADE
# =========================
def extract_grade(q):
    match = re.search(r"(\d+)", q)
    if match:
        g = int(match.group(1))
        if 1 <= g <= 12:
            return g
    return None

# =========================
# 🧠 EXTRACT TOPIC
# =========================
def extract_topic(q):
    q = clean_input(q)

    match = re.search(r"quiz on ([a-z\s]+)", q)
    topic = match.group(1) if match else q

    words = topic.split()
    words = [correct_spelling(w) for w in words]

    topic = " ".join(words)

    if len(topic) < 3:
        return "science"

    return topic.capitalize()

# =========================
# 🧠 MODE DETECTION
# =========================
def detect_mode(q):
    q = q.lower()

    if "only answers" in q:
        return "answers"

    if "answers" in q and "quiz" in q:
        return "both"

    if "answers" in q:
        return "answers"

    return "questions"

# =========================
# 🧠 QUIZ GENERATOR
# =========================
def generate_quiz(q):
    topic = extract_topic(q)
    grade = st.session_state.grade or 6
    mode = detect_mode(q)

    seed = random.randint(1, 10000)

    if mode == "questions":
        instruction = "DO NOT include answers."

    elif mode == "answers":
        instruction = "ONLY give answers like Q1: B"

    else:
        instruction = "Include both questions and answers."

    prompt = f"""
Create a HIGH-QUALITY 5-question MCQ quiz on {topic} for grade {grade} students.

Seed: {seed}

Rules:
- Clear MCQs
- A, B, C, D options
- Questions must NOT be generic
- Cover different concepts
- Avoid obvious textbook questions
- Each question must test understanding
- Use Q1, A), B), C), D)
- Keep it engaging and varied
{instruction}
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

    # save memory
    st.session_state.last_quiz_topic = topic
    st.session_state.last_quiz_text = text

    return f"🧠 Quiz on {topic}:\n{text}"

# =========================
# 🔥 FALLBACK
# =========================
def fallback_quiz(topic):
    return f"""Q1. {topic} belongs to which subject?
A) Math
B) Biology
C) History
D) Physics

Q2. Which is important in {topic}?
A) Air
B) Water
C) Light
D) All
"""

# =========================
# 🧠 ANSWERS
# =========================
def get_answers():
    text = st.session_state.last_quiz_text
    if not text:
        return "⚠️ No quiz yet."

    answers = [l for l in text.split("\n") if "Answer" in l]

    if not answers:
        return "⚠️ No stored answers."

    return "\n".join(answers)

# =========================
# 🤖 MAIN LOGIC
# =========================
def ai_answer(q):

    q_clean = clean_input(q)

    grade = extract_grade(q_clean)
    if grade:
        st.session_state.grade = grade
        return f"✅ Grade {grade} saved."

    if "answer" in q_clean:
        return get_answers()

    if "quiz" in q_clean:
        if st.session_state.grade is None:
            return "📚 Tell me your grade first."
        return generate_quiz(q_clean)

    return "🤖 Try asking for a quiz!"

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartLoop AI (Robust Mode)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)
    st.write("🤖", ai_answer(q))
