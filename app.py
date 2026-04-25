import streamlit as st
from PyPDF2 import PdfReader
import os, re, math, random
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Accurate • Topic-Aware • Fast")

# ===============================
# STATE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ===============================
# SUBJECT + MODE
# ===============================
subject = st.sidebar.selectbox(
    "Select Subject",
    ["Math","Physics","Chemistry","Biology","English","Hindi","General"]
)

mode = st.sidebar.selectbox(
    "Mode",
    ["Tutor Mode","Quiz Mode","Test Mode","Teacher Mode"]
)

# ===============================
# CLEAN PDF
# ===============================
def clean_text(t):
    t = t.lower()
    if any(x in t for x in ["indb","chapter","exercise","http","©"]):
        return None
    return t

@st.cache_resource
def load_pdfs():
    data=[]
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            sub="general"
            if "math" in f.lower(): sub="math"

            try:
                reader=PdfReader(f)
                for page in reader.pages:
                    txt=page.extract_text()
                    if txt:
                        txt=clean_text(txt)
                        if txt:
                            data.append({"text":txt,"file":f,"subject":sub})
            except:
                pass
    return data

pages_db = load_pdfs()

# ===============================
# RELEVANCE CHECK
# ===============================
def is_relevant(text, query):
    text=text.lower()
    words=query.lower().split()
    matches=sum(1 for w in words if w in text)
    return matches >= 2

# ===============================
# SEARCH PDF
# ===============================
def search_pdf(q, subject):
    results=[]
    for c in pages_db:
        if subject.lower()!="general" and c["subject"]!=subject.lower():
            continue

        score=sum(1 for w in q.lower().split() if w in c["text"])
        if score>0:
            results.append((score,c))

    results.sort(key=lambda x:x[0], reverse=True)
    return [r[1] for r in results[:2]]

# ===============================
# MATH SOLVER
# ===============================
def parse_math(q):
    q=q.lower()
    q=q.replace("^","**")
    q=q.replace("plus","+").replace("minus","-")
    q=q.replace("times","*").replace("divide","/")
    return q

def solve_math(q):
    try:
        return str(eval(parse_math(q)))
    except:
        return None

# ===============================
# KNOWLEDGE BASE
# ===============================
knowledge = {
    "fractions": """Fractions represent parts of a whole.

Example:
1/2 means 1 part out of 2 equal parts.

Types:
- Proper fractions
- Improper fractions
- Mixed numbers

Example:
1/2 + 1/4 = 3/4""",

    "decimals": "Decimals are numbers with a decimal point. Example: 0.5 = 1/2.",

    "gravity": "Gravity is a force that attracts objects towards Earth.",
    "atom": "An atom is the smallest unit of matter.",
    "cell": "A cell is the basic unit of life."
}

def get_knowledge(q):
    for k,v in knowledge.items():
        if k in q.lower():
            return v
    return None

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
Understand the concept, not just memorize it.
"""

# ===============================
# TOPIC DETECTION
# ===============================
def detect_math_topic(q):
    q=q.lower()
    if "fraction" in q:
        return "fractions"
    if "decimal" in q:
        return "decimals"
    if "indice" in q:
        return "indices"
    return "general"

# ===============================
# QUIZ GENERATOR (FIXED)
# ===============================
def generate_quiz(subject, doubt):

    if subject.lower()=="math":
        topic = detect_math_topic(doubt)

        # 🔥 FRACTIONS
        if topic=="fractions":
            return [
                f"{random.randint(1,5)}/{random.randint(6,9)} + {random.randint(1,5)}/{random.randint(6,9)}"
                for _ in range(5)
            ]

        # 🔥 DECIMALS
        if topic=="decimals":
            return [
                f"{round(random.uniform(0.1,5),2)} + {round(random.uniform(0.1,5),2)}"
                for _ in range(5)
            ]

        # 🔥 DEFAULT MATH
        return [
            f"{random.randint(1,20)} + {random.randint(1,20)}"
            for _ in range(5)
        ]

    # SCIENCE
    if subject.lower()=="physics":
        return ["What is force?","What is energy?"]

    if subject.lower()=="chemistry":
        return ["What is an atom?","Define acid"]

    if subject.lower()=="biology":
        return ["What is a cell?","Define photosynthesis"]

    return ["No quiz available"]

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q, subject):

    # math calculation
    if subject.lower()=="math":
        ans=solve_math(q)
        if ans:
            return (f"🧮 {ans}","Calculator")

    # knowledge FIRST
    k=get_knowledge(q)
    if k:
        return (explain(k),"📚 Knowledge")

    # pdf (strict)
    chunks=search_pdf(q, subject)
    if chunks:
        text=chunks[0]["text"]
        if is_relevant(text,q):
            return (explain(text.split(". ")[0]),f"📖 {chunks[0]['file']}")

    # wiki
    try:
        return (explain(wikipedia.summary(q,2)),"🌐 Wikipedia")
    except:
        pass

    return ("I couldn't find a clear answer.","Fallback")

# ===============================
# UI
# ===============================
st.subheader("💬 Ask Your Doubt")

doubt = st.text_input("Enter your doubt")

# ===============================
# MODES
# ===============================
if mode=="Tutor Mode":
    if doubt:
        ans,src=get_answer(doubt,subject)
        st.write(ans)
        st.caption(src)

elif mode=="Quiz Mode":
    if st.button("Generate Quiz"):
        for q in generate_quiz(subject,doubt):
            st.write("•",q)

elif mode=="Test Mode":
    if st.button("Start Test"):
        st.session_state.qs=generate_quiz(subject,doubt)
        st.session_state.ans=[""]*len(st.session_state.qs)

    if "qs" in st.session_state:
        for i,q in enumerate(st.session_state.qs):
            st.session_state.ans[i]=st.text_input(q,key=i)

        if st.button("Submit"):
            score=0
            for i,q in enumerate(st.session_state.qs):
                correct=solve_math(q)
                if correct and st.session_state.ans[i]==correct:
                    score+=1
            st.write(f"Score: {score}/{len(st.session_state.qs)}")

elif mode=="Teacher Mode":
    if doubt:
        ans,src=get_answer(doubt,subject)
        st.write(ans)
        st.caption(src)

        st.write("### Practice")
        for q in generate_quiz(subject,doubt):
            st.write("-",q)

st.write(f"📚 Loaded chunks: {len(pages_db)}")
