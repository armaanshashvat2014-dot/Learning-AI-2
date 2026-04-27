import streamlit as st
import re, math, os
import PyPDF2

# =========================
# 📄 LEARNING: LOAD BOOKS
# =========================
@st.cache_data
def learning_books():
    text = ""

    for file in os.listdir():
        if file.endswith(".pdf"):
            try:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += (page.extract_text() or "") + "\n"
            except:
                continue

    return text.lower()

PDF_TEXT = learning_books()

# =========================
# 🧠 UNDERSTANDING INPUT
# =========================
def clean(q):
    return q.lower().strip()

# =========================
# 🧮 SIMPLIFYING (MATH)
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
# 📖 DEFINING (SMART SEARCH)
# =========================
def defining(q):
    if not PDF_TEXT:
        return None

    stopwords = {
        "what","is","are","the","a","an","of","in","on",
        "for","to","and","explain","define"
    }

    keywords = [w for w in q.split() if w not in stopwords]

    chunks = PDF_TEXT.split("\n")

    best = None
    best_score = 0

    for chunk in chunks:
        if len(chunk) < 50:
            continue

        # ❌ ignore exercise/instruction lines
        if any(x in chunk for x in [
            "match", "fill", "answer", "exercise",
            "write", "solve", "complete"
        ]):
            continue

        score = 0

        # keyword match
        for word in keywords:
            if word in chunk:
                score += 3

        # 🔥 strong preference for definitions
        if any(x in chunk for x in [
            " is ", " are ", " means ", " refers to "
        ]):
            score += 5

        if score > best_score:
            best_score = score
            best = chunk

    if best:
        return "📖 Definition:\n" + best[:400]

    return None

# =========================
# 🔁 RETESTING (FALLBACK)
# =========================
def fallback(q):
    if "decimal" in q:
        return ("Decimals are numbers that include a decimal point.\n\n"
                "Example:\n0.5 means half\n1.25 means one and twenty-five hundredths.")

    return "⚠️ I couldn’t find a clear definition."

# =========================
# 🤖 MAIN
# =========================
def ai(q):
    q = clean(q)

    # simplifying
    math_res = solve_math(q)
    if math_res:
        return math_res

    # defining
    def_res = defining(q)
    if def_res:
        return def_res

    # retesting fallback
    return fallback(q)

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (Learning Mode)")

q = st.text_input("Ask anything... Know everything")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 thinking..."):
        answer = ai(q)

    st.write("🤖", answer)
