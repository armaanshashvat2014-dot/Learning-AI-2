import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import os
import re

st.set_page_config(
    page_title="MentorLoop Smart Study AI",
    page_icon="📚",
    layout="wide"
)

api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Missing GEMINI_API_KEY in Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

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
            except Exception:
                pass
    return pages

books = load_books()

def search_pages(question):
    words = clean_text(question).split()
    best_page = None
    best_score = 0
    for page in books:
        score = sum(page["clean"].count(word) for word in words)
        if score > best_score:
            best_score = score
            best_page = page
    return best_page

def ask_ai(question, context):
    prompt = f"""
You are MentorLoop Smart Study AI.
Answer ONLY using the textbook content below.
Do not invent information.
Keep the explanation simple for students.

TEXTBOOK PAGE:
{context[:7000]}

QUESTION:
{question}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI error: {str(e)}"

st.title("📚 MentorLoop Smart Study AI")
st.caption("Searches every textbook page and answers from your books")
st.write(f"📘 Pages indexed: {len(books)}")

question = st.text_input("Ask a question from your textbook")

if st.button("Search"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Searching textbooks..."):
            match = search_pages(question)
            if not match:
                st.error("No matching textbook found.")
            else:
                answer = ask_ai(question, match["text"])
                st.success("Answer")
                st.write(answer)
                st.info(f"Source: {match['file']} | Page {match['page']}")
