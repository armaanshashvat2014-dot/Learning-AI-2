import json
import os
import re
import time
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


# ----------------------------- #
# 1) CONFIG & API KEY #
# ----------------------------- #
st.set_page_config(page_title="helix.ai - Cambridge (CIE) Tutor", page_icon="📚", layout="wide")

PROVIDED_API_KEY = "AIzaSyCJ5kTedYLBjbTsCt9p7NBsbE-jsfH7sxM"
api_key = os.getenv("GEMINI_API_KEY") or PROVIDED_API_KEY

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"🚨 API Key Error: {e}")
    st.stop()

MODEL_CANDIDATES = ["gemini-2.0-flash", "gemini-1.5-flash"]
PDF_ROOT = Path(".")

# ----------------------------- #
# 2) STYLING (Glassmorphism) #
# ----------------------------- #
st.markdown(
    """
<style>
    .stApp { background: radial-gradient(800px circle at 50% 0%, rgba(0, 212, 255, 0.12), rgba(0, 212, 255, 0.00) 60%), #0a0a1a !important; color: #f5f5f7 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { background: rgba(255, 255, 255, 0.04) !important; backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 20px; }
    .big-title { color: #00d4ff; text-align: center; font-size: 40px; font-weight: 800; text-shadow: 0 0 10px rgba(0, 212, 255, 0.4); }
    .stButton>button { width: 100%; border-radius: 12px; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); transition: 0.3s; }
    .stButton>button:hover { background: #00d4ff; color: black; border-color: #00d4ff; }
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------- #
# 3) SESSION STATE & HELPERS #
# ----------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 I'm Helix! I'm ready to help you with Math, Science, or English. What's on your mind?",
        }
    ]
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False


@st.cache_data(show_spinner=False)
def get_pdf_text_preview(pdf_path: str, max_pages: int = 8, max_chars: int = 12000) -> str:
    """Extract a lightweight preview from a textbook for retrieval grounding."""
    if PdfReader is None:
        return ""

    try:
        reader = PdfReader(pdf_path)
        snippets = []
        pages_to_read = min(max_pages, len(reader.pages))
        for page_index in range(pages_to_read):
            text = reader.pages[page_index].extract_text() or ""
            if text.strip():
                snippets.append(f"[p.{page_index + 1}] {text.strip()}")
            if sum(len(x) for x in snippets) > max_chars:
                break
        joined = "\n\n".join(snippets)
        return joined[:max_chars]
    except Exception:
        return ""


def list_candidate_books(grade: str, subject: str) -> list[Path]:
    """Find best matching local PDFs for the learner's grade and subject."""
    normalized_grade = "".join(ch for ch in grade if ch.isdigit())
    subject_map = {
        "Math": ["Math"],
        "Science": ["Sci", "Science"],
        "English": ["Eng", "English"],
    }
    subject_keys = subject_map.get(subject, [subject])

    all_pdfs = sorted(PDF_ROOT.glob("*.pdf"))
    grade_filtered = [p for p in all_pdfs if f"_{normalized_grade}_" in p.name or f"_{normalized_grade}." in p.name or f" {normalized_grade}" in p.name]

    subject_filtered = []
    for pdf in grade_filtered:
        if any(key.lower() in pdf.name.lower() for key in subject_keys):
            subject_filtered.append(pdf)

    # If no strict subject match, fall back to grade-level books
    return subject_filtered[:3] if subject_filtered else grade_filtered[:3]


def build_curriculum_context(grade: str, subject: str) -> tuple[str, list[str]]:
    books = list_candidate_books(grade, subject)
    context_blocks = []
    used_sources = []

    for book in books:
        preview = get_pdf_text_preview(str(book))
        if preview:
            context_blocks.append(f"SOURCE: {book.name}\n{preview}")
            used_sources.append(book.name)

    context = "\n\n---\n\n".join(context_blocks)
    return context, used_sources


def get_ai_response(prompt: str, system_instruction: str, context: str = "") -> str:
    combined_prompt = prompt
    if context:
        combined_prompt = (
            "Use the provided curriculum context to answer accurately. "
            "If context is insufficient, say what is missing and then still help clearly.\n\n"
            f"CURRICULUM_CONTEXT:\n{context}\n\n"
            f"STUDENT_QUESTION:\n{prompt}"
        )

    last_error = None
    for model_name in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=combined_prompt,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
            if response.text:
                return response.text
        except Exception as e:
            last_error = e
            continue

    return f"⚠️ Error: {str(last_error) if last_error else 'Unknown model failure.'}"


def generate_quiz_with_retry(quiz_prompt: str, quiz_sys: str, retries: int = 2):
    for _ in range(retries + 1):
        raw_json = get_ai_response(quiz_prompt, quiz_sys)
        clean_json = re.sub(r"```json\n?|\n?```", "", raw_json).strip()
        try:
            data = json.loads(clean_json)
            if isinstance(data, list) and all(
                isinstance(q, dict) and {"question", "options", "correct_answer"}.issubset(q.keys()) for q in data
            ):
                return data
        except Exception:
            pass
    return None


# ----------------------------- #
# 4) LOGIN / SIGN UP PANEL #
# ----------------------------- #
if st.session_state.user_data is None:
    st.markdown("<div class='big-title'>helix.ai</div>", unsafe_allow_html=True)
    with st.container():
        st.subheader("🚀 Join the Learning Revolution")
        col1, col2 = st.columns(2)
        name = col1.text_input("Name")
        email = col2.text_input("Email")
        grade = st.selectbox("Your Grade", ["Grade 6", "Grade 7", "Grade 8"])

        if st.button("Start Learning Now"):
            if name and email:
                st.session_state.user_data = {"name": name, "email": email, "grade": grade}
                st.rerun()
            else:
                st.warning("Please enter your name and email.")
    st.stop()

# ----------------------------- #
# 5) SIDEBAR NAVIGATION #
# ----------------------------- #
with st.sidebar:
    st.markdown(f"### 🎓 Welcome, {st.session_state.user_data['name']}!")
    st.write(f"Grade: {st.session_state.user_data['grade']}")
    st.divider()
    app_mode = st.radio("Switch Mode", ["💬 AI Tutor", "⚡ Interactive Quiz"])

    st.markdown("### 🧠 Intelligence Controls")
    smart_mode = st.toggle("Smart Tutor Mode", value=True, help="Enables deeper reasoning and cleaner structure.")
    grounding_mode = st.toggle(
        "Ground Answers in Local Books",
        value=True,
        help="Retrieves relevant context from local CIE PDFs for better factual alignment.",
    )
    depth = st.select_slider("Reasoning Depth", options=["Standard", "Deep", "Olympiad"], value="Deep")

    if st.button("Clear History"):
        st.session_state.messages = [{"role": "assistant", "content": "Memory cleared! How can I help?"}]
        st.rerun()
    if st.button("Logout"):
        st.session_state.user_data = None
        st.rerun()

# ----------------------------- #
# 6) AI TUTOR MODE #
# ----------------------------- #
if app_mode == "💬 AI Tutor":
    st.markdown("<div class='big-title'>📚 helix.ai Tutor</div>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if chat_input := st.chat_input("Ask a question (e.g., 'Explain photosynthesis' or 'Solve 2x + 5 = 15')"):
        st.session_state.messages.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                base_inst = (
                    "You are Helix, an elite CIE tutor for middle-school learners. "
                    "Use clear markdown formatting, concise step-by-step logic, and check for student misconceptions. "
                    "Always end with a short 'Try this next' practice prompt."
                )

                if smart_mode:
                    smart_inst = {
                        "Standard": "Give a simple, accurate answer.",
                        "Deep": "Use diagnostic reasoning: identify concept gaps and provide scaffolded explanation.",
                        "Olympiad": "Offer advanced challenge insights after solving the base problem clearly.",
                    }[depth]
                    base_inst = f"{base_inst} {smart_inst}"

                context = ""
                sources = []
                if grounding_mode:
                    context, sources = build_curriculum_context(
                        grade=st.session_state.user_data["grade"],
                        subject="Math" if "math" in chat_input.lower() else "Science" if "science" in chat_input.lower() else "English",
                    )

                response = get_ai_response(chat_input, base_inst, context=context)
                if sources:
                    response += "\n\n---\n**Grounded with:** " + ", ".join(f"`{s}`" for s in sources)

                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# ----------------------------- #
# 7) QUIZ ENGINE MODE #
# ----------------------------- #
else:
    st.markdown("<div class='big-title'>⚡ Interactive Quiz</div>", unsafe_allow_html=True)

    if not st.session_state.quiz_active:
        with st.form("quiz_config"):
            st.write("Configure your practice test:")
            c1, c2 = st.columns(2)
            q_subject = c1.selectbox("Subject", ["Math", "Science", "English"])
            q_num = c2.slider("Number of Questions", 3, 10, 5)
            q_topic = st.text_input("Specific Topic (e.g. Fractions, Electricity, Grammar)")

            if st.form_submit_button("Generate Quiz Now"):
                with st.spinner("Helix is crafting your unique questions..."):
                    quiz_sys = (
                        "You are a strict quiz engine. "
                        "Output only raw JSON array of objects with keys: "
                        "question, options (4), correct_answer, explanation, difficulty."
                    )
                    quiz_prompt = (
                        f"Create a {q_num} question {q_subject} quiz on {q_topic or 'mixed topics'} "
                        f"for {st.session_state.user_data['grade']} students. "
                        "Return ONLY raw JSON."
                    )

                    quiz_data = generate_quiz_with_retry(quiz_prompt, quiz_sys, retries=2)
                    if quiz_data:
                        st.session_state.quiz_questions = quiz_data
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_active = True
                        st.session_state.current_q_idx = 0
                        st.rerun()
                    else:
                        st.error("Failed to generate quiz after retries. Please try again.")

    else:
        idx = st.session_state.current_q_idx
        questions = st.session_state.quiz_questions

        if idx < len(questions):
            q_data = questions[idx]
            st.subheader(f"Question {idx + 1} of {len(questions)}")
            st.write(q_data["question"])
            if q_data.get("difficulty"):
                st.caption(f"Difficulty: {q_data['difficulty']}")

            for option in q_data["options"]:
                if st.button(option, key=f"opt_{idx}_{option}"):
                    if option == q_data["correct_answer"]:
                        st.success(f"Correct! 🎉 {q_data.get('explanation', '')}")
                        st.session_state.quiz_score += 1
                        time.sleep(2)
                    else:
                        st.error(
                            f"Wrong! The correct answer was: {q_data['correct_answer']}. {q_data.get('explanation', '')}"
                        )
                        time.sleep(3)

                    st.session_state.current_q_idx += 1
                    st.rerun()
        else:
            st.balloons()
            st.markdown("### 🏁 Quiz Complete!")
            st.markdown(f"## Your Score: {st.session_state.quiz_score} / {len(questions)}")
            if st.button("Start New Quiz"):
                st.session_state.quiz_active = False
                st.rerun()
