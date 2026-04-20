import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import os
import re
import time

st.set_page_config(
    page_title="MentorLoop Smart Study AI",
    page_icon="📚",
    layout="wide"
)

PDF_FOLDER = "."

# ======================================
# KEY ROTATION
# Load all keys: GEMINI_API_KEY_1, _2, _3 ...
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
    # Also accept a single GEMINI_API_KEY for backwards compatibility
    single = st.secrets.get("GEMINI_API_KEY")
    if single and single not in keys:
        keys.append(single)
    return keys

API_KEYS = get_api_keys()
if not API_KEYS:
    st.error("No API keys found. Add GEMINI_API_KEY_1, GEMINI_API_KEY_2 ... to Streamlit secrets.")
    st.stop()

def get_next_key():
    """Round-robin key selector using session state."""
    if "key_index" not in st.session_state:
        st.session_state.key_index = 0
    key = API_KEYS[st.session_state.key_index % len(API_KEYS)]
    st.session_state.key_index += 1
    return key

# ======================================
# CLEAN TEXT
# ======================================
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    return text

# ======================================
# LOAD ALL PDF PAGES
# ======================================
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

# ======================================
# SEARCH
# ======================================
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

# ======================================
# ASK GEMINI — tries all keys on 429
# ======================================
def ask_ai(question, context):
    prompt = f"""
You are MentorLoop Smart Study AI.
Answer ONLY using the textbook content below.
Do not invent information.
Keep the explanation simple for students.

TEXTBOOK PAGE:
{context[:3000]}

QUESTION:
{question}
"""
    # Try each key once before giving up
    for attempt in range(len(API_KEYS)):
        key = get_next_key()
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error = str(e)
            if "429" in error:
                # This key is rate limited, try the next one
                continue
            else:
                return f"AI error: {error}"

    # All keys exhausted — wait and retry once
    time.sleep(15)
    try:
        genai.configure(api_key=API_KEYS[0])
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "All API keys are temporarily rate limited. Please try again in a minute."

# ======================================
# UI
# ======================================
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
                st.error("No matching textbook content found.")
            else:
                answer = ask_ai(question, match["text"])
                st.success("Answer")
                st.write(answer)
                st.info(f"Source: {match['file']} | Page {match['page']}")
