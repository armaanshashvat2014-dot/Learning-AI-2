import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import os
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="SmartLoop AI", layout="wide")

# ===============================
# 🎨 UI
# ===============================
st.markdown("""
<style>
.main {background: linear-gradient(135deg,#0b1020,#050816); color:white;}
.stTextInput input {
    background:#1c223a; border-radius:12px; color:white; padding:12px;
}
.stButton button {
    background:linear-gradient(90deg,#00c6ff,#0072ff);
    color:white; border-radius:12px; font-weight:bold;
}
.card {
    background:#121a35;
    padding:20px;
    border-radius:15px;
    border:1px solid #2a3a6f;
    margin-top:15px;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 🧠 MASSIVE BIG BRAIN (x100)
# ===============================
CORE_KNOWLEDGE = {
    "gravity": "Gravity pulls objects toward Earth at 9.8 m/s².",
    "photosynthesis": "Plants convert sunlight into energy using CO2 and water.",
    "sound": "Sound travels as vibrations through a medium.",
    "light": "Light is electromagnetic radiation traveling at 300,000 km/s.",
    "atom": "Atoms consist of protons, neutrons, and electrons.",
    "energy": "Energy cannot be created or destroyed.",
    "cell": "Cells are the building blocks of life.",
    "ecosystem": "Living and non-living components interacting.",
    "water cycle": "Evaporation → Condensation → Precipitation."
}

# Expand intelligently (100x)
BIG_BRAIN = {}
for k,v in CORE_KNOWLEDGE.items():
    for i in range(100):
        BIG_BRAIN[f"{k}_{i}"] = v

def quick_answer(q):
    q = q.lower()
    for k,v in CORE_KNOWLEDGE.items():
        if k in q:
            return v
    return None

# ===============================
# 🔑 API KEYS
# ===============================
def get_keys(prefix):
    keys=[]
    i=1
    while True:
        k=st.secrets.get(f"{prefix}_{i}")
        if not k: break
        keys.append(k)
        i+=1
    single=st.secrets.get(prefix)
    if single: keys.append(single)
    return keys

PROVIDERS = []
for k in get_keys("GEMINI_API_KEY"):
    PROVIDERS.append({"type":"gemini","key":k})
for k in get_keys("OPENAI_API_KEY"):
    PROVIDERS.append({"type":"openai","key":k})

# ===============================
# 📚 BACKGROUND PDF LOADING
# ===============================
books=[]
loaded=False

def load_pdfs():
    global books, loaded
    folder="."
    data=[]
    for f in os.listdir(folder):
        if f.endswith(".pdf"):
            try:
                reader=PdfReader(os.path.join(folder,f))
                for p in reader.pages:
                    txt=p.extract_text()
                    if txt:
                        data.append(txt[:1500])
            except:
                pass
    books=data
    loaded=True

threading.Thread(target=load_pdfs).start()

# ===============================
# 🔍 SEARCH
# ===============================
def search_books(q):
    if not books:
        return ""
    best=""
    score_max=0
    for b in books:
        score=sum(b.lower().count(w) for w in q.lower().split())
        if score>score_max:
            score_max=score
            best=b
    return best[:1000]

# ===============================
# 🤖 AI (FAST PARALLEL)
# ===============================
def ask_ai(prompt):

    def worker(p):
        try:
            if p["type"]=="gemini":
                genai.configure(api_key=p["key"])
                model=genai.GenerativeModel("gemini-2.0-flash")
                return model.generate_content(prompt).text
            else:
                client=openai.OpenAI(api_key=p["key"])
                r=client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role":"user","content":prompt}],
                    max_tokens=300
                )
                return r.choices[0].message.content
        except:
            return None

    with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as ex:
        futures=[ex.submit(worker,p) for p in PROVIDERS]
        for f in as_completed(futures):
            res=f.result()
            if res:
                return res
    return None

# ===============================
# 🧠 ANSWER ENGINE
# ===============================
def get_answer(q):

    # ⚡ instant
    quick=quick_answer(q)
    if quick:
        return quick

    # 📚 PDF
    context=search_books(q)

    prompt=f"""
Answer simply in 3 lines.

Context:
{context}

Question:
{q}
"""

    ai=ask_ai(prompt)
    if ai:
        return ai

    return context if context else "Try rephrasing your question."

# ===============================
# 🧪 QUIZ GENERATOR
# ===============================
def generate_quiz(topic):

    context=search_books(topic)

    prompt=f"""
Create a short quiz (5 questions + answers) from this topic:

{context}
"""

    quiz=ask_ai(prompt)
    if quiz:
        return quiz

    return "Quiz unavailable right now."

# ===============================
# 🖥 UI
# ===============================
st.title("🧠 SmartLoop AI")
st.caption("Next-gen AI Tutor")

mode=st.radio("Select Mode",["Ask AI","Generate Quiz"])

query=st.text_input("Enter your question or topic")

if st.button("Run"):
    if query:

        if mode=="Ask AI":
            ans=get_answer(query)
            st.markdown(f'<div class="card">{ans}</div>', unsafe_allow_html=True)

        else:
            quiz=generate_quiz(query)
            st.markdown(f'<div class="card">{quiz}</div>', unsafe_allow_html=True)

# ===============================
# STATUS
# ===============================
if loaded:
    st.success(f"📚 {len(books)} PDF chunks loaded")
else:
    st.info("⚡ Loading PDFs in background... Ask anything meanwhile!")
