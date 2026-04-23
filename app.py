import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os

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

# ===============================
# 📚 LOAD ALL PDF PAGES (ONCE)
# ===============================
@st.cache_resource
def load_all_pages():
    data=[]

    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader=PdfReader(f)

                # detect subject
                name=f.lower()
                if "math" in name:
                    subject="math"
                elif "physics" in name:
                    subject="physics"
                elif "chemistry" in name:
                    subject="chemistry"
                elif "biology" in name:
                    subject="biology"
                else:
                    subject="general"

                for i,page in enumerate(reader.pages):
                    txt=page.extract_text()
                    if txt:
                        data.append({
                            "text":txt[:1000],
                            "file":f,
                            "page":i,
                            "subject":subject
                        })
            except:
                pass

    return data

pages_db = load_all_pages()

# ===============================
# ⚡ FAST SKIM (NO WAIT)
# ===============================
def skim(subject, query):

    words = query.lower().split()

    for p in pages_db:
        if p["subject"] != subject:
            continue

        text = p["text"].lower()

        if any(w in text for w in words):
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
        return wikipedia.summary(q[:50], sentences=2)
    except:
        return None

# ===============================
# 🧠 ANSWER ENGINE
# ===============================
def get_answer(query):

    if query in st.session_state.cache:
        return st.session_state.cache[query]

    if ":" in query:
        subject, q = query.split(":",1)
    else:
        subject, q = "general", query

    subject = subject.strip().lower()
    q = q.strip()

    # 1️⃣ SKIM ALL PAGES (FAST)
    page = skim(subject, q)

    if page:
        prompt=f"""
Use this textbook content:

{page['text']}

Answer:
{q}
"""
        ans=ask_gemini(prompt)

        if ans:
            result=(ans, f"📖 {page['file']} (p{page['page']})")
            st.session_state.cache[query]=result
            return result

    # 2️⃣ AI
    ans=ask_gemini(q) or ask_openai(q)
    if ans:
        result=(ans,"💡 AI")
        st.session_state.cache[query]=result
        return result

    # 3️⃣ LAST
    ans=wiki(q)
    result=(ans or "Try rephrasing","🌐 Wiki")
    st.session_state.cache[query]=result
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
        with st.spinner("⚡ Instant answer..."):
            ans,src=get_answer(q)

        st.write(ans)
        st.caption(src)

    st.session_state.chat.append({"role":"assistant","content":ans})

# ===============================
# STATUS
# ===============================
st.write(f"📚 Pages indexed: {len(pages_db)}")
