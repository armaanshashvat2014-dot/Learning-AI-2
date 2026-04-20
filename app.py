import streamlit as st
from PyPDF2 import PdfReader
from openai import OpenAI
import os
import difflib

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="MentorLoop Smart Study AI",
    page_icon="📚",
    layout="wide"
)

# ===============================
# OPENAI KEY FROM STREAMLIT SECRET
# ===============================
client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

# ===============================
# BOOK FOLDER
# ===============================
PDF_FOLDER = "books"

# ===============================
# LOAD BOOKS
# ===============================
@st.cache_resource
def load_books():
    database = []

    if not os.path.exists(PDF_FOLDER):
        return database

    for filename in os.listdir(PDF_FOLDER):
        if filename.lower().endswith(".pdf"):
            path = os.path.join(PDF_FOLDER, filename)

            try:
                reader = PdfReader(path)
                text = ""

                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                database.append({
                    "file": filename,
                    "text": text
                })

            except Exception as e:
                st.warning(f"Could not load {filename}")

    return database


books = load_books()

# ===============================
# FIND BEST MATCH
# ===============================
def search_books(question):
    best_match = None
    best_score = 0

    for book in books:
        sample = book["text"][:5000]

        score = difflib.SequenceMatcher(
            None,
            question.lower(),
            sample.lower()
        ).ratio()

        if score > best_score:
            best_score = score
            best_match = book

    return best_match


# ===============================
# ASK OPENAI
# ===============================
def ask_ai(question, context):
    prompt = f"""
You are MentorLoop Smart Study AI.

Answer ONLY using the textbook information below.
Do not invent information.
If the answer is unclear, say:
"The answer is not clearly available in your textbook."

TEXTBOOK:
{context[:6000]}

QUESTION:
{question}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# ===============================
# UI
# ===============================
st.title("📚 MentorLoop Smart Study AI")
st.caption("Answers directly from your school textbooks")

question = st.text_input("Ask a question from your textbook")

if st.button("Get Answer"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Searching textbooks..."):
            match = search_books(question)

            if not match:
                st.error("No matching textbook found.")
            else:
                answer = ask_ai(question, match["text"])

                st.success("Answer")
                st.write(answer)

                st.info(f"📘 Source: {match['file']}")
