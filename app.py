import streamlit as st
import re, os, time, itertools
import PyPDF2
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
# 📄 LOAD BOOKS (FAST)
# =========================
@st.cache_data(show_spinner=False)
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
# 🔑 API KEYS (ROTATION)
# =========================
UNDERSTAND_KEYS = [
    st.secrets.get("OPENAI_API_KEY_1"),
    st.secrets.get("OPENAI_API_KEY_2"),
    st.secrets.get("OPENAI_API_KEY_3")
]

ANSWER_KEYS = [
    st.secrets.get("OPENAI_API_KEY_2"),
    st.secrets.get("OPENAI_API_KEY_3")
]

JUDGE_KEYS = [
    st.secrets.get("GOOGLE_API_KEY_1"),
    st.secrets.get("GOOGLE_API_KEY_2"),
    st.secrets.get("GOOGLE_API_KEY_3"),
    st.secrets.get("GOOGLE_API_KEY_4")
]

UNDERSTAND_KEYS = [k for k in UNDERSTAND_KEYS if k]
ANSWER_KEYS = [k for k in ANSWER_KEYS if k]
JUDGE_KEYS = [k for k in JUDGE_KEYS if k]

understand_cycle = itertools.cycle(UNDERSTAND_KEYS) if UNDERSTAND_KEYS else None
answer_cycle = itertools.cycle(ANSWER_KEYS) if ANSWER_KEYS else None
judge_cycle = itertools.cycle(JUDGE_KEYS) if JUDGE_KEYS else None

# =========================
# 🧠 FALLBACK UNDERSTAND
# =========================
def simple_understand(q):
    q = q.lower()

    topic = re.sub(r"what is|what are|define|explain|laws of", "", q).strip()

    if "law" in q or "what" in q:
        intent = "definition"
    elif re.fullmatch(r"[0-9+\-*/().\s^]+", q):
        intent = "math"
    else:
        intent = "general"

    return topic, intent

# =========================
# 🧠 UNDERSTAND (SAFE)
# =========================
@st.cache_data(show_spinner=False)
def understand(q):
    prompt = f"""
Extract clearly:
Topic:
Intent:

Question: {q}
"""

    for attempt in range(3):
        key = next(understand_cycle, None)
        if not key:
            break

        try:
            client = OpenAI(api_key=key)

            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )

            text = r.choices[0].message.content.lower()

            topic = text.split("topic:")[-1].split("\n")[0].strip()
            intent = text.split("intent:")[-1].strip()

            return topic, intent

        except Exception:
            time.sleep(1.5 * (attempt + 1))

    return simple_understand(q)

# =========================
# 🔍 GET PDF CANDIDATES
# =========================
def get_candidates(topic):
    return [c for c in PDF_CHUNKS if topic in c][:8]

# =========================
# 🔍 JUDGE CHUNK (AI)
# =========================
def judge_chunk(chunk, topic):
    key = next(judge_cycle, None)
    if not key:
        return False

    try:
        client = genai.Client(api_key=key)

        prompt = f"""
Topic: {topic}

Text:
{chunk}

Is this a GOOD explanation?

Reject if:
- question
- exercise
- incomplete

Answer ONLY: YES or NO
"""

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
    if not chunks:
        return []

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda c: (c, judge_chunk(c, topic)), chunks))

    return [c for c, ok in results if ok]

# =========================
# ✍️ GENERATE ANSWER
# =========================
def generate_answer(info, question):
    for _ in range(2):
        key = next(answer_cycle, None)
        if not key:
            break

        try:
            client = OpenAI(api_key=key)

            prompt = f"""
Explain clearly for a student:

Question: {question}

Use this info:
{info}

Give a clean explanation with examples.
"""

            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )

            return r.choices[0].message.content

        except:
            time.sleep(1)

    return "⚠️ Couldn't generate answer."

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
st.title("🧠 SmartBot (Stable Parallel AI)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 Thinking..."):
        st.write("🤖", ai(q))
