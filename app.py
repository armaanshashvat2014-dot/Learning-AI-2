import streamlit as st
from PyPDF2 import PdfReader
import os
import re
import math
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Learns • Clean • Offline")

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
# SEARCH PDF
# ===============================
def search_pdf(q):
    words=set(q.lower().split())
    res=[]
    for c in pages_db:
        score=sum(1 for w in words if w in c["text"])
        if score>1:
            res.append((score,c))
    res.sort(reverse=True)
    return [r[1] for r in res[:3]]

# ===============================
# MATH PARSER (ENGLISH → EXPRESSION)
# ===============================
def parse_math(q):
    q=q.lower()

    # words to symbols
    q=q.replace("plus","+")
    q=q.replace("add","+")
    q=q.replace("minus","-")
    q=q.replace("subtract","-")
    q=q.replace("remove","-")
    q=q.replace("times","*")
    q=q.replace("multiply","*")
    q=q.replace("divide","/")
    q=q.replace("divided by","/")

    # powers
    q=q.replace("square","**2")
    q=q.replace("cube","**3")

    # roots
    q=re.sub(r"square root of (\d+)", r"math.sqrt(\1)", q)
    q=re.sub(r"cube root of (\d+)", r"(\1)**(1/3)", q)

    return q

# ===============================
# DETECT CALC
# ===============================
def is_calc(q):
    return any(w in q.lower() for w in [
        "+","-","*","/","square","root","add","subtract","multiply","divide","power"
    ]) or bool(re.fullmatch(r"[0-9\.\+\-\*/\(\)\^\s]+", q.strip()))

# ===============================
# SOLVE
# ===============================
def solve_math(q):
    try:
        q = q.replace("^","**")
        q = parse_math(q)
        return str(eval(q))
    except:
        return None

# ===============================
# KNOWLEDGE
# ===============================
knowledge={
    "indices":"Indices are powers showing repeated multiplication. Example: 2^3 = 2×2×2.",
    "algebra":"Algebra uses symbols like x to represent unknown values.",
    "einstein":"Albert Einstein developed the theory of relativity.",
    "gold":"Gold is a chemical element with symbol Au."
}

def get_knowledge(q):
    for k,v in knowledge.items():
        if k in q.lower():
            return v
    return None

# ===============================
# QUESTION GENERATOR
# ===============================
def generate_questions(q):
    if "indices" in q.lower():
        return """📘 Indices Questions:
1. 2^3 × 2^4
2. 5^6 ÷ 5^2
3. (3^2)^3
4. 10^0
5. 64 as power of 2"""
    return """📘 Maths Questions:
1. 45 + 67
2. 120 − 89
3. 8 × 7
4. 144 ÷ 12"""

# ===============================
# LOCAL ANSWER
# ===============================
def local_answer(text,q):
    s=text.split(". ")
    return ". ".join(s[:3])

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q):

    try:
        if q in st.session_state.cache:
            return st.session_state.cache[q]

        # questions
        if "question" in q.lower():
            res=(generate_questions(q),"📘 Practice")
            st.session_state.cache[q]=res
            return res

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

        # pdf (math only)
        if any(w in q.lower() for w in ["math","indices","algebra"]):
            chunks=search_pdf(q)
            if chunks:
                combined=" ".join([c["text"] for c in chunks])
                res=(local_answer(combined,q),f"📖 {chunks[0]['file']}")
                st.session_state.cache[q]=res
                return res

        # wiki
        if not is_calc(q):
            try:
                w=wikipedia.summary(q,2)
                res=(w,"🌐 Wikipedia")
                st.session_state.cache[q]=res
                return res
            except:
                pass

        # fallback
        res=("I couldn't find a clear answer.","Fallback")
        st.session_state.cache[q]=res
        return res

    except Exception as e:
        return (f"⚠️ {str(e)}","Error")

# ===============================
# UI
# ===============================
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

st.write(f"📚 Loaded chunks: {len(pages_db)}")
