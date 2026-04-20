import streamlit as st
from PyPDF2 import PdfReader
from openai import OpenAI
import os
import re

# ===================================
# PAGE CONFIG
# ===================================
st.set_page_config(
    page_title="MentorLoop Smart Study AI",
    page_icon="📚",
    layout="wide"
)

# ===================================
# OPENAI
# ===================================
api_key = st.secrets.get("OPENAI_API_KEY")

if not api_key:
    st.error("Missing OPENAI_API_KEY in Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# ===================================
# BOOK FOLDER
# ===================================
PDF_FOLDER = "books"

# ===================================
# CLEAN TEXT
# ===================================
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    return text

# ===================================
# LOAD ALL PAGES ONCE
# ===================================
@st.cache_resource
def load_books():
    pages_db = []

    if not os.path.exists(PDF_FOLDER):
        return pages_db

    for file in os.listdir(PDF_FOLDER):
        if file.lower().endswith(".pdf"):
            path = os.path.join(PDF_FOLDER, file)

            try:
                reader = PdfReader(path)

                for page_number, page in enumerate(reader.pages):
                    text = page.extract_text()

                    if text and len(text.strip()) > 30:
                        pages_db.append({
                            "file": file,
                            "page": page_number + 1,
                            "text": text,
                            "clean": clean_text(text)
                        })

            except:
                pass

    return pages_db

books = load_books()

# ===================================
# FAST PAGE SEARCH
# ===================================
def search_pages(question):
    q_words = clean_text(question).split()

    best_page = None
    best_score = 0

    for item in books:
        score = 0
        page_text = item["clean"]

        for word in q_words:
            score += page_text.count(word)

        if score > best_score:
            best_score = score
            best_page = item

    return best_page

# ===================================
# ASK AI
# ===================================
def ask_ai(question, context):
    prompt = f"""
You are MentorLoop Smart Study AI.

Answer ONLY using the textbook content below.
Do not invent information.
If the answer is unclear, say:
"The answer is not clearly available in your textbook."

TEXTBOOK PAGE:
{context}

QUESTION:
{question}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

# ===================================
# UI
# ===================================
st.title("📚 MentorLoop Smart Study AI")
st.caption("Searches every textbook page instantly")

question = st.text_input("Ask a question")

if st.button("Search"):
    if not question.strip():
        st.warning("Please type a question.")
    else:
        with st.spinner("Searching every textbook page..."):
            match = search_pages(question)

            if not match:
                st.error("No matching textbook found.")
            else:
                answer = ask_ai(question, match["text"])

                st.success("Answer")
                st.write(answer)

                st.info(
                    f"📘 Source: {match['file']} | Page {match['page']}"
                )
