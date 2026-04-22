import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.markdown("""
<style>
.main {background: linear-gradient(135deg,#0b1020,#050816); color:white;}
.stTextInput input {background:#1c223a; border-radius:12px; color:white;}
.stButton button {background:#0072ff; color:white; border-radius:10px;}
.card {background:#121a35; padding:20px; border-radius:15px; margin-top:10px; color:white;}
</style>
""", unsafe_allow_html=True)

st.title("🧠 SmartLoop AI")
st.caption("⚡ Use format → Subject: Your Question (faster answers)")

# ======================================
# API KEYS
# ======================================
def get_keys(prefix):
    keys = []
    i = 1
    while True:
        k = st.secrets.get(f"{prefix}_{i}")
        if not k:
            break
        keys.append(k)
        i += 1
    single = st.secrets.get(prefix)
    if single and single not in keys:
        keys.append(single)
    return keys

GEMINI_KEYS = get_keys("GEMINI_API_KEY")
OPENAI_KEYS = get_keys("OPENAI_API_KEY")

if not GEMINI_KEYS and not OPENAI_KEYS:
    st.error("No API keys found. Add them to Streamlit Secrets.")
    st.stop()

# Debug sidebar
st.sidebar.write(f"Gemini keys loaded: {len(GEMINI_KEYS)}")
st.sidebar.write(f"OpenAI keys loaded: {len(OPENAI_KEYS)}")

# ======================================
# PDF LOADING
# ======================================
@st.cache_resource
def load_pdfs():
    data = []
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader = PdfReader(f)
                for p in reader.pages:
                    txt = p.extract_text()
                    if txt and len(txt.strip()) > 20:
                        data.append(txt[:1200])
            except:
                pass
    return data

with st.spinner("Loading library..."):
    books = load_pdfs()

pdf_loaded = len(books) > 0

# ======================================
# PDF SEARCH
# ======================================
def search_pdf(q):
    if not books:
        return ""
    best = ""
    score_max = 0
    words = set(q.lower().split())
    stopwords = {
        "what","is","are","how","why","when","who","the","a","an",
        "of","in","to","and","does","do","explain","define","tell",
        "me","about","give","can","you","please","describe"
    }
    words = words - stopwords
    for b in books:
        score = len(words & set(b.lower().split()))
        if score > score_max:
            score_max = score
            best = b
    return best[:1000] if score_max > 1 else ""

# ======================================
# WIKIPEDIA
# ======================================
def wiki(q):
    try:
        return wikipedia.summary(q, sentences=3, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            return wikipedia.summary(e.options[0], sentences=3)
        except:
            return ""
    except:
        return ""

# ======================================
# AI CALLS
# ======================================
def ask_gemini(prompt):
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel("gemini-2.0-flash")
            return model.generate_content(prompt).text
        except Exception as e:
            st.sidebar.warning(f"Gemini error: {str(e)[:120]}")
            continue
    return None

def ask_openai(prompt):
    for k in OPENAI_KEYS:
        try:
            client = openai.OpenAI(api_key=k)
            r = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400
            )
            return r.choices[0].message.content
        except Exception as e:
            st.sidebar.warning(f"OpenAI error: {str(e)[:120]}")
            continue
    return None

# ======================================
# MASTER AI
# ======================================
def master_ai(question, context=""):
    prompt = f"""
You are SmartLoop AI, a helpful tutor for students.
Answer clearly and simply. Use the context if relevant.

Context:
{context}

Question:
{question}
"""
    results = []

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = [
            ex.submit(ask_gemini, prompt),
            ex.submit(ask_openai, prompt)
        ]
        for f in as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    wiki_res = wiki(question)
    if wiki_res:
        results.append(wiki_res)

    if not results:
        return "AI temporarily unavailable. Check API keys in the sidebar."

    if len(results) == 1:
        return results[0]

    combined = "\n\n".join(results)
    combine_prompt = f"""
Combine these answers into ONE clear, simple answer for a student.
Remove repetition. Do not mention sources.

Question: {question}

Answers:
{combined}

Final answer:
"""
    final = ask_gemini(combine_prompt) or ask_openai(combine_prompt)
    return final if final else results[0]

# ======================================
# ANSWER ENGINE
# ======================================
def get_answer(query):
    if ":" in query:
        _, q = query.split(":", 1)
        q = q.strip()
    else:
        q = query.strip()

    if not pdf_loaded:
        return ask_gemini(q) or ask_openai(q) or "AI temporarily unavailable."

    context = search_pdf(q)
    return master_ai(q, context)

# ======================================
# QUIZ GENERATOR
# ======================================
def generate_quiz(topic, num_q):
    if not pdf_loaded:
        context = f"General knowledge about {topic}"
    else:
        context = search_pdf(topic)
        if not context:
            context = f"General knowledge about {topic}"

    questions = []
    for i in range(num_q):

        q_prompt = f"""
You are an IGCSE examiner. Write ONE real exam question about "{topic}".
Use this context if helpful: {context[:600]}

Write exactly in this format:
(a) [Simple recall question about {topic}] [2 marks]
(b) [Explanation question about {topic}] [3 marks]
(c) [Application or calculation question about {topic}] [3 marks]

Write actual exam questions, not placeholders. Replace the brackets with real questions.
"""

        ms_prompt = f"""
You are an IGCSE examiner. Write a detailed mark scheme for an exam question about "{topic}".
Context: {context[:600]}

Write exactly in this format:
(a) [2 marks]
- Award 1 mark for: [specific marking point 1]
- Award 1 mark for: [specific marking point 2]

(b) [3 marks]
- Award 1 mark for: [specific marking point 1]
- Award 1 mark for: [specific marking point 2]
- Award 1 mark for: [specific marking point 3]

(c) [3 marks]
- Award 1 mark for: [specific marking point 1]
- Award 1 mark for: [specific marking point 2]
- Award 1 mark for: [specific marking point 3]

Be specific to "{topic}". Replace brackets with real marking points.
"""

        q_text = ask_gemini(q_prompt) or ask_openai(q_prompt)
        ms_text = ask_gemini(ms_prompt) or ask_openai(ms_prompt)

        if not q_text:
            q_text = "AI unavailable. Check your API keys in the sidebar."
        if not ms_text:
            ms_text = "AI unavailable. Check your API keys in the sidebar."

        questions.append({"q": q_text, "ms": ms_text})

    return questions, None

# ======================================
# UI
# ======================================
mode = st.radio("Mode", ["Tutor", "Quiz"])
query = st.text_input(
    "Enter your question or topic",
    placeholder="e.g. Physics: What is sound?"
)
num_q = st.selectbox("Number of Questions", [1, 2, 3, 5])

if st.button("Run"):
    if not query.strip():
        st.warning("Please enter a question or topic.")
    elif mode == "Tutor":
        with st.spinner("Thinking..."):
            ans = get_answer(query)
        st.markdown(
            f'<div class="card">{ans}</div>',
            unsafe_allow_html=True
        )
    else:
        with st.spinner("Generating quiz..."):
            quiz, err = generate_quiz(query, num_q)
        if err:
            st.warning(err)
        else:
            st.session_state.quiz = quiz
            st.session_state.quiz_topic = query

# ======================================
# DISPLAY QUIZ
# ======================================
if "quiz" in st.session_state:
    st.markdown("## 📄 Quiz")
    for i, q in enumerate(st.session_state.quiz):
        st.markdown(f"### Question {i+1}")
        st.markdown(q["q"])
        st.text_area("Your Answer", key=f"ans_{i}", height=120)
        if st.button(f"Show Mark Scheme", key=f"ms_{i}"):
            st.info(q["ms"])
    st.divider()

# ======================================
# STATUS BAR
# ======================================
col1, col2, col3 = st.columns(3)
with col1:
    if pdf_loaded:
        st.success(f"📚 {len(books)} PDF chunks loaded")
    else:
        st.info("No PDFs found")
with col2:
    st.info(f"🔑 {len(GEMINI_KEYS)} Gemini key(s)")
with col3:
    st.info(f"🔑 {len(OPENAI_KEYS)} OpenAI key(s)")
