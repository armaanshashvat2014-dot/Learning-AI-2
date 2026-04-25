import streamlit as st
from PyPDF2 import PdfReader
import os, re, math, random
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Accurate • Clean • Teacher Mode AI")

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
    q=q.lower()

    if any(w in q for w in ["add","subtract","fraction","decimal","algebra","equation"]):
        return "math"
    if any(w in q for w in ["force","energy","gravity","motion"]):
        return "physics"
    if any(w in q for w in ["atom","acid","reaction","molecule"]):
        return "chemistry"
    if any(w in q for w in ["cell","plant","photosynthesis"]):
        return "biology"
    if any(w in q for w in ["noun","verb","grammar"]):
        return "english"
    if any(w in q for w in ["हिंदी","अर्थ","वाक्य"]):
        return "hindi"

    return "general"

# ===============================
# CLEAN PDF TEXT
# ===============================
def clean_text(t):
    t=t.lower()
    if any(x in t for x in ["indb","chapter","exercise","http","©","youtube"]):
        return None
    if not re.match(r'^[a-z0-9\s\.\,\-\+\*/\(\)]+$', t):
        return None
    return t

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

pages_db=load_pdfs()

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
# VALIDATION
# ===============================
def is_valid_answer(text, query):
    if not text:
        return False

    text=text.lower()
    q_words=set(query.lower().split())
    matches=sum(1 for w in q_words if w in text)

    if matches < 2:
        return False

    if any(b in text for b in ["chapter","exercise","contents"]):
        return False

    return True

# ===============================
# CLEAN OUTPUT
# ===============================
def clean_output(text):
    sentences=text.split(". ")
    sentences=[s for s in sentences if len(s)<200]
    return ". ".join(sentences[:2])

# ===============================
# TEACHER EXPLAINER
# ===============================
def explain_like_teacher(text, question):
    if not text:
        return None

    return f"""
📘 Explanation:

{text}

💡 In simple words:
This means that {text.split('.')[0].lower()}.

🧠 Tip:
Try to remember the idea rather than memorising words.
"""

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
knowledge={
    "gravity":"Gravity is a force that attracts objects towards Earth.",
    "atom":"An atom is the smallest unit of matter.",
    "cell":"A cell is the basic unit of life.",
    "noun":"A noun is a naming word.",
    "अर्थ":"अर्थ का मतलब किसी शब्द का अर्थ होता है।"
}

def get_knowledge(q):
    for k,v in knowledge.items():
        if k in q.lower():
            return v
    return None

# ===============================
# QUIZ
# ===============================
def generate_quiz(topic):
    subject=detect_subject(topic)

    if subject=="math":
        return [f"{random.randint(1,20)} + {random.randint(1,20)}" for _ in range(5)]

    if subject=="physics":
        return random.sample([
            "What is force?",
            "Define energy.",
            "What is gravity?"
        ],3)

    if subject=="chemistry":
        return random.sample([
            "What is an atom?",
            "Define molecule."
        ],2)

    if subject=="biology":
        return random.sample([
            "What is a cell?",
            "Define photosynthesis."
        ],2)

    return ["No quiz available"]

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q):

    if q in st.session_state.cache:
        return st.session_state.cache[q]

    # math
    ans=solve_math(q)
    if ans:
        return (f"🧮 {ans}","Calculator")

    # knowledge
    k=get_knowledge(q)
    if k:
        return (explain_like_teacher(k,q),"📚 Knowledge")

    # pdf
    chunks=search_pdf(q)
    if chunks:
        text=chunks[0]["text"]
        if is_valid_answer(text,q):
            return (explain_like_teacher(clean_output(text),q),"📖 PDF")

    # wiki
    try:
        w=wikipedia.summary(q,2)
        if is_valid_answer(w,q):
            return (explain_like_teacher(clean_output(w),q),"🌐 Wikipedia")
    except:
        pass

    return ("I couldn’t find a clear answer. Try asking more specifically.","Fallback")

# ===============================
# MODES
# ===============================
if mode=="Quiz Mode":
    topic=st.text_input("Enter topic")
    if topic:
        for q in generate_quiz(topic):
            st.write("•",q)

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

elif mode=="Teacher Mode":
    topic=st.text_input("Enter topic")
    if topic:
        ans,src=get_answer(topic)
        st.write(ans)
        st.caption(src)

        st.write("### Practice")
        for q in generate_quiz(topic):
            st.write("-",q)

elif mode=="Tutor Mode":
    q=st.chat_input("Ask anything")
    if q:
        ans,src=get_answer(q)
        st.write(ans)
        st.caption(src)

st.write(f"📚 Loaded chunks: {len(pages_db)}")
