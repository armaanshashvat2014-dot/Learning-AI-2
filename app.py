import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="SmartLoop AI", layout="wide")

# ===============================
# UI
# ===============================
st.markdown("""
<style>
.main {background: linear-gradient(135deg,#0b1020,#050816); color:white;}
.stTextInput input {background:#1c223a; border-radius:12px; color:white;}
.stButton button {background:#0072ff; color:white; border-radius:10px;}
.card {background:#121a35; padding:20px; border-radius:15px; margin-top:10px;}
</style>
""", unsafe_allow_html=True)

st.title("🧠 SmartLoop AI")
st.caption("⚡ Use format → Subject: Your Question (e.g., Physics: What is force?)")

# ===============================
# API KEYS
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

GEMINI_KEYS = get_keys("GEMINI_API_KEY")
OPENAI_KEYS = get_keys("OPENAI_API_KEY")

# ===============================
# PDF BACKGROUND LOADING
# ===============================
books = []
pdf_loaded = False

def load_pdfs():
    global books, pdf_loaded
    data=[]
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader = PdfReader(f)
                for p in reader.pages:
                    txt = p.extract_text()
                    if txt:
                        data.append(txt[:1200])
            except:
                pass
    books = data
    pdf_loaded = True

threading.Thread(target=load_pdfs).start()

# ===============================
# PDF SEARCH
# ===============================
def search_pdf(q):
    if not books:
        return ""

    best=""
    score_max=0
    words=set(q.lower().split())

    for b in books:
        score=len(words & set(b.lower().split()))
        if score>score_max:
            score_max=score
            best=b

    return best[:1000]

# ===============================
# WIKIPEDIA
# ===============================
def wiki(q):
    try:
        return wikipedia.summary(q, sentences=3)
    except:
        return ""

# ===============================
# AI CALLS (3 PROVIDERS)
# ===============================
def ask_gemini(prompt):
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel("gemini-2.0-flash")
            return model.generate_content(prompt).text
        except:
            continue
    return None

def ask_openai(prompt):
    for k in OPENAI_KEYS:
        try:
            client = openai.OpenAI(api_key=k)
            r = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=400
            )
            return r.choices[0].message.content
        except:
            continue
    return None

# ===============================
# 🧠 MASTER AI (3 AI COMBINE)
# ===============================
def master_ai(question, context=""):

    prompt = f"""
You are SmartLoop AI tutor.

Answer clearly and correctly.

CONTEXT:
{context}

QUESTION:
{question}
"""

    results = []

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [
            ex.submit(ask_gemini, prompt),
            ex.submit(ask_openai, prompt),
            ex.submit(lambda p: wiki(question), prompt)
        ]

        for f in as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    if not results:
        return "Try rephrasing."

    # MASTER COMBINE
    combined = "\n\n".join(results)

    final_prompt = f"""
Combine the answers into one clear, correct explanation.

{combined}
"""

    final = ask_gemini(final_prompt)
    return final or results[0]

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(query):

    if ":" in query:
        subject, q = query.split(":",1)
    else:
        q = query

    # ⚡ If PDF not ready → Gemini only
    if not pdf_loaded:
        return ask_gemini(q) or "Loading PDFs..."

    # 📚 Use PDF context
    context = search_pdf(q)

    return master_ai(q, context)

# ===============================
# 🧪 QUIZ (PDF REQUIRED)
# ===============================
def generate_quiz(subject, topic, num_q):

    if not pdf_loaded:
        return "PDFs still loading. Quiz requires textbook knowledge."

    context = search_pdf(topic)

    questions=[]

    for i in range(num_q):

        q = f"""
Q{i+1}.

(a) Define {topic}. (2 marks)

(b) Explain using knowledge from text. (3 marks)

(c) Using this context:

{context[:200]}

Apply the concept. (3 marks)
"""

        ms = """
(a) Definition (2)
(b) Explanation (3)
(c) Application (3)
"""

        questions.append({"q":q,"ms":ms})

    return questions

# ===============================
# UI
# ===============================
mode = st.radio("Mode", ["Tutor","Quiz"])

query = st.text_input("Enter (Subject: Question or Topic)")

num_q = st.selectbox("Questions",[1,2,3,5])

if st.button("Run"):

    if mode=="Tutor":
        ans = get_answer(query)
        st.markdown(f'<div class="card">{ans}</div>', unsafe_allow_html=True)

    else:
        quiz = generate_quiz("", query, num_q)
        st.session_state.quiz = quiz

# ===============================
# DISPLAY QUIZ
# ===============================
if "quiz" in st.session_state:

    st.markdown("## 📄 IGCSE Quiz")

    for i,q in enumerate(st.session_state.quiz):
        st.markdown(q["q"])
        st.text_area(f"Answer Q{i+1}", key=f"a{i}")

        if st.button(f"Mark Scheme {i+1}", key=f"ms{i}"):
            st.info(q["ms"])

# ===============================
# STATUS
# ===============================
if pdf_loaded:
    st.success("📚 PDFs Ready")
else:
    st.info("⚡ PDFs loading in background...")
