import streamlit as st
import re, math, os
import PyPDF2

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
# 📄 SMART PDF SEARCH
# =========================
def search_pdf(q):
    if not PDF_TEXT:
        return None

    words = q.split()

    best_match = None
    best_score = 0

    # scan chunks
    chunks = PDF_TEXT.split("\n")

    for chunk in chunks:
        score = sum(word in chunk for word in words)

        if score > best_score and len(chunk) > 50:
            best_score = score
            best_match = chunk

    if best_match:
        return "📄 From Books:\n" + best_match[:400]

    return None

# =========================
# 🤖 MAIN
# =========================
def ai(q):
    q = clean(q)

    # math first
    math_res = solve_math(q)
    if math_res:
        return math_res

    # 🔥 PDF SEARCH (MAIN BRAIN)
    pdf_res = search_pdf(q)
    if pdf_res:
        return pdf_res

    return "⚠️ Not found in books."

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot (All Books Mode)")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🤖 Thinking..."):
        ans = ai(q)

    st.write("🤖", ans)
