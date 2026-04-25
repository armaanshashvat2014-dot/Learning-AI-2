import streamlit as st
from PyPDF2 import PdfReader
import os, re
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("✅ Stable • Predictable • No nonsense")

# ===============================
# NORMALIZATION (LANGUAGE UNDERSTANDING)
# ===============================
def normalize(q):
    q = q.lower()

    mapping = {
        "indices": "exponents",
        "index": "exponent",
        "powers": "exponents",
        "maths": "math",
        "multiplication": "*",
        "division": "/"
    }

    for k, v in mapping.items():
        q = q.replace(k, v)

    return q


# ===============================
# CORE KNOWLEDGE (NEVER FAIL)
# ===============================
def core_knowledge(q):
    q = normalize(q)

    if "exponent" in q:
        return """Indices (exponents) show repeated multiplication.

Example:
2^3 = 2 × 2 × 2 = 8

Laws:
a^m × a^n = a^(m+n)
a^m ÷ a^n = a^(m−n)
(a^m)^n = a^(mn)
"""

    if "fraction" in q:
        return """A fraction represents a part of a whole.

Example:
1/2 means one out of two equal parts.

1/2 + 1/4 = 3/4
"""

    if "decimal" in q:
        return """Decimals are numbers with a decimal point.

Example:
0.5 = 1/2
"""

    return None


# ===============================
# MATH SOLVER (SAFE)
# ===============================
def parse_math(q):
    q = q.lower()

    q = q.replace("plus","+")
    q = q.replace("minus","-")
    q = q.replace("times","*")
    q = q.replace("multiply","*")
    q = q.replace("divide","/")
    q = q.replace("^","**")

    q = re.sub(r"square (\d+)", r"(\1**2)", q)
    q = re.sub(r"cube (\d+)", r"(\1**3)", q)

    return q

def is_math(q):
    return bool(re.search(r"[0-9\+\-\*/\^]", q))

def solve_math(q):
    try:
        expr = parse_math(q)
        return str(eval(expr, {"__builtins__": None}, {}))
    except:
        return None


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
# LOAD TEXTBOOK
# ===============================
@st.cache_resource
def load_kb():
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

                        for line in text.split(". "):
                            if 40 < len(line) < 200:
                                kb.append({
                                    "text": line,
                                    "source": file
                                })

            except:
                pass

    return kb

knowledge_db = load_kb()


# ===============================
# SEARCH ENGINE
# ===============================
def search_kb(query):
    query = normalize(query)
    words = query.split()

    results = []

    for item in knowledge_db:
        text = item["text"]

        score = 0

        for w in words:
            if w in text:
                score += 2

        if query in text:
            score += 5

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in results[:3]]


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
Focus on understanding.
"""


# ===============================
# MAIN ENGINE
# ===============================
def get_answer(q):

    # 1️⃣ CORE KNOWLEDGE (never fail topics)
    core = core_knowledge(q)
    if core:
        return (explain(core), "📚 Core Knowledge")

    # 2️⃣ MATH
    if is_math(q):
        ans = solve_math(q)
        if ans:
            return (f"🧮 Answer: {ans}", "Calculator")

    # 3️⃣ TEXTBOOK
    results = search_kb(q)
    if results:
        return (explain(results[0]["text"]), f"📖 {results[0]['source']}")

    # 4️⃣ WIKIPEDIA
    try:
        return (explain(wikipedia.summary(q, 2)), "🌐 Wikipedia")
    except:
        pass

    # 5️⃣ FINAL
    return ("I couldn't find a clear answer. Try being more specific.", "Fallback")


# ===============================
# UI
# ===============================
st.subheader("💬 Ask Your Doubt")

q = st.text_input("Enter your question")

if q:
    ans, src = get_answer(q)
    st.write(ans)
    st.caption(src)

st.write(f"📚 Learned concepts: {len(knowledge_db)}")
