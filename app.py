import streamlit as st
from PyPDF2 import PdfReader
import os
import re
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Clean • Smart • Offline")

# ===============================
# CACHE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ===============================
# CLEAN TEXT
# ===============================
def clean_text(t):
    t = t.lower()

    bad_phrases = [
        "how to use this book",
        "worked example",
        "let’s talk",
        "history of mathematics",
        "exercise",
        "questions",
        "give one criticism",
        "talk with a partner",
        "for each question",
        "diagram shows"
    ]

    for b in bad_phrases:
        if b in t:
            return None

    return t

# ===============================
# LOAD PDFS
# ===============================
@st.cache_resource
def load_pdfs():
    data = []
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader = PdfReader(f)
                subject = "math" if "math" in f.lower() else "general"

                for i, page in enumerate(reader.pages):
                    txt = page.extract_text()
                    if txt:
                        txt = clean_text(txt)
                        if not txt:
                            continue

                        parts = txt.split(". ")

                        for p in parts:
                            if len(p) > 50:
                                data.append({
                                    "text": p.strip(),
                                    "file": f,
                                    "page": i,
                                    "subject": subject
                                })
            except:
                pass
    return data

pages_db = load_pdfs()

# ===============================
# SEARCH PDF
# ===============================
def search_pdf(q, subject):
    words = set(q.lower().split())
    results = []

    for c in pages_db:
        if c["subject"] != subject:
            continue

        text = c["text"]
        score = sum(1 for w in words if w in text)

        if score > 2:
            results.append((score, c))

    results.sort(reverse=True, key=lambda x: x[0])
    return [r[1] for r in results[:3]]

# ===============================
# MATH (FIXED)
# ===============================
def is_calc(q):
    return bool(re.fullmatch(r"[0-9\.\+\-\*/\(\)\^\s]+", q.strip()))

def solve_math(q):
    try:
        q = q.replace("^", "**")  # 🔥 FIX exponent
        return str(eval(q.replace(" ", "")))
    except:
        return None

# ===============================
# KNOWLEDGE
# ===============================
knowledge = {
    "einstein": "Albert Einstein was a physicist known for developing the theory of relativity.",
    "what is gold": "Gold is a chemical element with symbol Au. It is a dense, soft metal used in jewelry and electronics.",
    "what is gravity": "Gravity is a force that attracts objects with mass.",
    "what are decimals": "Decimals are numbers written with a decimal point to represent fractions."
}

def get_knowledge(q):
    ql = q.lower()
    for k, v in knowledge.items():
        if k in ql:
            return v
    return None

# ===============================
# LOCAL ANSWER GENERATOR
# ===============================
def generate_local_answer(text, question):
    if not text:
        return None

    sentences = text.split(". ")
    q_words = set(question.lower().split())

    scored = []
    for s in sentences:
        score = sum(1 for w in q_words if w in s.lower())
        if score > 0:
            scored.append((score, s))

    scored.sort(reverse=True)
    best = [s for _, s in scored[:3]]

    if best:
        return " ".join(best)

    return sentences[0] if sentences else None

# ===============================
# WIKIPEDIA (CONTROLLED)
# ===============================
def wiki(q):
    try:
        return wikipedia.summary(q, sentences=2)
    except:
        return None

# ===============================
# SUBJECT DETECTION
# ===============================
def detect_subject(q):
    if is_calc(q):
        return "math"

    math_words = ["add", "subtract", "multiply", "divide", "fraction", "decimal"]
    if any(w in q.lower() for w in math_words):
        return "math"

    return "general"

# ===============================
# ANSWER ENGINE (FIXED)
# ===============================
def get_answer(q):

    try:
        if q in st.session_state.cache:
            return st.session_state.cache[q]

        # 1️⃣ math
        if is_calc(q):
            ans = solve_math(q)
            if ans:
                res = (f"🧮 {ans}", "Calculator")
                st.session_state.cache[q] = res
                return res

        # 2️⃣ knowledge
        k = get_knowledge(q)
        if k:
            res = (k, "📚 Knowledge")
            st.session_state.cache[q] = res
            return res

        subject = detect_subject(q)

        # 3️⃣ PDF (only for math)
        if subject == "math":
            chunks = search_pdf(q, subject)

            if chunks:
                combined = " ".join([c["text"] for c in chunks])
                ans = generate_local_answer(combined, q)

                if ans:
                    res = (ans, f"📖 {chunks[0]['file']}")
                    st.session_state.cache[q] = res
                    return res

        # 4️⃣ Wikipedia (NOT for math)
        if not is_calc(q):
            w = wiki(q)
            if w:
                res = (w, "🌐 Wikipedia")
                st.session_state.cache[q] = res
                return res

        # 5️⃣ fallback
        ans = generate_local_answer(q, q)

        if ans:
            res = (ans, "💡 Local")
        else:
            res = ("I couldn't find a clear answer.", "Fallback")

        st.session_state.cache[q] = res
        return res

    except Exception as e:
        return (f"⚠️ Error handled: {str(e)}", "System")

# ===============================
# UI
# ===============================
if "chat" not in st.session_state:
    st.session_state.chat = []

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.write(m["content"])

q = st.chat_input("Ask anything...")

if q:
    st.session_state.chat.append({"role": "user", "content": q})

    with st.chat_message("assistant"):
        ans, src = get_answer(q)
        st.write(ans)
        st.caption(src)

    st.session_state.chat.append({"role": "assistant", "content": ans})

# ===============================
# STATUS
# ===============================
st.write(f"📚 Loaded chunks: {len(pages_db)}")
