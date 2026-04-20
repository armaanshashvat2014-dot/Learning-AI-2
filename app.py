import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import os
import re
import time

# ======================================
# CONFIGURATION
# ======================================
st.set_page_config(
    page_title="MentorLoop Smart Study AI",
    page_icon="📚",
    layout="wide"
)

# Use the latest model alias to prevent the 404 error
MODEL_NAME = "gemini-1.5-flash-latest"

# The folder where your pre-provided PDFs are stored
PDF_FOLDER = "."

# ======================================
# API KEY MANAGEMENT
# ======================================
def get_api_keys():
    keys = []
    i = 1
    while True:
        key = st.secrets.get(f"GEMINI_API_KEY_{i}")
        if not key:
            break
        keys.append(key)
        i += 1
    single = st.secrets.get("GEMINI_API_KEY")
    if single and single not in keys:
        keys.append(single)
    return keys

API_KEYS = get_api_keys()

if not API_KEYS:
    st.error("Missing API Keys! Add them to Streamlit Secrets.")
    st.stop()

def get_next_key():
    if "key_index" not in st.session_state:
        st.session_state.key_index = 0
    key = API_KEYS[st.session_state.key_index % len(API_KEYS)]
    st.session_state.key_index += 1
    return key

# ======================================
# PDF INDEXING (Background)
# ======================================
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    return text

@st.cache_resource
def load_and_index_books():
    """Automatically scans the folder for provided PDFs."""
    pages = []
    if not os.path.exists(PDF_FOLDER):
        return pages

    for file in os.listdir(PDF_FOLDER):
        if file.lower().endswith(".pdf"):
            try:
                # Ensure we use the full path to the pre-provided file
                path = os.path.join(PDF_FOLDER, file)
                reader = PdfReader(path)
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
                print(f"Error loading {file}: {e}")
                continue
    return pages

# Automatically load the library on startup
with st.spinner("Initializing library..."):
    books = load_and_index_books()

# ======================================
# SEARCH & AI LOGIC
# ======================================
def search_library(question):
    words = clean_text(question).split()
    if not words: return None

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
Answer ONLY using the provided textbook excerpt.
If the answer isn't there, say you can't find it in the current books.

TEXTBOOK EXCERPT:
{context[:4000]}

QUESTION:
{question}
"""
    for _ in range(len(API_KEYS)):
        key = get_next_key()
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e): continue
            return f"AI Error: {str(e)}"

    return "All systems busy. Please try again in a few seconds."

# ======================================
# USER INTERFACE
# ======================================
st.title("📚 MentorLoop Smart Study AI")
st.markdown(f"**Library Status:** {len(books)} pages indexed from pre-loaded textbooks.")

query = st.text_input("What would you like to learn today?", placeholder="e.g., Explain photosynthesis...")

if st.button("Search Library"):
    if not query.strip():
        st.warning("Please enter a question.")
    elif not books:
        st.error("Library is empty. Ensure PDFs are in the app folder.")
    else:
        with st.spinner("Scanning textbooks..."):
            match = search_library(query)
            if not match:
                st.error("No relevant information found in the library.")
            else:
                answer = ask_ai(query, match["text"])
                st.subheader("Answer")
                st.write(answer)
                st.caption(f"📍 Found in: **{match['file']}** (Page {match['page']})")
