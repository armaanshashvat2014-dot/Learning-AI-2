import streamlit as st
from PyPDF2 import PdfReader
from openai import OpenAI
import os
import re

st.set_page_config(page_title="MentorLoop Smart Study AI")

api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OPENAI_API_KEY")
    st.stop()

client = OpenAI(api_key=api_key)

# PDFs are in repo root
PDF_FOLDER = "."


def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    return text


@st.cache_resource
def load_books():
    pages = []

    for file in os.listdir(PDF_FOLDER):
        if file.lower().endswith(".pdf"):
            try:
                reader = PdfReader(file)

                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()

                    if text and len(text.strip()) > 20:
                        pages.append({
                            "file": file,
                            "page": page_num + 1,
                            "text": text,
                            "clean": clean_text(text)
                        })

            except Exception as e:
                st.warning(f"Could not read {file}")

    return pages


books = load_books()


def search_pages(question):
    words = clean_text(question).split()

    best_page = None
    best_score = 0

    for page in books:
        score = 0

        for word in words:
            score += page["clean"].count(word)

        if score > best_score:
            best_score = score
            best_page = page

    return best_page


def ask_ai(question, context):
    prompt = f"""
Answer ONLY using this textbook page.

TEXT:
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


st.title("📚 MentorLoop Smart Study AI")
st.caption("Searches every textbook page instantly")

st.write("Books loaded:", len(books))

question = st.text_input("Ask a question")

if st.button("Search"):
    if not question:
        st.warning("Enter a question")
    else:
        match = search_pages(question)

        if not match:
            st.error("No matching textbook found.")
        else:
            answer = ask_ai(question, match["text"])
            st.success(answer)
            st.info(f"{match['file']} | Page {match['page']}")
