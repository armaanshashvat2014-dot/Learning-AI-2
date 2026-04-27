import streamlit as st
import re, math, os
import PyPDF2
import wikipedia

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
# 🧠 CLEAN
# =========================
def clean(q):
    return q.lower().strip()

# =========================
# 🧠 INTENT DETECTION
# =========================
def detect_intent(q):
    if any(x in q for x in ["what is", "what are", "define", "meaning"]):
        return "definition"

    if re.fullmatch(r"[0-9+\-*/().\s^]+", q):
        return "math"

    return "general"

# =========================
# 🎯 EXTRACT TOPIC
# =========================
def extract_topic(q):
    q = re.sub(r"what is|what are|define|meaning of|explain", "", q)
    return q.strip()

# =========================
# 📚 CORE KNOWLEDGE (EXPANDABLE)
# =========================
KNOWLEDGE = {
    # MATH
    "indices": "Indices (powers) show how many times a number is multiplied by itself. Example: 2³ = 8.",
    "decimals": "Decimals are numbers with a decimal point representing parts of a whole. Example: 0.5 = half.",
    "fractions": "Fractions represent parts of a whole. Example: 1/2 means one out of two equal parts.",
    "percentage": "A percentage means 'out of 100'. Example: 50% = 50/100 = 0.5.",
    "ratio": "A ratio compares two quantities. Example: 2:3.",
    "algebra": "Algebra uses symbols (like x) to represent numbers.",
    "equation": "An equation shows that two expressions are equal.",
    "perimeter": "Perimeter is the total distance around a shape.",
    "area": "Area is the space inside a shape.",
    "volume": "Volume is the space inside a 3D object.",

    # SCIENCE
    "photosynthesis": "Plants make food using sunlight, water, and carbon dioxide.",
    "cell": "A cell is the smallest unit of life.",
    "sound": "Sound is energy from vibrations that travels as waves.",
    "force": "Force is a push or pull.",
    "energy": "Energy is the ability to do work.",
    "gravity": "Gravity is the force that pulls objects toward Earth.",
    "friction": "Friction is a force that opposes motion.",
    "atom": "An atom is the smallest unit of matter.",
    "molecule": "A molecule is made of atoms bonded together.",
    "ecosystem": "An ecosystem is a community of living and non-living things.",

    # GENERAL
    "computer": "A computer is a machine that processes information.",
    "internet": "The internet is a global network connecting computers.",
    "data": "Data is information used for analysis or processing.",
}

# =========================
# 🧮 MATH
# =========================
def solve_math(q):
    try:
        q = q.replace("^", "**")
        result = eval(q, {"__builtins__": None}, {})
        return f"🧮 {q} = {result}"
    except:
        return None

# =========================
# 📄 PDF SEARCH (SECONDARY)
# =========================
def search_pdf(topic):
    best = None
    best_score = 0

    for chunk in PDF_CHUNKS:

        if any(x in chunk for x in [
            "match","fill","answer","exercise",
            "write","solve","complete"
        ]):
            continue

        if topic not in chunk:
            continue

        score = chunk.count(topic)

        if " is " in chunk or " are " in chunk:
            score += 3

        if score > best_score:
            best_score = score
            best = chunk

    if best:
        return "📄 From Books:\n" + best[:300]

    return None

# =========================
# 🌍 WIKIPEDIA FALLBACK (1000+ topics)
# =========================
def wiki_answer(topic):
    try:
        return "🌍 " + wikipedia.summary(topic, sentences=2)
    except:
        return None

# =========================
# 🤖 MAIN AI
# =========================
def ai(q):
    q = clean(q)
    intent = detect_intent(q)

    # math
    if intent == "math":
        res = solve_math(q)
        if res:
            return res

    topic = extract_topic(q)

    # core knowledge FIRST
    for key in KNOWLEDGE:
        if key in topic or topic in key:
            return f"📖 Definition:\n{KNOWLEDGE[key]}"

    # PDF
    pdf_res = search_pdf(topic)
    if pdf_res:
        return pdf_res

    # Wikipedia (infinite knowledge)
    wiki_res = wiki_answer(topic)
    if wiki_res:
        return wiki_res

    return "⚠️ I understand the question but couldn't find a clear answer."

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Real Understanding Mode)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 Thinking..."):
        answer = ai(q)

    st.write("🤖", answer)
