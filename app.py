import streamlit as st
from PyPDF2 import PdfReader
import os, re, math
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Clean • Smart • Stable")

# ===============================
# STATE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ===============================
# MODE
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

    bad = [
        "indb","contents","chapter","section","©",
        "youtube","http","exercise","worked example",
        "talk with","978"
    ]

    for b in bad:
        if b in t:
            return None

    # remove non-English junk
    if not re.match(r'^[a-z0-9\s\.\,\-\+\*/\(\)]+$', t):
        return None

    return t.strip()

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
                for i,page in enumerate(reader.pages):
                    txt=page.extract_text()
                    if txt:
                        txt=clean_text(txt)
                        if not txt: continue

                        for p in txt.split(". "):
                            if len(p)>60:
                                data.append({
                                    "text":p,
                                    "file":f,
                                    "page":i
                                })
            except:
                pass
    return data

pages_db = load_pdfs()

# ===============================
# SEARCH PDF
# ===============================
def search_pdf(q):
    ql=q.lower()
    results=[]

    for c in pages_db:
        text=c["text"]
        score=0

        if ql in text:
            score+=10

        for w in ql.split():
            if w in text:
                score+=1

        if score>0:
            results.append((score,c))

    results.sort(reverse=True)
    return [r[1] for r in results[:5]]

# ===============================
# MATH PARSER
# ===============================
def parse_math(q):
    q = q.lower()

    q = q.replace("plus","+").replace("add","+")
    q = q.replace("minus","-").replace("subtract","-")
    q = q.replace("times","*").replace("multiply","*")
    q = q.replace("divide","/").replace("divided by","/")
    q = q.replace("^","**")

    # square & cube
    q = re.sub(r"square of (\d+)", r"(\1**2)", q)
    q = re.sub(r"square (\d+)", r"(\1**2)", q)
    q = re.sub(r"cube of (\d+)", r"(\1**3)", q)
    q = re.sub(r"cube (\d+)", r"(\1**3)", q)

    # roots
    q = re.sub(r"square root of (\d+)", r"math.sqrt(\1)", q)
    q = re.sub(r"cube root of (\d+)", r"(\1)**(1/3)", q)

    return q

def is_calc(q):
    q=q.lower()
    return (
        bool(re.fullmatch(r"[0-9\.\+\-\*/\(\)\^\s]+", q.strip()))
        or any(word in q for word in [
            "add","subtract","multiply","divide",
            "square","cube","root","plus","minus"
        ])
    )

def solve_math(q):
    try:
        q=parse_math(q)
        return str(eval(q))
    except:
        return None

# ===============================
# KNOWLEDGE
# ===============================
knowledge = {
    "integer":"An integer is a whole number. It can be positive, negative, or zero. Example: -3, 0, 5.",
    "fractions":"""Fractions represent parts of a whole.

Example:
1/2 means one part out of two equal parts.

Types:
- Proper: 1/2
- Improper: 5/3
- Mixed: 1 2/3

Example operations:
1/2 + 1/4 = 3/4
""",
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
def local_answer(chunks):
    text = " ".join([c["text"] for c in chunks])
    sentences = [s for s in text.split(". ") if len(s)<200]
    return ". ".join(sentences[:2])

# ===============================
# WIKIPEDIA SAFE
# ===============================
def safe_wiki(q):
    try:
        return wikipedia.summary(q, sentences=2)
    except:
        return None

# ===============================
# QUIZ
# ===============================
def generate_quiz(topic):
    topic=topic.lower()

    if "fraction" in topic:
        return [
            "1/2 + 1/4",
            "3/4 - 1/2",
            "2/3 * 3/5",
            "5/6 / 1/2"
        ]

    if "indices" in topic:
        return [
            "2^3 × 2^4",
            "5^6 ÷ 5^2",
            "(3^2)^3",
            "10^0"
        ]

    return [
        "45 + 67",
        "120 - 89",
        "8 * 7",
        "144 / 12"
    ]

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q):

    if q in st.session_state.cache:
        return st.session_state.cache[q]

    # math
    if is_calc(q):
        ans=solve_math(q)
        if ans:
            res=(f"🧮 {ans}","Calculator")
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
    if chunks and len(chunks[0]["text"])>80:
        res=(local_answer(chunks),f"📖 {chunks[0]['file']}")
        st.session_state.cache[q]=res
        return res

    # wiki (not math)
    if not is_calc(q):
        w=safe_wiki(q)
        if w:
            res=(w,"🌐 Wikipedia")
            st.session_state.cache[q]=res
            return res

    return ("I couldn't find a clear answer.","Fallback")

# ===============================
# MODES
# ===============================

# TEST
if mode == "Test Mode":
    st.subheader("🧪 Test Mode")

    if "test_started" not in st.session_state:
        st.session_state.test_started=False

    topic=st.text_input("Enter topic")

    if st.button("Start Test"):
        st.session_state.test_started=True
        st.session_state.questions=generate_quiz(topic)
        st.session_state.answers=[""]*len(st.session_state.questions)

    if st.session_state.test_started:
        for i,q in enumerate(st.session_state.questions):
            st.session_state.answers[i]=st.text_input(q,key=f"q{i}")

        if st.button("Submit"):
            score=0
            for i,q in enumerate(st.session_state.questions):
                correct=solve_math(q)
                if correct and st.session_state.answers[i].strip()==correct:
                    score+=1

            st.success(f"Score: {score}/{len(st.session_state.questions)}")

# QUIZ
elif mode == "Quiz Mode":
    st.subheader("📝 Quiz Mode")
    topic=st.text_input("Enter topic")
    if topic:
        for q in generate_quiz(topic):
            st.write("•",q)

# TEACHER
elif mode == "Teacher Mode":
    st.subheader("👨‍🏫 Teacher Mode")
    topic=st.text_input("Enter topic")

    if topic:
        ans,src=get_answer(topic)

        st.write("### 📘 Explanation")
        st.write(ans)
        st.caption(src)

        st.write("### 📝 Practice")
        for q in generate_quiz(topic):
            st.write("-",q)

# TUTOR
elif mode == "Tutor Mode":
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

# STATUS
st.write(f"📚 Loaded chunks: {len(pages_db)}")
