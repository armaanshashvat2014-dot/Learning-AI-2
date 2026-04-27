import streamlit as st
import re, math, os
import PyPDF2
import wikipedia

# =========================
# 📄 LOAD ALL PDFs
# =========================
@st.cache_data
def load_all_pdfs():
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

PDF_TEXT = load_all_pdfs()

# =========================
# 🧠 CLEAN INPUT
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
# 📄 SMART PDF SEARCH
# =========================
def search_pdf(q):
    if not PDF_TEXT:
        return None

    # remove useless words
    stopwords = {
        "what","is","are","the","a","an","of","in","on",
        "for","to","and","explain","define"
    }

    words = [w for w in q.lower().split() if w not in stopwords]

    if not words:
        return None

    chunks = PDF_TEXT.split("\n")

    best_match = None
    best_score = 0

    for chunk in chunks:
        if len(chunk) < 40:
            continue

        score = 0

        for word in words:
            if word in chunk:
                score += 3

        # prefer definition-style sentences
        if any(x in chunk for x in [" is ", " are ", " means ", " refers to "]):
            score += 2

        if score > best_score:
            best_score = score
            best_match = chunk

    if best_match:
        return "📄 From Books:\n" + best_match[:400]

    return None

# =========================
# 🌍 WIKIPEDIA (OPTIONAL)
# =========================
def wiki_answer(q):
    try:
        return "🌍 " + wikipedia.summary(q, sentences=2)
    except:
        return None

# =========================
# 🤖 MAIN AI
# =========================
def ai(q):
    q = clean(q)

    # math first
    math_res = solve_math(q)
    if math_res:
        return math_res

    # PDF search
    pdf_res = search_pdf(q)
    if pdf_res:
        return pdf_res

    # Wikipedia fallback
    wiki_res = wiki_answer(q)
    if wiki_res:
        return wiki_res

    return "⚠️ I couldn't find a clear answer."

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (All Books + Smart Search)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🤖 Thinking..."):
        answer = ai(q)

    st.write("🤖", answer)
