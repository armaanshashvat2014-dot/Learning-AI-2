import streamlit as st
import re, os, time, itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
import wikipedia

from openai import OpenAI
from google import genai
import fitz  # pymupdf

# =========================
# GLOBAL SAFE INIT
# =========================
PDF_CHUNKS = []

# =========================
# PDF EXTRACTION (FITZ)
# =========================
def extract_pdf(fname):
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if len(text) > 60:
                words = set(
                    re.sub(r'[^a-z0-9 ]', ' ', text.lower()).split()
                )
                chunks.append({
                    "text": text[:1500],
                    "words": words,
                    "file": fname,
                    "page": page_num + 1
                })
        doc.close()
    except Exception as e:
        print(f"PDF ERROR in {fname}: {e}")
    return chunks

# =========================
# LOAD ALL PDFs
# =========================
def load_all_pdfs():
    all_chunks = []
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]

    for f in pdf_files:
        all_chunks.extend(extract_pdf(f))

    return all_chunks

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SmartLoop AI",
    page_icon="🧠",
    layout="wide"
)

# =========================
# PDF LOAD (IMPORTANT POSITION)
# =========================
with st.spinner("📚 Loading library..."):
    PDF_CHUNKS = load_all_pdfs()

# =========================
# CSS (UNCHANGED)
# =========================
st.markdown("""
<style>

.stApp {
    background: radial-gradient(800px circle at 50% 0%,
        rgba(0,212,255,0.10), rgba(0,212,255,0.00) 60%), #0a0a1a !important;
    color: #f5f5f7 !important;
    font-family: -apple-system, BlinkMacSystemFont,
        "Segoe UI", Roboto, sans-serif !important;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: rgba(12,12,22,0.92) !important;
    backdrop-filter: blur(40px) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}

/* CHAT MESSAGE */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(24px) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 24px !important;
    padding: 18px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2) !important;
    color: #fff !important;
    margin-bottom: 12px;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
}

[data-testid="stChatMessage"] * {
    color: #f5f5f7 !important;
}

[data-testid="stChatMessage"] pre,
[data-testid="stChatMessage"] code {
    white-space: pre-wrap !important;
    word-break: break-word !important;
}

/* INPUT BOX */
.stChatInputContainer {
    background: rgba(20,20,35,0.85) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 20px !important;
}

/* INPUT FIELDS */
.stTextInput>div>div>input,
.stTextArea>div>textarea,
.stSelectbox>div>div>div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #fff !important;
}

/* BUTTONS */
.stButton>button {
    background: linear-gradient(180deg,
        rgba(255,255,255,0.10) 0%,
        rgba(255,255,255,0.02) 100%) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 18px !important;
    backdrop-filter: blur(20px) !important;
    color: #fff !important;
    font-weight: 600 !important;
    transition: all 0.25s !important;
}

@media (hover: hover) and (pointer: fine) {
    .stButton>button:hover {
        background: linear-gradient(180deg,
            rgba(255,255,255,0.20) 0%,
            rgba(255,255,255,0.05) 100%) !important;
        border-color: rgba(255,255,255,0.35) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
    }
}

.stButton>button:active {
    transform: translateY(1px) !important;
}

/* THINKING ANIMATION */
.thinking-container {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.04);
    border-radius: 14px;
    margin: 8px 0;
    border-left: 3px solid #00d4ff;
}

.thinking-text {
    color: #00d4ff;
    font-size: 14px;
    font-weight: 600;
}

.thinking-dots {
    display: flex;
    gap: 4px;
}

.thinking-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #00d4ff;
    animation: tp 1.4s infinite;
}

.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes tp {
    0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
    30% { opacity: 1; transform: scale(1.2); }
}

/* BADGES */
.beta-badge {
    display: inline-block;
    background: linear-gradient(135deg, #ff4d6d, #7b2ff7);
    color: white;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
    box-shadow: 0 0 12px rgba(255,77,109,0.5);
    vertical-align: middle;
    margin-left: 10px;
}

.section-label {
    color: #00d4ff;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 12px 0 6px;
}

.welcome-card {
    background: linear-gradient(135deg,
        rgba(0,212,255,0.12),
        rgba(123,47,247,0.08));
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-weight: 600;
    color: #2ecc71;
    font-size: 14px;
}

/* SOURCE TAGS */
.source-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 6px;
}

.src-pdf {
    background: rgba(0,212,255,0.15);
    color: #00d4ff;
    border: 1px solid rgba(0,212,255,0.3);
}

.src-ai {
    background: rgba(252,132,4,0.15);
    color: #fc8404;
    border: 1px solid rgba(252,132,4,0.3);
}

.src-wiki {
    background: rgba(52,152,219,0.15);
    color: #3498db;
    border: 1px solid rgba(52,152,219,0.3);
}

.src-calc {
    background: rgba(155,89,182,0.2);
    color: #9b59b6;
    border: 1px solid rgba(155,89,182,0.4);
}

</style>
""", unsafe_allow_html=True)
# =========================
# API KEYS
# =========================
def get_secret(key):
    return st.secrets.get(key)

ALL_OPENAI_KEYS = [
    get_secret("OPENAI_API_KEY_1"),
    get_secret("OPENAI_API_KEY_2"),
    get_secret("OPENAI_API_KEY_3"),
    get_secret("OPENAI_API_KEY_4"),
]
ALL_OPENAI_KEYS = [k for k in ALL_OPENAI_KEYS if k]

ALL_GOOGLE_KEYS = [
    get_secret("GOOGLE_API_KEY_1"),
    get_secret("GOOGLE_API_KEY_2"),
    get_secret("GOOGLE_API_KEY_3"),
    get_secret("GOOGLE_API_KEY_4"),
]
ALL_GOOGLE_KEYS = [k for k in ALL_GOOGLE_KEYS if k]

# =========================
# GRADE SELECTION
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None

if st.session_state.grade is None:
    st.markdown("## Select your grade")

    grade = st.selectbox(
        "Grade",
        [f"Grade {i}" for i in range(1, 11)],
        index=5
    )

    if st.button("Start"):
        st.session_state.grade = int(grade.split()[1])
        st.rerun()

    st.stop()

# =========================
# SESSION STATE
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# =========================
# KEYWORD SEARCH
# =========================
STOPWORDS = {"what","is","are","how","why","when","who"}

def keyword_search(q):
    if not PDF_CHUNKS:
        return []

    q_words = set(re.sub(r'[^a-z0-9 ]', ' ', q.lower()).split()) - STOPWORDS

    scored = []
    for chunk in PDF_CHUNKS:
        score = len(q_words & chunk["words"])
        if score >= 2:
            scored.append((score, chunk))

    scored.sort(reverse=True)
    return scored[:5]

# =========================
# SIMPLE ANSWER PIPELINE
# =========================
def smartloop(q):
    results = keyword_search(q)

    if results:
        return results[0][1]["text"], "pdf"

    return "No PDF match found, using AI...", "ai"

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.success(f"📚 {len(PDF_CHUNKS)} pages loaded")

# =========================
# CHAT UI
# =========================
q = st.chat_input("Ask something...")

if q:
    st.chat_message("user").write(q)

    ans, tier = smartloop(q)

    st.chat_message("assistant").write(ans)
