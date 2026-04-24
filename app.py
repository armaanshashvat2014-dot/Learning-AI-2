import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import re

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Fast • 📚 Learns • 🧠 Works without APIs")

# ===============================
# ⚡ NO API MODE
# ===============================
NO_API_MODE = st.sidebar.toggle("⚡ No API Mode", value=False)

# ===============================
# KEYS
# ===============================
def get_keys(prefix):
    keys=[]
    i=1
    while True:
        k=st.secrets.get(f"{prefix}_{i}")
        if not k: break
        keys.append(k)
        i+=1
    return keys

GEMINI_KEYS = get_keys("GEMINI_API_KEY")
OPENAI_KEYS = get_keys("OPENAI_API_KEY")

# ===============================
# CACHE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache={}

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
                        parts=txt.split(". ")
                        for p in parts:
                            if len(p)>50:
                                data.append({
                                    "text":p.strip(),
                                    "file":f,
                                    "page":i
                                })
            except:
                pass
    return data

pages_db=load_pdfs()

# ===============================
# SEARCH
# ===============================
def search_pdf(q):
    words=set(q.lower().split())
    results=[]
    for c in pages_db:
        text=c["text"].lower()
        score=sum(1 for w in words if w in text)
        if score>1:
            results.append((score,c))
    results.sort(reverse=True,key=lambda x:x[0])
    return [r[1] for r in results[:3]]

# ===============================
# MATH
# ===============================
def is_calc(q):
    return bool(re.fullmatch(r"[0-9\.\+\-\*/\(\)\s]+", q.strip()))

def solve_math(q):
    try:
        return str(eval(q.replace(" ","")))
    except:
        return None

# ===============================
# KNOWLEDGE
# ===============================
knowledge={
    "who is einstein":"Albert Einstein was a physicist known for the theory of relativity.",
    "what are decimals":"Decimals are numbers written with a decimal point to represent fractions.",
    "what is gravity":"Gravity is a force that attracts objects with mass.",
    "what is photosynthesis":"Photosynthesis is how plants make food using sunlight."
}

def get_knowledge(q):
    for k,v in knowledge.items():
        if k in q.lower():
            return v
    return None

# ===============================
# LOCAL ANSWER ENGINE
# ===============================
def generate_local_answer(text, question):
    if not text:
        return None
    sentences=text.split(". ")
    q_words=set(question.lower().split())
    scored=[]
    for s in sentences:
        score=sum(1 for w in q_words if w in s.lower())
        if score>0:
            scored.append((score,s))
    scored.sort(reverse=True)
    best=[s for _,s in scored[:3]]
    if best:
        return " ".join(best)
    return sentences[0] if sentences else None

# ===============================
# AI CALLS
# ===============================
def ask_gemini(q):
    if NO_API_MODE:
        return None
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(q).text
        except:
            continue
    return None

def ask_openai(q):
    if NO_API_MODE:
        return None
    for k in OPENAI_KEYS:
        try:
            client=openai.OpenAI(api_key=k)
            r=client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":q}],
                max_tokens=300
            )
            return r.choices[0].message.content
        except:
            continue
    return None

def ask_ai(q):
    return ask_gemini(q) or ask_openai(q)

# ===============================
# WIKI
# ===============================
def wiki(q):
    try:
        return wikipedia.summary(q[:60], sentences=2)
    except:
        return None

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
    if chunks:
        combined=" ".join([c["text"] for c in chunks])
        prompt=f"{combined}\n\nQ:{q}"

        ans=ask_ai(prompt)

        if not ans:
            ans=generate_local_answer(combined,q)

        if ans:
            res=(ans,f"📖 {chunks[0]['file']}")
            st.session_state.cache[q]=res
            return res

    # wiki
    w=wiki(q)
    if w:
        res=(w,"🌐 Wikipedia")
        st.session_state.cache[q]=res
        return res

    # final
    ans=ask_ai(q)

    if not ans:
        ans=generate_local_answer(q,q) or "I couldn't find a clear answer."

    res=(ans,"💡 AI / Local")
    st.session_state.cache[q]=res
    return res

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

# ===============================
# STATUS
# ===============================
st.write(f"📚 Loaded chunks: {len(pages_db)}")
