import streamlit as st
from PyPDF2 import PdfReader
import os, re, random
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Smart • Multi-Subject • Adaptive")

# ===============================
# MODE
# ===============================
mode = st.sidebar.selectbox(
    "Select Mode",
    ["Tutor Mode", "Teacher Mode", "Quiz Mode", "Test Mode"]
)

# ===============================
# CLEAN TEXT
# ===============================
def clean_text(text):
    text = text.lower()
    text = re.sub(r'^\d+\s+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ===============================
# LOAD PDF
# ===============================
@st.cache_resource
def load_kb():
    kb=[]
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader=PdfReader(f)
                for p in reader.pages:
                    t=p.extract_text()
                    if t:
                        t=clean_text(t)
                        for s in t.split(". "):
                            if 60 < len(s) < 180:
                                kb.append({"text":s,"src":f})
            except:
                pass
    return kb

kb=load_kb()

# ===============================
# SEARCH
# ===============================
def search_kb(q):
    q=q.lower()
    words=q.split()
    res=[]
    for item in kb:
        score=0
        for w in words:
            if w in item["text"]:
                score+=2
        if q in item["text"]:
            score+=5
        if score>0:
            res.append((score,item))
    res.sort(key=lambda x:x[0],reverse=True)
    return [r[1] for r in res[:3]]

# ===============================
# CONTENT
# ===============================
def get_content(q):
    text=""
    src=""

    r=search_kb(q)
    if r:
        text=r[0]["text"]
        src=f"📖 {r[0]['src']}"

    try:
        wiki=wikipedia.summary(q,2)
        text+=" "+wiki
        src+=" + 🌐 Wikipedia"
    except:
        pass

    return text.strip(),src

# ===============================
# EXPLAIN
# ===============================
def explain(text):
    if not text:
        return "No explanation found."
    return f"""
📘 Explanation:
{text[:400]}

💡 Simple:
{text.split('.')[0]}.
"""

# ===============================
# SUBJECT DETECTION
# ===============================
def detect_subject(q):
    q=q.lower()

    if any(x in q for x in ["add","minus","number","+","-","*","/","^","math","algebra","fraction","decimal"]):
        return "math"

    if any(x in q for x in ["force","cell","energy","atom","plant","physics","chemistry","biology","science"]):
        return "science"

    if any(x in q for x in ["noun","verb","english","grammar","sentence"]):
        return "english"

    return "general"

# ===============================
# MATH ENGINE
# ===============================
def is_math(q):
    return bool(re.search(r"[0-9\+\-\*/\^]", q))

def parse_math(q):
    q=q.lower()
    q=q.replace("plus","+").replace("minus","-")
    q=q.replace("times","*").replace("divide","/")
    q=q.replace("^","**")
    q=re.sub(r"square (\d+)", r"(\1**2)", q)
    return q

def solve_math(q):
    try:
        return str(eval(parse_math(q),{"__builtins__":None},{}))
    except:
        return None

# ===============================
# QUESTION GENERATORS
# ===============================
def generate_math(mode):
    qs=[]
    count={"Teacher Mode":3,"Quiz Mode":5,"Test Mode":7}.get(mode,4)

    for _ in range(count):
        style=random.choice(["basic","power","mix"])

        if style=="basic":
            a,b=random.randint(1,20),random.randint(1,20)
            op=random.choice(["+","-","*"])
            qs.append(f"{a} {op} {b}")

        elif style=="power":
            a=random.randint(2,10)
            b=random.randint(2,4)
            qs.append(f"{a}^{b}")

        else:
            a=random.randint(5,20)
            b=random.randint(2,5)
            c=random.randint(2,3)
            op=random.choice(["+","-"])
            qs.append(f"{a} {op} {b}^{c}")

    return qs

def generate_science(topic,mode):
    base=[
        f"What is {topic}?",
        f"Why is {topic} important?",
        f"How does {topic} work?",
        f"When is {topic} used?",
        f"Who discovered {topic}?",
        f"Give an example of {topic}."
    ]
    random.shuffle(base)
    return base[:{"Teacher Mode":3,"Quiz Mode":5,"Test Mode":6}.get(mode,4)]

def generate_english(topic,mode):
    base=[
        f"What is {topic}?",
        f"Define {topic}.",
        f"Give an example of {topic}.",
        f"Use {topic} in a sentence.",
        f"Why is {topic} important?"
    ]
    random.shuffle(base)
    return base[:{"Teacher Mode":3,"Quiz Mode":5,"Test Mode":6}.get(mode,4)]

def generate_questions(topic,mode):
    subject=detect_subject(topic)

    if subject=="math":
        return generate_math(mode)

    elif subject=="science":
        return generate_science(topic,mode)

    elif subject=="english":
        return generate_english(topic,mode)

    else:
        return generate_science(topic,mode)

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q):

    if is_math(q):
        ans=solve_math(q)
        if ans:
            return f"🧮 Answer: {ans}","Calculator"

    text,src=get_content(q)

    if text:
        return explain(text),src

    return "No clear answer","Fallback"

# ===============================
# UI
# ===============================
st.subheader("💬 Ask Your Doubt")
q=st.text_input("Enter topic or question")

if q:

    text,src=get_content(q)
    ans,source=get_answer(q)

    # Tutor
    if mode=="Tutor Mode":
        st.write(ans)
        st.caption(source)

    # Teacher
    elif mode=="Teacher Mode":
        st.write(ans)
        st.caption(source)

        st.subheader("📝 Practice")
        for ques in generate_questions(q,mode):
            st.write("-",ques)

    # Quiz
    elif mode=="Quiz Mode":
        st.subheader("📝 Quiz")
        for ques in generate_questions(q,mode):
            st.write("•",ques)

    # Test
    elif mode=="Test Mode":

        if "started" not in st.session_state:
            st.session_state.started=False

        if not st.session_state.started:
            if st.button("Start Test"):
                st.session_state.started=True
                st.session_state.qs=generate_questions(q,mode)
                st.session_state.ans=[""]*len(st.session_state.qs)

        if st.session_state.started:

            for i,ques in enumerate(st.session_state.qs):
                st.session_state.ans[i]=st.text_input(f"Q{i+1}. {ques}",key=i)

            if st.button("Submit"):

                score=0

                for i,ques in enumerate(st.session_state.qs):

                    if is_math(ques):
                        correct=solve_math(ques)
                        if correct and st.session_state.ans[i]==correct:
                            score+=1
                    else:
                        if len(st.session_state.ans[i])>3:
                            score+=1

                st.write(f"🎯 Score: {score}/{len(st.session_state.qs)}")
                st.session_state.started=False

# ===============================
# STATUS
# ===============================
st.write(f"📚 Knowledge chunks: {len(kb)}")
