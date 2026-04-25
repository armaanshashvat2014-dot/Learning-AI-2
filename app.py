import streamlit as st
from PyPDF2 import PdfReader
import os, re, random
import wikipedia

st.set_page_config(page_title="SmartLoop AI", layout="wide")

st.title("🧠 SmartLoop AI")
st.caption("📚 Learn • Practice • Test • Solve")

# ===============================
# MODE
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
# SEARCH
# ===============================
def search_kb(query):
    query = query.lower()
    words = query.split()

    results = []
    for item in kb:
        score = 0
        for w in words:
            if w in item["text"]:
                score += 2
        if query in item["text"]:
            score += 5

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:3]]

# ===============================
# GET CONTENT
# ===============================
def get_content(q):
    text = ""
    source = ""

    results = search_kb(q)

    if results:
        text = results[0]["text"]
        source = f"📖 {results[0]['source']}"

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
def explain(text):
    if not text:
        return "No explanation found."

    return f"""
📘 Explanation:
{text[:500]}

💡 Simple:
{text.split('.')[0]}.
"""

# ===============================
# QUESTION GENERATOR
# ===============================
def generate_questions(text, topic):

    sentences = [s for s in text.split(". ") if len(s) > 40]
    random.shuffle(sentences)

    questions = []

    for s in sentences[:5]:

        style = random.choice(["what","explain","fill"])

        if style == "what":
            q = f"What is meant by: {s[:50]}?"

        elif style == "explain":
            q = f"Explain: {s[:60]}"

        else:
            words = s.split()
            if len(words) > 6:
                blank = words[random.randint(2, len(words)-3)]
                q = s.replace(blank, "_____")
            else:
                q = f"Fill in: {s}"

        questions.append(q)

    if not questions:
        questions = [
            f"What is {topic}?",
            f"Explain {topic}"
        ]

    return questions

# ===============================
# MATH ENGINE
# ===============================
def is_math(q):
    q = q.lower().strip()

    if re.search(r"\d+\s*[\+\-\*/\^]\s*\d+", q):
        return True

    if re.match(r"^[0-9\+\-\*/\^\.\s]+$", q):
        return True

    keywords = ["plus","minus","times","divide","square","cube"]
    return any(k in q for k in keywords)

def parse_math(q):
    q = q.lower()
    q = q.replace("plus","+").replace("minus","-")
    q = q.replace("times","*").replace("multiply","*")
    q = q.replace("divide","/")
    q = q.replace("^","**")

    q = re.sub(r"square (\d+)", r"(\1**2)", q)
    q = re.sub(r"cube (\d+)", r"(\1**3)", q)

    return q

def solve_math(q):
    try:
        expr = parse_math(q)
        return str(eval(expr, {"__builtins__": None}, {}))
    except:
        return None

# ===============================
# ANSWER ENGINE
# ===============================
def get_answer(q):

    # 🧮 MATH FIRST
    if is_math(q):
        ans = solve_math(q)
        if ans:
            return f"🧮 Answer: {ans}", "Calculator"

    # 📚 KNOWLEDGE
    text, src = get_content(q)

    if text:
        return explain(text), src

    return "I couldn't find a clear answer.", "Fallback"

# ===============================
# UI
# ===============================
st.subheader("💬 Ask Your Doubt")
q = st.text_input("Enter topic or question")

# ===============================
# MODES
# ===============================
if q:

    text, src = get_content(q)
    ans, source = get_answer(q)

    # -------------------------
    # TUTOR
    # -------------------------
    if mode == "Tutor Mode":
        st.write(ans)
        st.caption(source)

    # -------------------------
    # TEACHER
    # -------------------------
    elif mode == "Teacher Mode":
        st.write(ans)
        st.caption(source)

        st.subheader("📝 Practice")
        for ques in generate_questions(text, q):
            st.write("-", ques)

    # -------------------------
    # QUIZ
    # -------------------------
    elif mode == "Quiz Mode":
        st.subheader("📝 Quiz")
        for ques in generate_questions(text, q):
            st.write("•", ques)

    # -------------------------
    # TEST
    # -------------------------
    elif mode == "Test Mode":

        if "test_started" not in st.session_state:
            st.session_state.test_started = False

        if not st.session_state.test_started:
            if st.button("Start Test"):
                st.session_state.test_started = True
                st.session_state.qs = generate_questions(text, q)
                st.session_state.ans = [""] * len(st.session_state.qs)

        if st.session_state.test_started:

            st.subheader("🧪 Test")

            for i, ques in enumerate(st.session_state.qs):
                st.session_state.ans[i] = st.text_input(
                    f"Q{i+1}. {ques}", key=f"t{i}"
                )

            if st.button("Submit Test"):

                score = 0

                for ans in st.session_state.ans:
                    if len(ans.strip()) > 3:
                        score += 1

                st.write(f"🎯 Score: {score}/{len(st.session_state.qs)}")
                st.success("✅ Test completed!")

                st.session_state.test_started = False

# ===============================
# STATUS
# ===============================
st.write(f"📚 Learned chunks: {len(kb)}")
