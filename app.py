import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("⚡ Use Subject: Question for faster answers")

# ===============================
# KEYS
# ===============================
def get_keys(prefix):
    keys=[]
    i=1
    while True:
        k=st.secrets.get(f"{prefix}_{i}")
        if not k:
            break
        keys.append(k)
        i+=1
    return keys

GEMINI_KEYS = get_keys("GEMINI_API_KEY")
OPENAI_KEYS = get_keys("OPENAI_API_KEY")

# ===============================
# PDF MEMORY SYSTEM
# ===============================
@st.cache_resource
def load_pdfs():
    chunks=[]
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader = PdfReader(f)
                for p in reader.pages:
                    txt = p.extract_text()
                    if txt:
                        chunks.append(txt[:1500])
            except:
                pass
    return chunks

books = load_pdfs()

# MEMORY INDEX (persistent in session)
if "memory_index" not in st.session_state:
    st.session_state.memory_index = books.copy()

# ===============================
# SEARCH MEMORY
# ===============================
def search_memory(q):
    words=set(q.lower().split())
    best=""
    score_max=0

    for chunk in st.session_state.memory_index:
        score=len(words & set(chunk.lower().split()))
        if score>score_max:
            score_max=score
            best=chunk

    return best[:1000]

# ===============================
# AI CALLS
# ===============================
def ask_gemini(prompt):
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(prompt).text
        except:
            continue
    return None

def ask_openai(prompt):
    for k in OPENAI_KEYS:
        try:
            client=openai.OpenAI(api_key=k)
            r=client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=400
            )
            return r.choices[0].message.content
        except:
            continue
    return None

# ===============================
# PARALLEL AI
# ===============================
def ask_ai_parallel(prompt):

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [
            ex.submit(ask_gemini, prompt),
            ex.submit(ask_openai, prompt),
            ex.submit(lambda: wikipedia.summary(prompt, sentences=2))
        ]

        for f in as_completed(futures):
            try:
                res = f.result()
                if res:
                    return res
            except:
                pass

    return None

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(query):

    if ":" in query:
        subject, q = query.split(":",1)
    else:
        q = query

    # 1️⃣ MEMORY SEARCH (PDF learned)
    context = search_memory(q)

    if context:
        prompt = f"""
Answer based ONLY on this knowledge:

{context}

Question:
{q}
"""
        ans = ask_ai_parallel(prompt)
        if ans:
            return ans + "\n\n📚 Source: Memory (PDF)"

    # 2️⃣ AI fallback
    ans = ask_ai_parallel(q)
    if ans:
        return ans + "\n\n💡 Source: AI"

    return "⚡ Still thinking... try again"

# ===============================
# UI
# ===============================
query = st.text_input("Ask your doubt")

if st.button("Ask"):
    if query:
        with st.spinner("Thinking..."):
            ans = get_answer(query)
        st.write(ans)

# ===============================
# STATUS
# ===============================
st.write(f"📚 Memory chunks: {len(st.session_state.memory_index)}")
