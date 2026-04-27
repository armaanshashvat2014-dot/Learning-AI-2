import streamlit as st
import re, math, os
import PyPDF2
import wikipedia
from google import genai
from openai import OpenAI
import itertools

# =========================
# 🎯 GRADE POPUP
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None

if st.session_state.grade is None:
    st.markdown("## 🎯 Select Your Grade")

    col1, col2 = st.columns([3,1])
    with col1:
        grade = st.selectbox("", ["Grade 6", "Grade 7", "Grade 8"])
    with col2:
        if st.button("OK"):
            st.session_state.grade = int(grade.split()[1])
            st.rerun()

    st.stop()

st.markdown(f"### 🎯 ACTIVE GRADE: Grade {st.session_state.grade}")

# =========================
# 📄 LOAD BOOKS (FAST + FILTERED)
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

        file_lower = file.lower()

        # Hindi exception
        if "hindi" in file_lower:
            if str(grade) not in file_lower:
                continue
        else:
            if not any(str(g) in file_lower for g in allowed):
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
# 🧠 UNDERSTANDING
# =========================
def clean(q):
    return q.lower().strip()

def detect_intent(q):
    if any(x in q for x in ["what is", "what are", "define", "laws"]):
        return "definition"
    if re.fullmatch(r"[0-9+\-*/().\s^]+", q):
        return "math"
    return "general"

def extract_topic(q):
    q = re.sub(r"what is|what are|define|meaning of|explain", "", q)
    return q.strip()

# =========================
# 📄 STRICT PDF SEARCH
# =========================
def search_pdf(topic):
    best = None
    best_score = 0

    for chunk in PDF_CHUNKS:

        # ❌ HARD BLOCK: questions & exercises
        if any(x in chunk for x in [
            "?", "student", "work out", "calculate",
            "find", "solve", "question", "exercise",
            "example:", "try", "complete"
        ]):
            continue

        # ❌ weak/broken text
        if len(chunk.split()) < 7:
            continue

        if topic not in chunk:
            continue

        score = 0

        # ✅ explanation style only
        if any(x in chunk for x in [" is ", " are ", " rule", " law", " means"]):
            score += 10

        score += chunk.count(topic) * 3

        if score > best_score:
            best_score = score
            best = chunk

    if best and best_score >= 10:
        return "📄 From Books:\n" + best[:300]

    return None

# =========================
# 📚 KNOWLEDGE (FALLBACK)
# =========================
KNOWLEDGE = {
    "laws of indices": (
        "The laws of indices are rules for working with powers:\n"
        "1. a^m × a^n = a^(m+n)\n"
        "2. a^m ÷ a^n = a^(m−n)\n"
        "3. (a^m)^n = a^(mn)\n"
        "4. a^0 = 1\n"
        "5. a^-n = 1/a^n"
    ),
    "indices": "Indices show how many times a number is multiplied by itself.",
    "decimals": "Decimals are numbers with a decimal point representing parts of a whole.",
}

# =========================
# 🌍 WIKIPEDIA
# =========================
def wiki_answer(topic):
    try:
        return "🌍 " + wikipedia.summary(topic, sentences=2)
    except:
        return None

# =========================
# 🤖 AI BACKUP
# =========================
GOOGLE_KEYS = [st.secrets.get("GOOGLE_API_KEY_1")]
OPENAI_KEYS = [st.secrets.get("OPENAI_API_KEY_1")]

google_cycle = itertools.cycle([k for k in GOOGLE_KEYS if k]) if GOOGLE_KEYS else None
openai_cycle = itertools.cycle([k for k in OPENAI_KEYS if k]) if OPENAI_KEYS else None

def api_answer(q):
    prompt = f"Explain simply:\n{q}"

    if google_cycle:
        try:
            c = genai.Client(api_key=next(google_cycle))
            r = c.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if r.text:
                return r.text
        except:
            pass

    if openai_cycle:
        try:
            c = OpenAI(api_key=next(openai_cycle))
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
        except:
            pass

    return None

# =========================
# 🤖 MAIN PIPELINE
# =========================
def ai(q):
    q = clean(q)
    intent = detect_intent(q)
    topic = extract_topic(q)

    # 1️⃣ PDF FIRST (STRICT)
    pdf_res = search_pdf(topic)
    if pdf_res:
        return pdf_res

    # 2️⃣ KNOWLEDGE
    for key in sorted(KNOWLEDGE, key=len, reverse=True):
        if key in topic:
            return f"📖 Definition:\n{KNOWLEDGE[key]}"

    # 3️⃣ WIKIPEDIA
    wiki_res = wiki_answer(topic)
    if wiki_res:
        return wiki_res

    # 4️⃣ AI
    api_res = api_answer(q)
    if api_res:
        return api_res

    return "⚠️ Couldn't find a clear answer."

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Clean + Accurate)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 Thinking..."):
        st.write("🤖", ai(q))
