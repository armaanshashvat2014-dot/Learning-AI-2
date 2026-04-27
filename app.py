import streamlit as st
import re, math, os
import PyPDF2

# =========================
# 🎯 GRADE POPUP
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None

if st.session_state.grade is None:
    st.markdown("## 🎯 ACTIVE GRADE")

    col1, col2 = st.columns([3,1])
    with col1:
        grade = st.selectbox("", ["Grade 6", "Grade 7", "Grade 8"])
    with col2:
        if st.button("▼"):
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
# 🧠 CLEAN
# =========================
def clean(q):
    return q.lower().strip()

# =========================
# 🧠 UNDERSTAND INTENT
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
# 📖 TRUSTED KNOWLEDGE
# =========================
KNOWLEDGE = {
    "decimals": "Decimals are numbers that contain a decimal point. They represent parts of a whole.\nExample: 0.5 = half, 1.25 = one and twenty-five hundredths.",
    "fractions": "Fractions represent parts of a whole. Example: 1/2 means one out of two equal parts.",
    "photosynthesis": "Photosynthesis is the process by which plants make food using sunlight, water, and carbon dioxide.",
    "cell": "A cell is the smallest unit of life. All living things are made of cells.",
    "sound": "Sound is a form of energy produced by vibrations and travels in waves."
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
# 📄 SAFE PDF SEARCH (ONLY SUPPORT)
# =========================
def search_pdf(topic):
    best = None
    best_score = 0

    for chunk in PDF_CHUNKS:

        # skip junk
        if any(x in chunk for x in [
            "match","fill","answer","exercise",
            "write","solve","complete"
        ]):
            continue

        if len(chunk.split()) < 6:
            continue

        if topic not in chunk:
            continue

        score = 0

        if " is " in chunk or " are " in chunk:
            score += 5

        score += chunk.count(topic) * 3

        if score > best_score:
            best_score = score
            best = chunk

    if best:
        return "📄 From Books:\n" + best[:300]

    return None

# =========================
# 🤖 MAIN AI
# =========================
def ai(q):
    q = clean(q)

    intent = detect_intent(q)

    # 🧮 math
    if intent == "math":
        res = solve_math(q)
        if res:
            return res

    topic = extract_topic(q)

    # 📖 trusted definitions FIRST
    for key in KNOWLEDGE:
        if key in topic:
            return f"📖 Definition:\n{KNOWLEDGE[key]}"

    # 📄 PDF (secondary)
    pdf_res = search_pdf(topic)
    if pdf_res:
        return pdf_res

    return "⚠️ I understand your question, but I couldn't find a clear answer."

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Actually Understands)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 Thinking..."):
        answer = ai(q)

    st.write("🤖", answer)
