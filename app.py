import streamlit as st
from PyPDF2 import PdfReader
import os, re
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("📚 Learns from PDFs + Wikipedia • Generates questions • Stable")

# ===============================
# MODE SELECT
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

    bad = ["indb", "chapter", "exercise", "©", "http", "youtube"]
    if any(b in text for b in bad):
        return None

    text = re.sub(r'[^a-z0-9\s\.\-]', '', text)
    return text.strip()

# ===============================
# LOAD PDFs
# ===============================
@st.cache_resource
def load_kb():
    kb = []

    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader = PdfReader(f)

                for page in reader.pages:
                    text = page.extract_text()

                    if text:
                        text = clean_text(text)
                        if not text:
                            continue

                        for s in text.split(". "):
                            if 40 < len(s) < 200:
                                kb.append({
                                    "text": s,
                                    "source": f
                                })

            except:
                pass

    return kb

kb = load_kb()

# ===============================
# SEARCH KNOWLEDGE
# ===============================
def search_kb(query):
    query = query.lower()
    words = query.split()

    results = []

    for item in kb:
        text = item["text"]

        score = 0

        for w in words:
            if w in text:
                score += 2

        if query in text:
            score += 5

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in results[:3]]

# ===============================
# GET COMBINED CONTENT
# ===============================
def get_content(q):

    text = ""
    source = ""

    # 📚 PDF first
    results = search_kb(q)

    if results:
        text = results[0]["text"]
        source = f"📖 {results[0]['source']}"

    # 🌐 Wikipedia add
    try:
        wiki = wikipedia.summary(q, 2)
        text += " " + wiki
        source += " + 🌐 Wikipedia"
    except:
        pass

    return text.strip(), source

# ===============================
# EXPLAIN
# ===============================
def explain_topic(text):
    if not text:
        return "No explanation found."

    return f"""
📘 Explanation:
{text[:500]}

💡 Simple:
{text.split('.')[0]}.

🧠 Tip:
Focus on understanding the concept.
"""

# ===============================
# GENERATE QUESTIONS
# ===============================
def generate_questions(text, topic):

    questions = []
    sentences = text.split(". ")

    for s in sentences:
        if len(s) > 40 and len(questions) < 5:

            if " is " in s:
                q = s.replace(" is ", " is what? ")
            elif " are " in s:
                q = s.replace(" are ", " are what? ")
            else:
                q = f"What does this mean: {s[:50]}?"

            questions.append(q.strip())

    if not questions:
        questions = [
            f"What is {topic}?",
            f"Explain {topic}"
        ]

    return questions

# ===============================
# UI INPUT
# ===============================
st.subheader("💬 Ask Your Doubt")
q = st.text_input("Enter topic or question")

# ===============================
# MODES
# ===============================
if q:

    text, src = get_content(q)

    # =========================
    # 👨‍🏫 TUTOR MODE
    # =========================
    if mode == "Tutor Mode":
        st.write(explain_topic(text))
        st.caption(src)

    # =========================
    # 📘 TEACHER MODE
    # =========================
    elif mode == "Teacher Mode":
        st.write(explain_topic(text))
        st.caption(src)

        st.subheader("📝 Practice Questions")

        for ques in generate_questions(text, q):
            st.write("-", ques)

    # =========================
    # 📝 QUIZ MODE
    # =========================
    elif mode == "Quiz Mode":
        st.subheader("📝 Quiz")

        for ques in generate_questions(text, q):
            st.write("•", ques)

    # =========================
    # 🧪 TEST MODE
    # =========================
    elif mode == "Test Mode":

        if "test_started" not in st.session_state:
            st.session_state.test_started = False

        if not st.session_state.test_started:
            if st.button("Start Test"):
                st.session_state.test_started = True
                st.session_state.qs = generate_questions(text, q)
                st.session_state.ans = [""] * len(st.session_state.qs)

        if st.session_state.test_started:

            for i, ques in enumerate(st.session_state.qs):
                st.session_state.ans[i] = st.text_input(ques, key=f"t{i}")

            if st.button("Submit Test"):
                st.write("✅ Test submitted!")

# ===============================
# STATUS
# ===============================
st.write(f"📚 Learned chunks: {len(kb)}")
