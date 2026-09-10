import streamlit as st
import os
import re
import time
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from google import genai


# =============================================================================
# PAGE
# =============================================================================

st.set_page_config(
    page_title="SmartLoop AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# STYLE — NOTEBOOKLM-INSPIRED
# =============================================================================

st.markdown("""
<style>

:root {
    color-scheme: dark !important;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    color-scheme: dark !important;
}

.stApp {
    background:
        radial-gradient(
            900px circle at 50% -10%,
            rgba(87, 111, 255, 0.13),
            transparent 60%
        ),
        #0b0c10 !important;
    color: #f1f3f4 !important;
    font-family: Inter, -apple-system, BlinkMacSystemFont,
                 "Segoe UI", sans-serif !important;
}

/* Header */

[data-testid="stHeader"] {
    background: rgba(11,12,16,0.75) !important;
    backdrop-filter: blur(20px);
}

[data-testid="stHeader"] button {
    display: none !important;
}

/* Sidebar */

[data-testid="stSidebar"] {
    background: #111217 !important;
    border-right: 1px solid rgba(255,255,255,.07) !important;
}

[data-testid="stSidebar"] * {
    color: #eceef2;
}

/* Hide Streamlit chrome */

#MainMenu,
footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton {
    display: none !important;
}

/* Buttons */

.stButton > button {
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,.10) !important;
    background: rgba(255,255,255,.055) !important;
    color: #f5f5f7 !important;
    font-weight: 600 !important;
    transition: .18s ease !important;
}

.stButton > button:hover {
    background: rgba(255,255,255,.10) !important;
    border-color: rgba(255,255,255,.18) !important;
}

/* Primary */

button[kind="primary"] {
    background: linear-gradient(
        135deg,
        #5667ff,
        #7b61ff
    ) !important;
    border: none !important;
}

/* Inputs */

.stTextInput input,
.stTextArea textarea,
[data-baseweb="select"] {
    background: #17181e !important;
    color: #f5f5f7 !important;
    border-radius: 12px !important;
}

/* Chat */

[data-testid="stChatMessage"] {
    background: rgba(255,255,255,.045) !important;
    border: 1px solid rgba(255,255,255,.07) !important;
    border-radius: 18px !important;
    margin-bottom: 12px !important;
}

[data-testid="stChatMessage"] * {
    color: #f1f3f4 !important;
}

/* Chat input */

[data-testid="stChatInputContainer"] {
    background: rgba(20,21,27,.95) !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    border-radius: 18px !important;
}

/* Source cards */

.source-card {
    background: #17181e;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
    padding: 13px 14px;
    margin: 7px 0;
}

.source-title {
    font-weight: 700;
    font-size: 14px;
    color: #f5f5f7;
}

.source-meta {
    font-size: 11px;
    color: #90939d;
    margin-top: 4px;
}

/* Notebook title */

.notebook-title {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -.8px;
    color: #f5f5f7;
}

.notebook-subtitle {
    color: #92959f;
    font-size: 14px;
}

/* Pills */

.pill {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(91,105,255,.14);
    border: 1px solid rgba(91,105,255,.25);
    color: #9da8ff;
    font-size: 11px;
    font-weight: 700;
}

/* Citation */

.citation {
    display: inline-block;
    padding: 2px 7px;
    margin: 2px;
    border-radius: 6px;
    background: rgba(82, 139, 255, .13);
    border: 1px solid rgba(82,139,255,.25);
    color: #91b5ff !important;
    font-size: 11px;
}

/* Thinking */

.thinking {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 15px;
    color: #9ca3ff;
    background: rgba(91,105,255,.07);
    border-radius: 12px;
    border: 1px solid rgba(91,105,255,.14);
}

.dot {
    width: 6px;
    height: 6px;
    background: #7481ff;
    border-radius: 50%;
    display: inline-block;
    animation: pulse 1.2s infinite;
}

.dot:nth-child(2) { animation-delay: .2s; }
.dot:nth-child(3) { animation-delay: .4s; }

@keyframes pulse {
    0%,100% { opacity:.25; transform:scale(.8); }
    50% { opacity:1; transform:scale(1); }
}

/* Tabs */

button[data-baseweb="tab"] {
    color: #9da0aa !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #fff !important;
}

/* Divider */

hr {
    border-color: rgba(255,255,255,.07) !important;
}

</style>
""", unsafe_allow_html=True)


# =============================================================================
# API KEYS
# =============================================================================

def collect_keys(prefix):
    keys = []
    for i in range(1, 6):
        value = st.secrets.get(f"{prefix}_{i}")
        if value:
            keys.append(value)
    return keys


OPENAI_KEYS = collect_keys("OPENAI_API_KEY")
GOOGLE_KEYS = collect_keys("GOOGLE_API_KEY")
MY_API_KEY = st.secrets.get("MY_API_KEY")

if not OPENAI_KEYS and not GOOGLE_KEYS and not MY_API_KEY:
    st.error("No API keys found. Add OPENAI_API_KEY_1 or GOOGLE_API_KEY_1 to Streamlit secrets.")
    st.stop()


# =============================================================================
# SESSION STATE
# =============================================================================

defaults = {
    "notebooks": {},
    "current_notebook": None,
    "selected_sources": {},
    "notes": {},
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def make_id(text):
    return hashlib.md5(
        f"{text}-{time.time_ns()}".encode()
    ).hexdigest()[:12]


def create_notebook(name="New notebook"):
    notebook_id = make_id(name)
    st.session_state.notebooks[notebook_id] = {
        "name": name,
        "sources": {},
        "messages": [],
    }
    st.session_state.current_notebook = notebook_id
    st.session_state.selected_sources[notebook_id] = []


if not st.session_state.notebooks:
    create_notebook("My first notebook")


if st.session_state.current_notebook not in st.session_state.notebooks:
    st.session_state.current_notebook = next(
        iter(st.session_state.notebooks)
    )


NB = st.session_state.notebooks[st.session_state.current_notebook]


# =============================================================================
# LLM
# =============================================================================

def call_llm(messages, max_tokens=1200, temperature=0.2):

    # Google
    for key in GOOGLE_KEYS:
        try:
            client = genai.Client(api_key=key)

            prompt = "\n\n".join(
                f"{m['role'].upper()}:\n{m['content']}"
                for m in messages
            )

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            text = (response.text or "").strip()

            if len(text) > 10:
                return text

        except Exception as e:
            print("Gemini:", e)

    # OpenAI
    for key in OPENAI_KEYS:
        try:
            client = OpenAI(api_key=key)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            text = response.choices[0].message.content.strip()

            if len(text) > 10:
                return text

        except Exception as e:
            print("OpenAI:", e)

    # Custom API
    if MY_API_KEY:
        try:
            response = requests.post(
                "https://raujzsawwpmixwlcgcgs.supabase.co/functions/v1/public-ai-api",
                headers={
                    "Authorization": f"Bearer {MY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"messages": messages},
                timeout=45,
            )

            data = response.json()

            text = (
                data.get("response")
                or data.get("content")
                or data.get("message")
                or data.get("reply")
                or ""
            )

            if text:
                return str(text).strip()

        except Exception as e:
            print("Custom API:", e)

    return None


# =============================================================================
# PDF PROCESSING
# =============================================================================

def extract_pdf(file_bytes, filename):

    chunks = []

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_number, page in enumerate(doc, start=1):

            text = page.get_text("text").strip()

            if not text:
                continue

            text = re.sub(r"\s+", " ", text).strip()

            # Smaller chunks improve retrieval.
            words = text.split()

            chunk_size = 350

            for start in range(0, len(words), chunk_size):

                piece = " ".join(
                    words[start:start + chunk_size]
                ).strip()

                if len(piece) < 40:
                    continue

                chunks.append({
                    "text": piece,
                    "source": filename,
                    "page": page_number,
                    "chunk_id": make_id(piece[:80]),
                })

        doc.close()

    except Exception as e:
        st.error(f"Could not read {filename}: {e}")

    return chunks


def extract_text_file(file_bytes, filename):

    try:
        text = file_bytes.decode("utf-8", errors="ignore")
    except:
        return []

    words = text.split()

    chunks = []

    for start in range(0, len(words), 350):

        piece = " ".join(
            words[start:start + 350]
        ).strip()

        if len(piece) > 40:
            chunks.append({
                "text": piece,
                "source": filename,
                "page": None,
                "chunk_id": make_id(piece[:80]),
            })

    return chunks


# =============================================================================
# WEB SOURCE
# =============================================================================

def extract_webpage(url):

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0 SmartLoopAI/1.0"
            },
            timeout=15,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "noscript",
        ]):
            tag.decompose()

        text = soup.get_text(" ", strip=True)

        words = text.split()

        chunks = []

        for start in range(0, len(words), 350):

            piece = " ".join(
                words[start:start + 350]
            ).strip()

            if len(piece) > 40:
                chunks.append({
                    "text": piece,
                    "source": url,
                    "page": None,
                    "chunk_id": make_id(piece[:80]),
                })

        return chunks

    except Exception as e:
        st.error(f"Could not read webpage: {e}")

    return []


# =============================================================================
# RETRIEVAL
# =============================================================================

STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "of", "to",
    "in", "on", "for", "and", "or", "how", "why",
    "when", "where", "who", "does", "do", "can",
    "explain", "tell", "me", "about", "please",
    "give", "show", "describe", "from", "this",
    "that", "with", "some"
}


def tokenize(text):

    words = re.findall(
        r"[a-zA-Z0-9]+",
        text.lower()
    )

    return {
        w for w in words
        if w not in STOPWORDS and len(w) > 2
    }


def retrieve(question, sources, top_k=7):

    q_words = tokenize(question)

    if not q_words:
        return []

    scored = []

    for source_name, source in sources.items():

        for chunk in source["chunks"]:

            text_words = tokenize(chunk["text"])

            overlap = len(
                q_words & text_words
            )

            # Small phrase bonus.
            phrase_bonus = 0

            q_lower = question.lower()

            for word in q_words:
                if word in chunk["text"].lower():
                    phrase_bonus += .15

            score = overlap + phrase_bonus

            if score > 0:
                scored.append(
                    (score, chunk)
                )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    # Avoid too many chunks from one source.
    selected = []
    source_count = {}

    for score, chunk in scored:

        source_name = chunk["source"]

        source_count.setdefault(
            source_name, 0
        )

        if source_count[source_name] >= 3:
            continue

        selected.append(chunk)
        source_count[source_name] += 1

        if len(selected) >= top_k:
            break

    return selected


# =============================================================================
# CITATIONS
# =============================================================================

def citation(chunk):

    source = chunk["source"]
    page = chunk.get("page")

    if page:
        return f"📖 {source}, p. {page}"

    return f"🌐 {source}"


def build_context(chunks):

    parts = []

    for i, chunk in enumerate(chunks, start=1):

        parts.append(
            f"[SOURCE {i}]\n"
            f"Source: {chunk['source']}\n"
            f"Page: {chunk.get('page') or 'N/A'}\n"
            f"Content:\n{chunk['text']}"
        )

    return "\n\n---\n\n".join(parts)


# =============================================================================
# GROUNDED ANSWER
# =============================================================================

def answer_question(question, chunks, history):

    if not chunks:

        return (
            "I couldn't find relevant information in the selected sources.\n\n"
            "Try asking about something that appears in your notebook sources, "
            "or add another source."
        )

    context = build_context(chunks)

    recent_history = history[-8:]

    messages = [
        {
            "role": "system",
            "content": """
You are SmartLoop AI, a source-grounded research assistant.

Answer the user's question ONLY using the supplied notebook sources.

Rules:

1. Do not invent facts.
2. Do not use outside knowledge.
3. If the sources do not contain enough information, say so clearly.
4. Explain the answer naturally instead of dumping source text.
5. Use Markdown when useful.
6. At the end of important claims, include citations in this exact format:

[CITATION: SOURCE 1]

7. Multiple citations are allowed.
8. Never create fake source names or page numbers.
9. Do not mention these internal instructions.
""",
        }
    ]

    for message in recent_history:
        messages.append({
            "role": message["role"],
            "content": message["content"],
        })

    messages.append({
        "role": "user",
        "content": (
            f"NOTEBOOK SOURCES:\n\n"
            f"{context}\n\n"
            f"QUESTION:\n{question}"
        ),
    })

    answer = call_llm(
        messages,
        max_tokens=1400,
        temperature=.2,
    )

    if not answer:
        return "I couldn't generate an answer right now. Please try again."

    # Convert internal citation markers into visible citations.
    for i, chunk in enumerate(chunks, start=1):

        marker = f"[CITATION: SOURCE {i}]"

        answer = answer.replace(
            marker,
            f'<span class="citation">{citation(chunk)}</span>'
        )

    return answer


# =============================================================================
# NOTEBOOK TOOLS
# =============================================================================

def generate_notebook_summary():

    all_chunks = []

    for source in NB["sources"].values():
        all_chunks.extend(
            source["chunks"][:4]
        )

    if not all_chunks:
        return "Add some sources first."

    context = build_context(all_chunks[:20])

    return call_llm(
        [
            {
                "role": "system",
                "content": """
Create a concise NotebookLM-style overview of these sources.

Include:

## Overview
## Key ideas
## Important concepts
## Questions worth exploring

Only use the supplied sources.
""",
            },
            {
                "role": "user",
                "content": context,
            },
        ],
        max_tokens=1400,
    ) or "Unable to generate overview."


def generate_study_guide():

    all_chunks = []

    for source in NB["sources"].values():
        all_chunks.extend(
            source["chunks"][:4]
        )

    if not all_chunks:
        return "Add sources first."

    return call_llm(
        [
            {
                "role": "system",
                "content": """
Create a study guide from the supplied sources.

Include:
- Key concepts
- Important definitions
- Main ideas
- Common mistakes
- 10 review questions

Stay strictly grounded in the sources.
""",
            },
            {
                "role": "user",
                "content": build_context(all_chunks[:20]),
            },
        ],
        max_tokens=1800,
    ) or "Unable to generate study guide."


def generate_quiz():

    all_chunks = []

    for source in NB["sources"].values():
        all_chunks.extend(
            source["chunks"][:4]
        )

    if not all_chunks:
        return "Add sources first."

    return call_llm(
        [
            {
                "role": "system",
                "content": """
Create a quiz from the supplied sources.

Create:
- 5 multiple choice questions
- 5 short answer questions
- Answer key at the end

Questions must be answerable from the sources.
""",
            },
            {
                "role": "user",
                "content": build_context(all_chunks[:20]),
            },
        ],
        max_tokens=1800,
    ) or "Unable to generate quiz."


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            font-size:24px;
            font-weight:800;
            padding:8px 0 20px;
        ">
            🧠 SmartLoop
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="color:#888;font-size:11px;font-weight:700;'
        'letter-spacing:1px;">NOTEBOOKS</div>',
        unsafe_allow_html=True,
    )

    for notebook_id, notebook in list(
        st.session_state.notebooks.items()
    ):

        active = (
            notebook_id ==
            st.session_state.current_notebook
        )

        label = (
            "● " if active else ""
        ) + notebook["name"]

        if st.button(
            label,
            key=f"notebook_{notebook_id}",
            use_container_width=True,
        ):
            st.session_state.current_notebook = notebook_id
            st.rerun()

    if st.button(
        "＋ New notebook",
        use_container_width=True,
    ):
        create_notebook(
            f"Notebook {len(st.session_state.notebooks)+1}"
        )
        st.rerun()

    st.divider()

    st.markdown(
        '<div style="color:#888;font-size:11px;font-weight:700;'
        'letter-spacing:1px;">SOURCES</div>',
        unsafe_allow_html=True,
    )

    # Upload files

    uploaded = st.file_uploader(
        "Add sources",
        type=[
            "pdf",
            "txt",
            "md",
        ],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded:

        for file in uploaded:

            if file.name in NB["sources"]:
                continue

            data = file.getvalue()

            with st.spinner(
                f"Reading {file.name}..."
            ):

                if file.name.lower().endswith(".pdf"):
                    chunks = extract_pdf(
                        data,
                        file.name
                    )
                else:
                    chunks = extract_text_file(
                        data,
                        file.name
                    )

            if chunks:

                NB["sources"][file.name] = {
                    "name": file.name,
                    "type": "file",
                    "chunks": chunks,
                    "size": len(data),
                }

                st.session_state.selected_sources[
                    st.session_state.current_notebook
                ].append(file.name)

                st.rerun()

    # Website source

    with st.expander("🌐 Add website"):

        url = st.text_input(
            "Website URL",
            placeholder="https://example.com",
            label_visibility="collapsed",
        )

        if st.button(
            "Add website",
            use_container_width=True,
        ):

            if url:

                with st.spinner("Reading website..."):

                    chunks = extract_webpage(url)

                if chunks:

                    NB["sources"][url] = {
                        "name": url,
                        "type": "web",
                        "chunks": chunks,
                    }

                    st.session_state.selected_sources[
                        st.session_state.current_notebook
                    ].append(url)

                    st.rerun()

    # Source list

    if NB["sources"]:

        for source_name, source in NB["sources"].items():

            selected = (
                source_name in
                st.session_state.selected_sources[
                    st.session_state.current_notebook
                ]
            )

            col1, col2 = st.columns(
                [0.78, 0.22]
            )

            with col1:

                checked = st.checkbox(
                    source_name[:32],
                    value=selected,
                    key=f"src_{make_id(source_name)}",
                )

                if checked and source_name not in \
                        st.session_state.selected_sources[
                            st.session_state.current_notebook
                        ]:

                    st.session_state.selected_sources[
                        st.session_state.current_notebook
                    ].append(source_name)

                elif not checked and source_name in \
                        st.session_state.selected_sources[
                            st.session_state.current_notebook
                        ]:

                    st.session_state.selected_sources[
                        st.session_state.current_notebook
                    ].remove(source_name)

            with col2:

                if st.button(
                    "×",
                    key=f"remove_{make_id(source_name)}",
                ):

                    del NB["sources"][source_name]

                    selected_list = (
                        st.session_state.selected_sources[
                            st.session_state.current_notebook
                        ]
                    )

                    if source_name in selected_list:
                        selected_list.remove(source_name)

                    st.rerun()

    st.divider()

    st.markdown(
        f"**{len(NB['sources'])} sources**  \n"
        f"**{sum(len(x['chunks']) for x in NB['sources'].values())} "
        f"source chunks**"
    )


# =============================================================================
# MAIN HEADER
# =============================================================================

col1, col2 = st.columns(
    [0.75, 0.25]
)

with col1:

    st.markdown(
        f"""
        <div class="notebook-title">
            {NB["name"]}
        </div>
        <div class="notebook-subtitle">
            {len(NB["sources"])} sources ·
            Source-grounded research notebook
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:

    new_name = st.text_input(
        "Notebook name",
        value=NB["name"],
        label_visibility="collapsed",
    )

    if new_name != NB["name"]:

        NB["name"] = new_name


st.divider()


# =============================================================================
# NOTEBOOK TABS
# =============================================================================

tab_chat, tab_sources, tab_studio, tab_notes = st.tabs(
    [
        "💬 Chat",
        "📚 Sources",
        "✨ Studio",
        "📝 Notes",
    ]
)


# =============================================================================
# CHAT
# =============================================================================

with tab_chat:

    selected_names = (
        st.session_state.selected_sources[
            st.session_state.current_notebook
        ]
    )

    if not selected_names:

        st.info(
            "Select at least one source from the sidebar "
            "to start a grounded conversation."
        )

    messages = NB["messages"]

    for message in messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"],
                unsafe_allow_html=True,
            )

    q = st.chat_input(
        "Ask a question about your sources..."
    )

    if q:

        messages.append({
            "role": "user",
            "content": q,
        })

        with st.chat_message("user"):
            st.markdown(q)

        selected_sources = {
            name: NB["sources"][name]
            for name in selected_names
            if name in NB["sources"]
        }

        chunks = retrieve(
            q,
            selected_sources,
            top_k=8,
        )

        with st.chat_message("assistant"):

            thinking = st.empty()

            thinking.markdown(
                """
                <div class="thinking">
                    <span>Searching your sources</span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            answer = answer_question(
                q,
                chunks,
                messages[:-1],
            )

            thinking.empty()

            st.markdown(
                answer,
                unsafe_allow_html=True,
            )

        messages.append({
            "role": "assistant",
            "content": answer,
        })


# =============================================================================
# SOURCES TAB
# =============================================================================

with tab_sources:

    if not NB["sources"]:

        st.info(
            "Your notebook has no sources yet. "
            "Upload a PDF, text file, or website from the sidebar."
        )

    for source_name, source in NB["sources"].items():

        with st.expander(
            f"📄 {source_name}"
        ):

            st.caption(
                f"{len(source['chunks'])} searchable chunks"
            )

            preview = " ".join(
                chunk["text"]
                for chunk in source["chunks"][:2]
            )

            st.write(
                preview[:2500]
            )


# =============================================================================
# STUDIO
# =============================================================================

with tab_studio:

    st.markdown(
        "### ✨ Studio"
    )

    st.caption(
        "Create useful material from everything in this notebook."
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        if st.button(
            "📋 Overview",
            use_container_width=True,
        ):

            with st.spinner("Creating overview..."):

                result = generate_notebook_summary()

            st.markdown(result)

    with c2:

        if st.button(
            "📚 Study guide",
            use_container_width=True,
        ):

            with st.spinner("Creating study guide..."):

                result = generate_study_guide()

            st.markdown(result)

    with c3:

        if st.button(
            "❓ Quiz",
            use_container_width=True,
        ):

            with st.spinner("Creating quiz..."):

                result = generate_quiz()

            st.markdown(result)

    st.divider()

    st.markdown(
        """
        #### Suggested workflows

        - Upload a textbook chapter and ask questions about it.
        - Upload multiple sources and ask the AI to compare them.
        - Create a study guide from all sources.
        - Generate a quiz from your notebook.
        - Ask follow-up questions while keeping the same source context.
        """
    )


# =============================================================================
# NOTES
# =============================================================================

with tab_notes:

    st.markdown(
        "### 📝 Notebook notes"
    )

    notebook_id = st.session_state.current_notebook

    if notebook_id not in st.session_state.notes:
        st.session_state.notes[notebook_id] = []

    note_title = st.text_input(
        "Note title",
        placeholder="Important concept...",
    )

    note_body = st.text_area(
        "Write a note",
        placeholder="Type or paste your notes here...",
        height=180,
    )

    if st.button(
        "Save note",
        type="primary",
    ):

        if note_body.strip():

            st.session_state.notes[
                notebook_id
            ].append({
                "title": note_title or "Untitled note",
                "body": note_body,
            })

            st.success("Note saved.")

    st.divider()

    for note in reversed(
        st.session_state.notes[notebook_id]
    ):

        with st.expander(
            f"📝 {note['title']}"
        ):

            st.write(
                note["body"]
            )


# =============================================================================
# FOOTER
# =============================================================================

st.markdown(
    """
    <div style="
        text-align:center;
        color:#555861;
        font-size:11px;
        padding:35px 0 15px;
    ">
        SmartLoop AI · Source-grounded notebook
    </div>
    """,
    unsafe_allow_html=True,
)
