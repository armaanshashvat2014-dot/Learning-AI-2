import streamlit as st
from PyPDF2 import PdfReader
import os, re, math, random
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Multi-Subject • Dynamic • Smart")

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
# SUBJECT DETECTION
# ===============================
def detect_subject(q):
    q = q.lower()

    if any(w in q for w in ["add","subtract","fraction","decimal","algebra","equation"]):
        return "math"
    if any(w in q for w in ["force","energy","motion","gravity"]):
        return "physics"
    if any(w in q for w in ["atom","molecule","acid","reaction"]):
        return "chemistry"
    if any(w in q for w in ["cell","plant","photosynthesis","human"]):
        return "biology"
    if any(w in q for w in ["noun","verb","grammar","synonym"]):
        return "english"
    if any(w in q for w in ["हिंदी","अर्थ","वाक्य"]):
        return "hindi"

    return "general"

# ===============================
# CLEAN PDF
# ===============================
def clean_text(t):
    t = t.lower()
    if any(x in t for x in ["indb","chapter","exercise","http","©"]):
        return None
    if not re.match(r'^[a-z0-9\s\.\,\-\+\*/\(\)]+$', t):
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
            try:
                reader=PdfReader(f)
                for page in reader.pages:
                    txt=page.extract_text()
                    if txt:
                        txt=clean_text(txt)
                        if txt:
                            data.append({"text":txt,"file":f})
            except:
                pass
    return data

pages_db = load_pdfs()

# ===============================
# SEARCH PDF
# ===============================
def search_pdf(q):
    results=[]
    for c in pages_db:
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

    q=re.sub(r"square (\d+)", r"(\1**2)", q)
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
    "gravity":"Gravity is a force that attracts objects.",
    "atom":"Atom is the smallest unit of matter.",
    "cell":"Cell is the basic unit of life.",
    "noun":"A noun is a naming word.",
    "अर्थ":"अर्थ का मतलब किसी शब्द का मतलब होता है।"
}

def get_knowledge(q):
    for k,v in knowledge.items():
        if k in q.lower():
            return v
    return None

# ===============================
# HINDI AI (SIMULATED)
# ===============================
def quantum_hindi_ai(q):
    return f"🤖 Quantum Hindi AI: यह प्रश्न '{q}' से संबंधित है। कृपया और संदर्भ दें।"

# ===============================
# DYNAMIC QUIZ GENERATOR
# ===============================
def generate_quiz(topic):
    subject = detect_subject(topic)
    qs = []

    if subject == "math":
        for _ in range(5):
            a,b=random.randint(1,20),random.randint(1,20)
            op=random.choice(["+","-","*","/"])
            qs.append(f"{a} {op} {b}")

    elif subject == "physics":
        qs=random.sample([
            "What is force?",
            "Define energy.",
            "What is gravity?",
            "What is motion?"
        ],3)

    elif subject == "chemistry":
        qs=random.sample([
            "What is an atom?",
            "Define molecule.",
            "What is an acid?"
        ],3)

    elif subject == "biology":
        qs=random.sample([
            "What is a cell?",
            "Define photosynthesis.",
            "What is respiration?"
        ],3)

    elif subject == "english":
        qs=random.sample([
            "What is a noun?",
            "Define verb.",
            "What is synonym?"
        ],3)

    elif subject == "hindi":
        qs=[
            "अर्थ क्या होता है?",
            "वाक्य क्या होता है?"
        ]

    else:
        qs=["No quiz available"]

    return qs

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q):

    if q in st.session_state.cache:
        return st.session_state.cache[q]

    subject = detect_subject(q)

    # math
    ans = solve_math(q)
    if ans:
        return (f"🧮 {ans}","Calculator")

    # knowledge
    k=get_knowledge(q)
    if k:
        return (k,f"📚 {subject}")

    # pdf
    chunks=search_pdf(q)
    if chunks:
        return (chunks[0]["text"],"📖 PDF")

    # hindi AI fallback
    if subject=="hindi":
        return (quantum_hindi_ai(q),"🤖 Hindi AI")

    # wiki fallback
    try:
        return (wikipedia.summary(q,2),"🌐 Wikipedia")
    except:
        return ("No answer found.","Fallback")

# ===============================
# MODES
# ===============================

# QUIZ
if mode=="Quiz Mode":
    topic=st.text_input("Enter topic")
    if topic:
        for q in generate_quiz(topic):
            st.write("•",q)

# TEST
elif mode=="Test Mode":
    topic=st.text_input("Enter topic")

    if st.button("Start Test"):
        st.session_state.qs=generate_quiz(topic)
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

# TEACHER
elif mode=="Teacher Mode":
    topic=st.text_input("Enter topic")
    if topic:
        ans,src=get_answer(topic)
        st.write(ans)
        st.caption(src)

        st.write("### Practice")
        for q in generate_quiz(topic):
            st.write("-",q)

# TUTOR
elif mode=="Tutor Mode":
    q=st.chat_input("Ask anything")
    if q:
        ans,src=get_answer(q)
        st.write(ans)
        st.caption(src)

st.write(f"📚 Loaded chunks: {len(pages_db)}")
