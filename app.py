import streamlit as st
from PyPDF2 import PdfReader
import os, re, math, random
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Subject-aware • Accurate • Smart")

# ===============================
# STATE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache = {}

# ===============================
# SUBJECT SELECTOR
# ===============================
subject = st.sidebar.selectbox(
    "Select Subject",
    ["Math", "Physics", "Chemistry", "Biology", "English", "Hindi", "General"]
)

mode = st.sidebar.selectbox(
    "Mode",
    ["Tutor Mode", "Quiz Mode", "Test Mode", "Teacher Mode"]
)

# ===============================
# CLEAN PDF TEXT
# ===============================
def clean_text(t):
    t = t.lower()
    if any(x in t for x in ["indb","chapter","exercise","http","©"]):
        return None
    return t

# ===============================
# LOAD PDF
# ===============================
@st.cache_resource
def load_pdfs():
    data=[]
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            sub = "general"
            if "math" in f.lower(): sub="math"
            if "phy" in f.lower(): sub="physics"
            if "chem" in f.lower(): sub="chemistry"
            if "bio" in f.lower(): sub="biology"

            try:
                reader=PdfReader(f)
                for page in reader.pages:
                    txt=page.extract_text()
                    if txt:
                        txt=clean_text(txt)
                        if txt:
                            data.append({
                                "text":txt,
                                "file":f,
                                "subject":sub
                            })
            except:
                pass
    return data

pages_db = load_pdfs()

# ===============================
# SEARCH PDF (SUBJECT FILTERED)
# ===============================
def search_pdf(q, subject):
    results=[]

    for c in pages_db:
        if subject.lower() != "general" and c["subject"] != subject.lower():
            continue

        score=sum(1 for w in q.lower().split() if w in c["text"])

        if score>0:
            results.append((score,c))

    results.sort(key=lambda x:x[0], reverse=True)
    return [r[1] for r in results[:2]]

# ===============================
# MATH
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
# KNOWLEDGE
# ===============================
knowledge = {
    "physics":{
        "gravity":"Gravity is a force that attracts objects toward Earth.",
        "energy":"Energy is the ability to do work."
    },
    "chemistry":{
        "atom":"An atom is the smallest unit of matter.",
        "acid":"An acid has pH less than 7."
    },
    "biology":{
        "cell":"A cell is the basic unit of life.",
        "photosynthesis":"Plants make food using sunlight."
    },
    "english":{
        "noun":"A noun is a naming word."
    },
    "hindi":{
        "अर्थ":"अर्थ का मतलब किसी शब्द का अर्थ होता है।"
    }
}

def get_knowledge(q, subject):
    if subject.lower() in knowledge:
        for k,v in knowledge[subject.lower()].items():
            if k in q.lower():
                return v
    return None

# ===============================
# TEACHER STYLE
# ===============================
def explain(text):
    return f"""
📘 Explanation:
{text}

💡 Simple:
{text.split('.')[0]}.

🧠 Tip:
Understand the idea clearly.
"""

# ===============================
# QUIZ (SUBJECT BASED)
# ===============================
def generate_quiz(subject):
    subject=subject.lower()

    if subject=="math":
        return [f"{random.randint(1,20)} + {random.randint(1,20)}" for _ in range(5)]

    if subject=="physics":
        return ["What is force?","What is energy?","What is gravity?"]

    if subject=="chemistry":
        return ["What is an atom?","Define acid","What is a molecule?"]

    if subject=="biology":
        return ["What is a cell?","Define photosynthesis"]

    if subject=="english":
        return ["What is a noun?","Define verb"]

    if subject=="hindi":
        return ["अर्थ क्या है?","वाक्य क्या है?"]

    return ["No quiz available"]

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q, subject):

    if q in st.session_state.cache:
        return st.session_state.cache[q]

    # math
    if subject.lower()=="math":
        ans=solve_math(q)
        if ans:
            return (f"🧮 {ans}","Calculator")

    # knowledge
    k=get_knowledge(q, subject)
    if k:
        return (explain(k),"📚 Knowledge")

    # pdf
    chunks=search_pdf(q, subject)
    if chunks:
        return (explain(chunks[0]["text"]),f"📖 {chunks[0]['file']}")

    # wiki
    try:
        return (explain(wikipedia.summary(q,2)),"🌐 Wikipedia")
    except:
        pass

    return ("I couldn't find a clear answer.","Fallback")

# ===============================
# UI INPUT (NEW SYSTEM)
# ===============================
st.subheader("💬 Ask Your Doubt")

doubt = st.text_input("Enter your doubt (Subject → Doubt format recommended)")

# ===============================
# MODES
# ===============================
if mode=="Tutor Mode":
    if doubt:
        ans,src=get_answer(doubt, subject)
        st.write(ans)
        st.caption(src)

elif mode=="Quiz Mode":
    if st.button("Generate Quiz"):
        for q in generate_quiz(subject):
            st.write("•",q)

elif mode=="Test Mode":
    if st.button("Start Test"):
        st.session_state.qs=generate_quiz(subject)
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
        ans,src=get_answer(doubt, subject)
        st.write(ans)
        st.caption(src)

        st.write("### Practice")
        for q in generate_quiz(subject):
            st.write("-",q)

st.write(f"📚 Loaded chunks: {len(pages_db)}")
