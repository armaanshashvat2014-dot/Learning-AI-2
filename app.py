import streamlit as st
from PyPDF2 import PdfReader
import os, re
import wikipedia
import sympy as sp
from sympy import sympify

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("📚 Learns from textbooks • Solves math • Explains clearly")

# ===============================
# CLEAN TEXT
# ===============================
def clean_text(text):
    text = text.lower()

    bad = ["indb","chapter","exercise","©","http","youtube"]
    if any(b in text for b in bad):
        return None

    text = re.sub(r'[^a-z0-9\s\.\-]', '', text)
    return text.strip()

# ===============================
# BUILD KNOWLEDGE FROM PDF
# ===============================
@st.cache_resource
def build_knowledge():
    kb = []

    for file in os.listdir("."):
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(file)

                for page in reader.pages:
                    text = page.extract_text()

                    if text:
                        text = clean_text(text)
                        if not text:
                            continue

                        sentences = text.split(". ")

                        for s in sentences:
                            if 40 < len(s) < 200:
                                kb.append({
                                    "text": s,
                                    "source": file
                                })

            except:
                pass

    return kb

knowledge_db = build_knowledge()

# ===============================
# SEARCH KNOWLEDGE
# ===============================
def search_knowledge(query):
    query = query.lower()
    q_words = query.split()

    results = []

    for item in knowledge_db:
        text = item["text"]

        score = 0

        for w in q_words:
            if w in text:
                score += 2

        if query in text:
            score += 5

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in results[:3]]

# ===============================
# MATH ENGINE
# ===============================
def parse_math(q):
    q = q.lower()

    q = q.replace("plus","add","+")
    q = q.replace("minus","remove","-")
    q = q.replace("times","x","*")
    q = q.replace("multiply","*","x")
    q = q.replace("divide","/")
    q = q.replace("^","**")

    q = re.sub(r"square (\d+)", r"(\1**2)", q)
    q = re.sub(r"cube (\d+)", r"(\1**3)", q)

    return q

def solve_math(q):
    try:
        expr = parse_math(q)
        result = sympify(expr)
        return str(result)
    except:
        return None

def is_math(q):
    return bool(re.search(r"[0-9\+\-\*/\^]", q)) or any(
        w in q.lower() for w in ["plus","minus","square","divide","times"]
    )

# ===============================
# EXPLAIN
# ===============================
def explain(text):
    return f"""
📘 Explanation:
{text}

💡 Simple:
{text.split('.')[0]}.

🧠 Tip:
Understand the concept, not memorize blindly.
"""

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q):

    # 1️⃣ MATH FIRST
    if is_math(q):
        ans = solve_math(q)
        if ans:
            return (f"🧮 Answer: {ans}", "Calculator")

    # 2️⃣ TEXTBOOK KNOWLEDGE
    results = search_knowledge(q)

    if results:
        return (explain(results[0]["text"]), f"📖 {results[0]['source']}")

    # 3️⃣ WIKIPEDIA
    try:
        return (explain(wikipedia.summary(q, 2)), "🌐 Wikipedia")
    except:
        pass

    return ("I couldn't find a clear answer.", "Fallback")

# ===============================
# UI
# ===============================
st.subheader("💬 Ask Your Doubt")

q = st.text_input("Enter your question")

if q:
    ans, src = get_answer(q)
    st.write(ans)
    st.caption(src)

# ===============================
# STATUS
# ===============================
st.write(f"📚 Learned concepts: {len(knowledge_db)}")
