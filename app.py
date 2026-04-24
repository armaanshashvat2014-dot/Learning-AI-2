import streamlit as st
from PyPDF2 import PdfReader
import os, re, math, random

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Tutor • Quiz • Test • Teacher Mode")

# ===============================
# CACHE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ===============================
# MODE SELECTOR
# ===============================
mode = st.sidebar.selectbox(
    "Mode",
    ["Tutor Mode", "Quiz Mode", "Test Mode", "Teacher Mode"]
)

# ===============================
# CLEAN TEXT
# ===============================
def clean_text(t):
    t = t.lower()
    bad = ["exercise","worked example","history of mathematics","talk with"]
    for b in bad:
        if b in t:
            return None
    return t

# ===============================
# LOAD PDFS
# ===============================
@st.cache_resource
def load_pdfs():
    data=[]
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader=PdfReader(f)
                subject="math" if "math" in f.lower() else "general"

                for i,page in enumerate(reader.pages):
                    txt=page.extract_text()
                    if txt:
                        txt=clean_text(txt)
                        if not txt: continue

                        for p in txt.split(". "):
                            if len(p)>50:
                                data.append({
                                    "text":p,
                                    "file":f,
                                    "page":i,
                                    "subject":subject
                                })
            except:
                pass
    return data

pages_db = load_pdfs()

# ===============================
# QUERY EXPANSION
# ===============================
def expand_query(q):
    synonyms = {
        "indices": ["indices","powers","exponents"],
        "laws": ["laws","rules"]
    }
    words = q.lower().split()
    expanded = words.copy()

    for w in words:
        if w in synonyms:
            expanded.extend(synonyms[w])

    return " ".join(expanded)

# ===============================
# SEARCH PDF (SMART)
# ===============================
def search_pdf(q):
    ql = expand_query(q)
    results = []

    for c in pages_db:
        text = c["text"]

        score = 0

        if ql in text:
            score += 10

        for w in ql.split():
            if w in text:
                score += 1

        if score > 0:
            results.append((score, c))

    results.sort(reverse=True, key=lambda x: x[0])
    return [r[1] for r in results[:5]]

# ===============================
# MATH PARSER
# ===============================
def parse_math(q):
    q=q.lower()
    q=q.replace("plus","+").replace("add","+")
    q=q.replace("minus","-").replace("subtract","-")
    q=q.replace("times","*").replace("multiply","*")
    q=q.replace("divide","/").replace("divided by","/")
    q=q.replace("^","**")

    q=re.sub(r"square root of (\d+)", r"math.sqrt(\1)", q)
    q=re.sub(r"cube root of (\d+)", r"(\1)**(1/3)", q)

    return q

def is_calc(q):
    return any(w in q.lower() for w in ["+","-","*","/","root","square","cube","add","subtract"])

def solve_math(q):
    try:
        q=parse_math(q)
        return str(eval(q))
    except:
        return None

# ===============================
# KNOWLEDGE
# ===============================
knowledge={
    "indices":"Indices are powers showing repeated multiplication. Example: 2^3 = 2×2×2.",
    "laws of indices":"a^m × a^n = a^(m+n), a^m ÷ a^n = a^(m−n), (a^m)^n = a^(mn).",
    "algebra":"Algebra uses symbols like x to represent unknown values."
}

def get_knowledge(q):
    for k,v in knowledge.items():
        if k in q.lower():
            return v
    return None

# ===============================
# LOCAL ANSWER
# ===============================
def local_answer(chunks,q):
    combined="\n".join([c["text"] for c in chunks])
    sentences=combined.split(". ")
    return ". ".join(sentences[:3])

# ===============================
# QUIZ GENERATOR
# ===============================
def generate_quiz(topic):
    if "indices" in topic.lower():
        return [
            "Simplify: 2^3 × 2^4",
            "Simplify: 5^6 ÷ 5^2",
            "Work out: (3^2)^3",
            "What is 10^0?"
        ]
    return [
        "45 + 67",
        "120 − 89",
        "8 × 7",
        "144 ÷ 12"
    ]

# ===============================
# TEST MODE
# ===============================
if mode == "Test Mode":
    topic = st.text_input("Enter topic")
    if st.button("Start Test"):
        qs = generate_quiz(topic)
        score = 0

        for q in qs:
            ans = st.text_input(q)
            correct = solve_math(q) if is_calc(q) else None

            if ans and correct and ans.strip() == correct:
                score += 1

        st.write(f"Score: {score}/{len(qs)}")

# ===============================
# QUIZ MODE
# ===============================
elif mode == "Quiz Mode":
    topic = st.text_input("Enter topic")
    if topic:
        qs = generate_quiz(topic)
        for q in qs:
            st.write("•", q)

# ===============================
# TUTOR MODE
# ===============================
def get_answer(q):

    if q in st.session_state.cache:
        return st.session_state.cache[q]

    # math
    if is_calc(q):
        ans = solve_math(q)
        if ans:
            res = (f"🧮 {ans}", "Calculator")
            st.session_state.cache[q]=res
            return res

    # knowledge
    k=get_knowledge(q)
    if k:
        res=(k,"📚 Knowledge")
        st.session_state.cache[q]=res
        return res

    # pdf
    chunks=search_pdf(q)
    if chunks:
        res=(local_answer(chunks,q),f"📖 {chunks[0]['file']}")
        st.session_state.cache[q]=res
        return res

    return ("I couldn't find a clear answer.","Fallback")

# ===============================
# TEACHER MODE (INTEGRATED)
# ===============================
elif mode == "Teacher Mode":
    st.write("👨‍🏫 Teacher Mode Active")

    q = st.text_input("Ask or give topic")

    if q:
        ans,src = get_answer(q)
        st.write("### Explanation")
        st.write(ans)
        st.caption(src)

        st.write("### Practice")
        for qq in generate_quiz(q):
            st.write("-", qq)

# ===============================
# TUTOR MODE UI
# ===============================
if mode == "Tutor Mode":
    if "chat" not in st.session_state:
        st.session_state.chat=[]

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    q=st.chat_input("Ask anything...")

    if q:
        st.session_state.chat.append({"role":"user","content":q})

        with st.chat_message("assistant"):
            ans,src=get_answer(q)
            st.write(ans)
            st.caption(src)

        st.session_state.chat.append({"role":"assistant","content":ans})

# ===============================
# STATUS
# ===============================
st.write(f"📚 Loaded chunks: {len(pages_db)}")
