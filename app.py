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

# =========================
# 🎯 SHOW ACTIVE GRADE
# =========================
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
# 🧮 MATH
# =========================
def solve_math(q):
    try:
        if re.fullmatch(r"[0-9+\-*/().\s^]+", q):
            q = q.replace("^", "**")
            result = eval(q, {"__builtins__": None}, {})
            return f"🧮 {q} = {result}"
    except:
        pass
    return None

# =========================
# 📖 SMART SEARCH (FINAL FIX)
# =========================
def defining(q):
    keywords = [w for w in q.split() if len(w) > 3]

    best = None
    best_score = 0

    for chunk in PDF_CHUNKS:

        # skip exercises
        if any(x in chunk for x in [
            "match","fill","answer","exercise",
            "write","solve","complete"
        ]):
            continue

        # reject broken OCR
        if len(chunk.split()) < 6:
            continue
        if chunk.count(" ") < 5:
            continue

        # must contain keyword
        if not any(k in chunk for k in keywords):
            continue

        score = 0

        for k in keywords:
            if k in chunk:
                score += 3

        # strong definition
        if chunk.startswith(("a decimal", "decimals are", "decimal numbers are")):
            score += 10

        if any(x in chunk for x in [" is ", " are ", " means "]):
            score += 5

        # reject nonsense
        if "what is the" in chunk and "?" not in chunk:
            continue

        if score > best_score:
            best_score = score
            best = chunk

    if best:
        return "📖 Definition:\n" + best[:400]

    return None

# =========================
# 🔁 FALLBACK
# =========================
def fallback(q):
    if "decimal" in q:
        return ("📖 Definition:\n"
                "Decimals are numbers that contain a decimal point. "
                "They represent parts of a whole.\n\n"
                "Example:\n0.5 = half\n1.25 = one and twenty-five hundredths.")
    return "⚠️ I couldn’t find a clear definition."

# =========================
# 🤖 MAIN
# =========================
def ai(q):
    q = clean(q)

    math_res = solve_math(q)
    if math_res:
        return math_res

    def_res = defining(q)
    if def_res:
        return def_res

    return fallback(q)

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Grade-Aware Learning)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 Thinking..."):
        answer = ai(q)

    st.write("🤖", answer)
