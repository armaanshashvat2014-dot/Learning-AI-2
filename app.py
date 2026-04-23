import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import threading
import re

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Instant answers + learns PDFs in background")

# ===============================
# 🔑 KEYS
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
# 🧠 STATE
# ===============================
if "pages_db" not in st.session_state:
    st.session_state.pages_db=[]
    st.session_state.loaded=False

if "cache" not in st.session_state:
    st.session_state.cache={}

# ===============================
# 📚 BACKGROUND PDF LOADER
# ===============================
def load_pdfs():
    data=[]

    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader=PdfReader(f)

                name=f.lower()
                if "math" in name:
                    subject="math"
                elif "physi" in name:
                    subject="physics"
                elif "chem" in name:
                    subject="chemistry"
                elif "biol" in name:
                    subject="biology"
                else:
                    subject="general"

                for i,page in enumerate(reader.pages):
                    txt=page.extract_text()
                    if txt:
                        data.append({
                            "text":txt[:800],
                            "file":f,
                            "page":i,
                            "subject":subject
                        })

                    # progressive update
                    if len(data)%30==0:
                        st.session_state.pages_db=data.copy()

            except:
                pass

    st.session_state.pages_db=data
    st.session_state.loaded=True

# start background loader
if not st.session_state.loaded:
    threading.Thread(target=load_pdfs, daemon=True).start()

# ===============================
# ⚡ CACHE
# ===============================
def cache_get(q):
    return st.session_state.cache.get(q)

def cache_set(q,a):
    st.session_state.cache[q]=a

# ===============================
# 📚 FAST PDF SEARCH
# ===============================
def skim(subject,q):
    for p in st.session_state.pages_db:
        if p["subject"]==subject and q.lower() in p["text"].lower():
            return p
    return None

# ===============================
# 🤖 AI
# ===============================
def ask_gemini(q):
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(q).text
        except:
            continue
    return None

def ask_openai(q):
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

# ===============================
# 🌐 WIKI
# ===============================
def wiki(q):
    try:
        return wikipedia.summary(q[:60], sentences=2)
    except:
        return None

# ===============================
# 🧮 MATH (FIXED PROPERLY)
# ===============================
def is_calculation(q):
    return bool(re.fullmatch(r"[0-9\.\+\-\*/\(\)\s]+", q.strip()))

def solve_math(q):
    try:
        q=q.replace(" ","")
        return str(eval(q))
    except:
        return None

def is_math_concept(q):
    words = ["what","define","explain","meaning","concept"]
    return any(w in q.lower() for w in words)

# ===============================
# 🧠 ANSWER ENGINE
# ===============================
def get_answer(query):

    # cache
    if query in st.session_state.cache:
        return st.session_state.cache[query]

    # subject split
    if ":" in query:
        subject,q=query.split(":",1)
    else:
        subject,q="general",query

    subject=subject.strip().lower()
    q=q.strip()

    # ===============================
    # 1️⃣ MATH HANDLING
    # ===============================
    if is_calculation(q):
        ans=solve_math(q)
        if ans:
            result=(f"🧮 Answer: {ans}","Calculator")
            cache_set(query,result)
            return result

    # ===============================
    # 2️⃣ PDF (if loaded)
    # ===============================
    if st.session_state.pages_db:
        page=skim(subject,q)
        if page:
            prompt=f"Use this:\n{page['text']}\n\nQ:{q}"
            ans=ask_gemini(prompt)
            if ans:
                result=(ans,f"📖 {page['file']} p{page['page']}")
                cache_set(query,result)
                return result

    # ===============================
    # 3️⃣ WIKI (FAST)
    # ===============================
    w=wiki(q)
    if w:
        result=(w,"🌐 Wikipedia")
        cache_set(query,result)
        return result

    # ===============================
    # 4️⃣ AI
    # ===============================
    ans=ask_gemini(q) or ask_openai(q)
    if ans:
        result=(ans,"💡 AI")
        cache_set(query,result)
        return result

    # ===============================
    # FINAL
    # ===============================
    result=("⚡ Try rephrasing your question","Fallback")
    cache_set(query,result)
    return result

# ===============================
# 💬 UI
# ===============================
if "chat" not in st.session_state:
    st.session_state.chat=[]

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.write(m["content"])

q=st.chat_input("Ask your doubt...")

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
st.write(f"📚 Pages learned: {len(st.session_state.pages_db)}")

if not st.session_state.loaded:
    st.info("⚡ Learning PDFs in background...")
else:
    st.success("📚 Fully learned")
