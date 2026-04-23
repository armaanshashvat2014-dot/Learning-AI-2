import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import time
import random

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("Use format → Subject: Question")

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
# ⚡ CACHE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache={}

def cache_get(q):
    return st.session_state.cache.get(q)

def cache_set(q,a):
    st.session_state.cache[q]=a

# ===============================
# 📚 LOAD PDF INDEX (FAST)
# ===============================
@st.cache_resource
def load_index():
    index={}
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            name=f.lower()

            if "math" in name:
                subject="math"
            elif "phy" in name:
                subject="physics"
            elif "chem" in name:
                subject="chemistry"
            elif "bio" in name:
                subject="biology"
            else:
                subject="general"

            index.setdefault(subject, []).append(f)
    return index

pdf_index = load_index()

# ===============================
# 📖 SKIM PDF (FAST)
# ===============================
def skim_pdf(subject, query):

    files = pdf_index.get(subject.lower(), [])

    for f in files:
        try:
            reader = PdfReader(f)

            for page in reader.pages[:5]:  # only first few pages
                text = page.extract_text()
                if not text:
                    continue

                if query.lower() in text.lower():
                    return text[:500], f

        except:
            continue

    return None, None

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
        return wikipedia.summary(q[:50], sentences=2)
    except:
        return None

# ===============================
# 🧠 ANSWER ENGINE
# ===============================
def get_answer(query):

    # cache
    if query in st.session_state.cache:
        return st.session_state.cache[query]

    # split subject
    if ":" in query:
        subject, q = query.split(":",1)
    else:
        subject, q = "general", query

    subject = subject.strip().lower()
    q = q.strip()

    # 1️⃣ PDF SKIM
    text, file = skim_pdf(subject, q)

    if text:
        prompt=f"Answer using this:\n{text}\n\nQ:{q}"
        ans=ask_gemini(prompt)

        if ans:
            result=(ans, f"📖 {file}")
            cache_set(query, result)
            return result

    # 2️⃣ AI
    ans = ask_gemini(q) or ask_openai(q)
    if ans:
        result=(ans,"💡 AI")
        cache_set(query, result)
        return result

    # 3️⃣ LAST
    ans = wiki(q)
    result=(ans or "Try rephrasing","🌐 Wiki")
    cache_set(query, result)
    return result

# ===============================
# 💬 UI
# ===============================
if "chat" not in st.session_state:
    st.session_state.chat=[]

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.write(m["content"])

q = st.chat_input("Ask your doubt...")

if q:
    st.session_state.chat.append({"role":"user","content":q})

    with st.chat_message("assistant"):
        with st.spinner("⚡ Fast thinking..."):
            ans,src=get_answer(q)

        st.write(ans)
        st.caption(src)

    st.session_state.chat.append({"role":"assistant","content":ans})
