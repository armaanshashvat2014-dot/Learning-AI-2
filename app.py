import streamlit as st
from PyPDF2 import PdfReader
import os, re, random

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("📚 Grade-based • Chapter-aware • Smart Questions")

# ===============================
# SELECT GRADE + MODE
# ===============================
grade = st.sidebar.selectbox("Select Grade", ["6","7","8"])
mode = st.sidebar.selectbox("Mode", ["Tutor","Teacher","Quiz","Test"])

# ===============================
# LOAD PDFs BY GRADE
# ===============================
@st.cache_resource
def load_books():
    data = []

    for f in os.listdir("."):
        if f.endswith(".pdf"):

            if f"_{grade}" in f or f"grade{grade}" in f.lower():

                try:
                    reader = PdfReader(f)

                    for page in reader.pages:
                        text = page.extract_text()

                        if text:
                            text = text.lower()

                            for chunk in text.split(". "):
                                if 50 < len(chunk) < 200:
                                    data.append({
                                        "text": chunk,
                                        "file": f
                                    })

                except:
                    pass

    return data

kb = load_books()

# ===============================
# FIND CHAPTER CONTENT
# ===============================
def get_chapter(topic):

    topic = topic.lower()
    results = []

    for item in kb:
        score = 0

        if topic in item["text"]:
            score += 5

        for w in topic.split():
            if w in item["text"]:
                score += 2

        if score > 0:
            results.append((score, item))

    results.sort(reverse=True)

    return [r[1] for r in results[:5]]

# ===============================
# QUESTION GENERATOR
# ===============================
def generate_questions(topic):

    topic = topic.lower()

    # math topics
    if "fraction" in topic:
        return [
            "1/2 + 1/4",
            "3/5 + 2/5",
            "4/7 - 1/7",
            "Convert 3/4 to decimal",
            "What is 2/3 of 12?"
        ]

    if "exponent" in topic or "indice" in topic:
        return [
            "2^3",
            "5^2",
            "3^4",
            "Simplify 2^3 × 2^2",
            "What is 10^0?"
        ]

    # fallback
    return [
        f"{random.randint(1,20)} + {random.randint(1,20)}"
        for _ in range(5)
    ]

# ===============================
# EXPLAIN
# ===============================
def explain(text):
    return f"""
📘 Explanation:
{text}

💡 Simple:
{text.split('.')[0]}.
"""

# ===============================
# MAIN UI
# ===============================
topic = st.text_input("Enter Chapter / Topic")

if topic:

    chapter_data = get_chapter(topic)

    if mode == "Tutor":
        if chapter_data:
            st.write(explain(chapter_data[0]["text"]))
            st.caption(f"📖 {chapter_data[0]['file']}")
        else:
            st.write("No chapter found.")

    elif mode == "Teacher":
        if chapter_data:
            st.write(explain(chapter_data[0]["text"]))

            st.subheader("📝 Practice")
            for q in generate_questions(topic):
                st.write("-", q)

    elif mode == "Quiz":
        st.subheader("📝 Quiz")
        for q in generate_questions(topic):
            st.write("•", q)

    elif mode == "Test":

        if st.button("Start Test"):
            st.session_state.qs = generate_questions(topic)
            st.session_state.ans = [""] * len(st.session_state.qs)

        if "qs" in st.session_state:
            for i, q in enumerate(st.session_state.qs):
                st.session_state.ans[i] = st.text_input(q, key=i)

            if st.button("Submit"):
                score = 0

                for i, q in enumerate(st.session_state.qs):
                    try:
                        correct = eval(q.replace("^","**"))
                        if str(correct) == st.session_state.ans[i]:
                            score += 1
                    except:
                        pass

                st.write(f"Score: {score}/{len(st.session_state.qs)}")

# ===============================
# STATUS
# ===============================
st.write(f"📚 Loaded content: {len(kb)} chunks")
