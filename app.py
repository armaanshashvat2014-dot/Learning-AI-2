import streamlit as st
import re, os
import PyPDF2
import itertools
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from google import genai

# =========================
# 🎯 GRADE POPUP
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None

if st.session_state.grade is None:
    grade = st.selectbox("Select Grade", ["Grade 6","Grade 7","Grade 8"])
    if st.button("OK"):
        st.session_state.grade = int(grade.split()[1])
        st.rerun()
    st.stop()

st.write(f"🎯 Grade {st.session_state.grade}")

# =========================
# 📄 LOAD BOOKS
# =========================
@st.cache_data
def load_books(grade):
    chunks = []

    allowed = [grade]
    if grade == 6:
        allowed += [7]
    elif grade == 7:
        allowed += [8]
    elif grade == 8:
        allowed += [9]

    for file in os.listdir():
        if not file.endswith(".pdf"):
            continue

        name = file.lower()

        if "hindi" in name:
            if str(grade) not in name:
                continue
        else:
            if not any(str(g) in name for g in allowed):
                continue

        try:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    line = line.strip().lower()
                    if len(line) > 40:
                        chunks.append(line)
        except:
            continue

    return chunks

PDF_CHUNKS = load_books(st.session_state.grade)

# =========================
# 🔑 API SETUP
# =========================
UNDERSTAND_KEY = st.secrets["OPENAI_API_KEY_1"]

PDF_JUDGE_KEYS = [
    st.secrets["GOOGLE_API_KEY_1"],
    st.secrets["GOOGLE_API_KEY_2"],
    st.secrets["GOOGLE_API_KEY_3"],
    st.secrets["GOOGLE_API_KEY_4"]
]

ANSWER_KEYS = [
    st.secrets["OPENAI_API_KEY_2"],
    st.secrets["OPENAI_API_KEY_3"]
]

judge_cycle = itertools.cycle(PDF_JUDGE_KEYS)
answer_cycle = itertools.cycle(ANSWER_KEYS)

# =========================
# 🧠 UNDERSTAND
# =========================
def understand(q):
    client = OpenAI(api_key=UNDERSTAND_KEY)

    prompt = f"""
Extract clearly:
Topic:
Intent:

Question: {q}
"""

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    text = r.choices[0].message.content.lower()

    topic = text.split("topic:")[-1].split("\n")[0].strip()
    intent = text.split("intent:")[-1].strip()

    return topic, intent

# =========================
# 🔍 GET CANDIDATES
# =========================
def get_candidates(topic):
    return [c for c in PDF_CHUNKS if topic in c][:8]

# =========================
# 🔍 JUDGE CHUNK
# =========================
def judge_chunk(chunk, topic):
    key = next(judge_cycle)
    client = genai.Client(api_key=key)

    prompt = f"""
Topic: {topic}

Text:
{chunk}

Is this a GOOD explanation of the topic?

Reject if:
- question
- exercise
- incomplete
- vague

Answer ONLY: YES or NO
"""

    try:
        r = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return "YES" in r.text.upper()
    except:
        return False

# =========================
# ⚡ PARALLEL FILTER
# =========================
def filter_chunks_parallel(chunks, topic):
    good = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda c: (c, judge_chunk(c, topic)), chunks))

    for chunk, is_good in results:
        if is_good:
            good.append(chunk)

    return good

# =========================
# ✍️ GENERATE ANSWER
# =========================
def generate_answer(info, question):
    key = next(answer_cycle)
    client = OpenAI(api_key=key)

    prompt = f"""
Explain clearly for a student:

Question: {question}

Use:
{info}

Give proper explanation with examples.
"""

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return r.choices[0].message.content

# =========================
# 🤖 MAIN PIPELINE
# =========================
def ai(q):

    topic, intent = understand(q)

    candidates = get_candidates(topic)

    good_chunks = filter_chunks_parallel(candidates, topic)

    if not good_chunks:
        return "⚠️ No good explanation found."

    return generate_answer("\n".join(good_chunks), q)

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Parallel AI System)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 Thinking..."):
        st.write("🤖", ai(q))
