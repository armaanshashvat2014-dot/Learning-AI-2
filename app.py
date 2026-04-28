import streamlit as st
import re, os, time, itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
import wikipedia

from openai import OpenAI
from google import genai
import fitz  # pymupdf

def extract_pdf(fname):
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if len(text) > 60:
                words = set(
                    re.sub(r'[^a-z0-9 ]', ' ',
                    text.lower()).split()
                )
                chunks.append({
                    "text":  text[:1500],
                    "words": words,
                    "file":  fname,
                    "page":  page_num + 1
                })
        doc.close()
    except:
        pass
    return chunks
# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SmartLoop AI",
    page_icon="🧠",
    layout="wide"
)

# =========================
# CSS
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
[data-testid="stSidebar"] {
    background: rgba(12,12,22,0.92) !important;
    backdrop-filter: blur(40px) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}
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
[data-testid="stChatMessage"] * { color: #f5f5f7 !important; }
[data-testid="stChatMessage"] pre,
[data-testid="stChatMessage"] code {
    white-space: pre-wrap !important;
    word-break: break-word !important;
}
.stChatInputContainer {
    background: rgba(20,20,35,0.85) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 20px !important;
}
.stTextInput>div>div>input,
.stTextArea>div>textarea,
.stSelectbox>div>div>div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #fff !important;
}
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
.stButton>button:active { transform: translateY(1px) !important; }
.thinking-container {
    display: flex; align-items: center; gap: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.04);
    border-radius: 14px; margin: 8px 0;
    border-left: 3px solid #00d4ff;
}
.thinking-text { color: #00d4ff; font-size: 14px; font-weight: 600; }
.thinking-dots { display: flex; gap: 4px; }
.thinking-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #00d4ff; animation: tp 1.4s infinite;
}
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes tp {
    0%,60%,100% { opacity:0.3; transform:scale(0.8); }
    30% { opacity:1; transform:scale(1.2); }
}
.beta-badge {
    display: inline-block;
    background: linear-gradient(135deg, #ff4d6d, #7b2ff7);
    color: white; padding: 4px 12px; border-radius: 999px;
    font-size: 13px; font-weight: 700;
    box-shadow: 0 0 12px rgba(255,77,109,0.5);
    vertical-align: middle; margin-left: 10px;
}
.section-label {
    color: #00d4ff; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    margin: 12px 0 6px;
}
.welcome-card {
    background: linear-gradient(135deg,
        rgba(0,212,255,0.12), rgba(123,47,247,0.08));
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px; padding: 12px 16px;
    margin-bottom: 8px; font-weight: 600;
    color: #2ecc71; font-size: 14px;
}
.source-badge {
    display: inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: 11px;
    font-weight: 600; margin-top: 6px;
}
.src-pdf  { background:rgba(0,212,255,0.15); color:#00d4ff; border:1px solid rgba(0,212,255,0.3); }
.src-ai   { background:rgba(252,132,4,0.15); color:#fc8404; border:1px solid rgba(252,132,4,0.3); }
.src-wiki { background:rgba(52,152,219,0.15); color:#3498db; border:1px solid rgba(52,152,219,0.3); }
.src-calc { background:rgba(155,89,182,0.2); color:#9b59b6; border:1px solid rgba(155,89,182,0.4); }
</style>
""", unsafe_allow_html=True)

# =========================
# API KEYS
# Key roles:
# OPENAI 1,2,3,4 → PDF parallel search/judge
# OPENAI 2,3     → primary answer generation
# OPENAI 4       → extra fallback answer generation
# GOOGLE 1,2,3,4 → answer generation + fallback
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

# Keys specifically for PDF judging — all openai keys
PDF_JUDGE_KEYS = ALL_OPENAI_KEYS.copy()

# Primary answer keys (keys 2 and 3)
PRIMARY_ANSWER_KEYS = [
    k for i, k in enumerate(ALL_OPENAI_KEYS)
    if i in [1, 2]
]

# Extra fallback answer key (key 4)
EXTRA_ANSWER_KEYS = [
    k for i, k in enumerate(ALL_OPENAI_KEYS)
    if i == 3
]

ALL_GOOGLE_KEYS = [
    get_secret("GOOGLE_API_KEY_1"),
    get_secret("GOOGLE_API_KEY_2"),
    get_secret("GOOGLE_API_KEY_3"),
    get_secret("GOOGLE_API_KEY_4"),
]
ALL_GOOGLE_KEYS = [k for k in ALL_GOOGLE_KEYS if k]

if not ALL_OPENAI_KEYS and not ALL_GOOGLE_KEYS:
    st.error("No API keys found in secrets.")
    st.stop()

# Cycles for each role
pdf_judge_cycle   = itertools.cycle(PDF_JUDGE_KEYS) if PDF_JUDGE_KEYS else None
primary_ans_cycle = itertools.cycle(PRIMARY_ANSWER_KEYS) if PRIMARY_ANSWER_KEYS else None
extra_ans_cycle   = itertools.cycle(EXTRA_ANSWER_KEYS) if EXTRA_ANSWER_KEYS else None
google_cycle      = itertools.cycle(ALL_GOOGLE_KEYS) if ALL_GOOGLE_KEYS else None

def get_pdf_judge_client():
    if not pdf_judge_cycle:
        return None
    return OpenAI(api_key=next(pdf_judge_cycle))

def get_primary_answer_client():
    if not primary_ans_cycle:
        return None
    return OpenAI(api_key=next(primary_ans_cycle))

def get_extra_answer_client():
    if not extra_ans_cycle:
        return None
    return OpenAI(api_key=next(extra_ans_cycle))

def get_google_client():
    if not google_cycle:
        return None
    return genai.Client(api_key=next(google_cycle))
# =========================
# PDF CHUNKING
# =========================
    PDF_CHUNKS = load_all_pdfs()
# =========================
# GRADE SELECTION POPUP
# =========================
if "grade" not in st.session_state:
    st.session_state.grade = None

if st.session_state.grade is None:
    st.markdown("""
<div style='max-width:400px; margin:100px auto;
    background:rgba(255,255,255,0.05);
    border:1px solid rgba(255,255,255,0.15);
    border-radius:28px; padding:40px;
    text-align:center; backdrop-filter:blur(40px);'>
    <div style='font-size:40px; margin-bottom:12px;'>🧠</div>
    <div style='font-size:28px; font-weight:800; color:#00d4ff;
        margin-bottom:6px;'>SmartLoop AI</div>
    <div style='color:rgba(255,255,255,0.5); margin-bottom:28px;
        font-size:15px;'>Select your grade to get started</div>
</div>
""", unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        grade = st.selectbox(
            "Your Grade",
            [f"Grade {i}" for i in range(1, 11)],
            index=5,
            label_visibility="collapsed"
        )
        if st.button(
            "Get Started →",
            use_container_width=True,
            type="primary"
        ):
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
if "last_q" not in st.session_state:
    st.session_state.last_q = ""

# =========================
# MATH SOLVER
# =========================
def is_pure_calc(q):
    return bool(re.fullmatch(
        r"[\d\.\+\-\*\/\(\)\s\^%]+", q.strip()
    ))

def solve_math(q):
    try:
        expr = (
            q.strip()
            .replace("^", "**")
            .replace(" ", "")
        )
        result = eval(expr, {"__builtins__": None}, {})
        return f"**= {round(result, 8)}**", "calc"
    except:
        return None, None

# =========================
# PDF KEYWORD SEARCH
# =========================
STOPWORDS = {
    "what","is","are","how","why","when","who","the","a","an",
    "of","in","to","and","does","do","explain","define","me",
    "about","give","please","describe","tell","example",
    "examples","find","solve","calculate","show","write"
}

def keyword_search(q):
    if not PDF_CHUNKS:
        return []
    q_words = set(
        re.sub(r'[^a-z0-9 ]', ' ', q.lower()).split()
    ) - STOPWORDS
    if not q_words:
        return []
    scored = []
    for chunk in PDF_CHUNKS:
        score = len(q_words & chunk["words"])
        if score >= 2:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:8]

# =========================
# AI JUDGE — is chunk good?
# Uses ALL openai keys in
# parallel for max speed
# =========================
def judge_single_chunk(args):
    chunk, question, key = args
    prompt = f"""Question: {question}

Excerpt:
{chunk['text'][:500]}

Does this excerpt directly help answer the question?
Reply ONLY: YES or NO"""
    try:
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=3,
            temperature=0
        )
        return "YES" in r.choices[0].message.content.upper(), chunk
    except:
        return False, chunk

def parallel_judge_chunks(candidates, question):
    if not candidates or not PDF_JUDGE_KEYS:
        return []

    # Assign keys round-robin to each chunk
    tasks = []
    key_list = list(itertools.islice(
        itertools.cycle(PDF_JUDGE_KEYS),
        len(candidates)
    ))
    for i, (_, chunk) in enumerate(candidates):
        tasks.append((chunk, question, key_list[i]))

    good = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = [ex.submit(judge_single_chunk, t) for t in tasks]
        for future in as_completed(futures):
            try:
                ok, chunk = future.result()
                if ok:
                    good.append(chunk)
            except:
                pass
    return good

# =========================
# GRADE STYLE
# =========================
def grade_style(grade_num):
    if grade_num <= 3:
        return "Use very simple words, very short sentences, and fun examples. Like explaining to a young child."
    elif grade_num <= 6:
        return "Use clear simple language with relatable everyday examples. Avoid jargon."
    elif grade_num <= 8:
        return "Use clear academic language. Include key terms, definitions, and worked examples."
    else:
        return "Use proper academic language with detailed explanations, equations, and analysis suitable for high school."

# =========================
# TIER 1: PDF ANSWER
# Uses primary openai keys
# =========================
def answer_from_pdf(question, good_chunks, grade_num, history):
    context = "\n\n---\n\n".join([
        f"[Source: {c['file']} p.{c['page']}]\n{c['text']}"
        for c in good_chunks[:4]
    ])
    source_file = good_chunks[0]["file"]

    style = grade_style(grade_num)
    history_text = ""
    if history:
        for msg in history[-4:]:
            role = "Student" if msg["role"] == "user" else "SmartLoop"
            history_text += f"{role}: {msg.get('content','')}\n"

    prompt = f"""You are SmartLoop AI, an expert tutor for Grade {grade_num} students.
{style}

Use the textbook excerpts below to answer the question accurately.
Structure your answer clearly with headings, bullet points, or numbered steps where helpful.
If the excerpts don't fully cover the question, supplement with your own knowledge.

TEXTBOOK EXCERPTS:
{context}

PREVIOUS CONVERSATION:
{history_text}

QUESTION: {question}

Give a complete, well-structured answer:"""

    # Try primary keys first (keys 2 and 3)
    for _ in range(len(PRIMARY_ANSWER_KEYS) or 1):
        try:
            client = get_primary_answer_client()
            if client:
                r = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role":"user","content":prompt}],
                    max_tokens=800
                )
                ans = r.choices[0].message.content.strip()
                if ans and len(ans) > 20:
                    return ans, "pdf", source_file
        except:
            time.sleep(1)

    # Try extra key (key 4)
    try:
        client = get_extra_answer_client()
        if client:
            r = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=800
            )
            ans = r.choices[0].message.content.strip()
            if ans and len(ans) > 20:
                return ans, "pdf", source_file
    except:
        pass

    return None, None, None

# =========================
# TIER 2: DIRECT AI ANSWER
# Google first, then openai
# =========================
def answer_from_ai(question, grade_num, history):
    style = grade_style(grade_num)
    history_text = ""
    if history:
        for msg in history[-4:]:
            role = "Student" if msg["role"] == "user" else "SmartLoop"
            history_text += f"{role}: {msg.get('content','')}\n"

    prompt = f"""You are SmartLoop AI, an expert tutor for Grade {grade_num} students.
{style}

Answer this question completely and accurately.
Use bullet points, examples, formulas, or diagrams described in text where helpful.
Never refuse. Always give a complete answer.

PREVIOUS CONVERSATION:
{history_text}

QUESTION: {question}

Complete answer:"""

    # Try Google first
    for _ in range(min(2, len(ALL_GOOGLE_KEYS))):
        try:
            c = get_google_client()
            if c:
                r = c.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                if r.text and len(r.text.strip()) > 20:
                    return r.text.strip(), "ai", None
        except:
            time.sleep(1)

    # Try primary OpenAI keys (2 and 3)
    for _ in range(len(PRIMARY_ANSWER_KEYS) or 1):
        try:
            client = get_primary_answer_client()
            if client:
                msgs = [{
                    "role": "system",
                    "content": (
                        f"You are SmartLoop AI, an expert tutor "
                        f"for Grade {grade_num} students. {style}"
                    )
                }]
                if history:
                    for msg in history[-4:]:
                        msgs.append({
                            "role": msg["role"],
                            "content": msg.get("content","")
                        })
                msgs.append({"role":"user","content":question})
                r = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=msgs,
                    max_tokens=800
                )
                ans = r.choices[0].message.content.strip()
                if ans and len(ans) > 20:
                    return ans, "ai", None
        except:
            time.sleep(1)

    # Try extra OpenAI key (4)
    try:
        client = get_extra_answer_client()
        if client:
            r = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=800
            )
            ans = r.choices[0].message.content.strip()
            if ans and len(ans) > 20:
                return ans, "ai", None
    except:
        pass

    return None, None, None

# =========================
# TIER 3: WIKIPEDIA
# Only if both PDF and AI fail
# =========================
def answer_from_wiki(question):
    try:
        # Clean question for wiki search
        search_q = re.sub(
            r"(what is|what are|explain|define|how does|"
            r"tell me about|describe)",
            "", question.lower()
        ).strip()

        result = wikipedia.summary(
            search_q[:60],
            sentences=3,
            auto_suggest=True
        )

        # Reject disambiguation/index articles
        bad = [
            "may refer to", "disambiguation",
            "is a list", "index (", "is an index"
        ]
        if any(b in result.lower() for b in bad):
            return None, None, None

        return result, "wiki", None

    except wikipedia.exceptions.DisambiguationError as e:
        try:
            result = wikipedia.summary(
                e.options[0], sentences=3
            )
            return result, "wiki", None
        except:
            return None, None, None
    except:
        return None, None, None

# =========================
# MAIN PIPELINE
# Calc → PDF → AI → Wiki
# =========================
def smartloop(question, grade_num, history):

    # ── Pure calculation ──────────────
    if is_pure_calc(question):
        ans, tier = solve_math(question)
        if ans:
            return ans, tier, None

    # ── TIER 1: PDF ───────────────────
    candidates = keyword_search(question)
    if candidates:
        good_chunks = parallel_judge_chunks(
            candidates, question
        )
        if good_chunks:
            ans, tier, src = answer_from_pdf(
                question, good_chunks,
                grade_num, history
            )
            if ans:
                return ans, tier, src

    # ── TIER 2: AI ────────────────────
    ans, tier, src = answer_from_ai(
        question, grade_num, history
    )
    if ans:
        return ans, tier, src

    # ── TIER 3: Wikipedia ─────────────
    ans, tier, src = answer_from_wiki(question)
    if ans:
        return ans, tier, src

    # ── Final fallback ────────────────
    return (
        "I'm having trouble connecting right now. "
        "Please try again in a moment.",
        "", None
    )

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(
        "<div class='welcome-card'>"
        f"👋 Welcome! Grade {st.session_state.grade}"
        "</div>",
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown(
        "<div class='section-label'>🎯 Active Grade</div>",
        unsafe_allow_html=True
    )
    new_grade = st.selectbox(
        "Grade",
        [f"Grade {i}" for i in range(1, 11)],
        index=st.session_state.grade - 1,
        label_visibility="collapsed"
    )
    if int(new_grade.split()[1]) != st.session_state.grade:
        st.session_state.grade = int(new_grade.split()[1])
        st.rerun()

    st.divider()

    if st.button(
        "➕ New Chat",
        use_container_width=True,
        type="primary"
    ):
        name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()

    st.markdown(
        "<div class='section-label'>💬 Chats</div>",
        unsafe_allow_html=True
    )

    for chat_name in list(reversed(
        list(st.session_state.chats.keys())
    )):
        is_active = (
            chat_name == st.session_state.current_chat
        )
        col1, col2 = st.columns(
            [0.82, 0.18], vertical_alignment="center"
        )
        msgs = st.session_state.chats.get(chat_name, [])
        first_user = next(
            (m["content"] for m in msgs
             if m["role"] == "user"),
            chat_name
        )
        title = (
            first_user[:22] + "..."
            if len(first_user) > 22
            else first_user
        )
        label = f"{'🟢' if is_active else '💬'} {title}"

        if col1.button(
            label, key=f"ch_{chat_name}",
            use_container_width=True
        ):
            st.session_state.current_chat = chat_name
            st.rerun()

        if col2.button(
            "🗑", key=f"dl_{chat_name}",
            use_container_width=True
        ):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[chat_name]
                if st.session_state.current_chat == chat_name:
                    st.session_state.current_chat = list(
                        st.session_state.chats.keys()
                    )[0]
                st.rerun()

    st.divider()

    st.markdown(
        "<div class='section-label'>📊 Status</div>",
        unsafe_allow_html=True
    )
    st.success(f"📚 {len(PDF_CHUNKS)} pages loaded")
    st.info(
        f"🔑 OpenAI: {len(ALL_OPENAI_KEYS)} | "
        f"Google: {len(ALL_GOOGLE_KEYS)}"
    )

    if st.button(
        "🔄 Change Grade",
        use_container_width=True
    ):
        st.session_state.grade = None
        st.rerun()

    with st.expander("🏫 Are you a Teacher?"):
        teacher_code = st.text_input(
            "School Code", type="password",
            placeholder="Enter code...",
            label_visibility="collapsed"
        )
        if st.button("Verify", use_container_width=True):
            if teacher_code == st.secrets.get(
                "TEACHER_CODE", ""
            ):
                st.success("✅ Teacher access granted!")
            else:
                st.error("Invalid code.")

# =========================
# MAIN CHAT UI
# =========================
st.markdown(f"""
<div style='text-align:center; padding:20px 0 8px;'>
    <span style='font-size:44px; font-weight:800;
        color:#00d4ff; letter-spacing:-2px;
        text-shadow:0 0 16px rgba(0,212,255,0.45);'>
        🧠 SmartLoop AI
    </span>
    <span class='beta-badge'>BETA</span>
</div>
<div style='text-align:center; color:rgba(255,255,255,0.4);
    font-size:15px; margin-bottom:24px;'>
    Grade {st.session_state.grade} Tutor
</div>
""", unsafe_allow_html=True)

messages = st.session_state.chats.get(
    st.session_state.current_chat, []
)

# Greeting
if not messages:
    with st.chat_message("assistant"):
        st.markdown(
            f"👋 **Hey! I'm SmartLoop AI!**\n\n"
            f"I'm your Grade {st.session_state.grade} "
            f"tutor. Ask me anything!\n\n"
            f"- 📖 I search your **textbooks first**\n"
            f"- 🤖 If not found, I use **AI knowledge**\n"
            f"- 🌐 If AI fails, I search **Wikipedia**\n"
            f"- 🧮 I solve **maths step-by-step**\n"
            f"- 💬 I remember our **conversation**\n\n"
            f"*What would you like to learn today?*"
        )

# Display history
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content",""))
        tier   = msg.get("tier","")
        source = msg.get("source","")
        if tier == "pdf" and source:
            st.markdown(
                f'<span class="source-badge src-pdf">'
                f'📖 {source}</span>',
                unsafe_allow_html=True
            )
        elif tier == "ai":
            st.markdown(
                '<span class="source-badge src-ai">'
                '💡 AI general knowledge</span>',
                unsafe_allow_html=True
            )
        elif tier == "wiki":
            st.markdown(
                '<span class="source-badge src-wiki">'
                '🌐 Wikipedia</span>',
                unsafe_allow_html=True
            )
        elif tier == "calc":
            st.markdown(
                '<span class="source-badge src-calc">'
                '🧮 Calculator</span>',
                unsafe_allow_html=True
            )

# Chat input
q = st.chat_input("Ask SmartLoop...")

if q and q != st.session_state.last_q:
    st.session_state.last_q = q
    messages = st.session_state.chats[
        st.session_state.current_chat
    ]
    messages.append({"role":"user","content":q})

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.markdown("""
<div class="thinking-container">
    <span class="thinking-text">Searching & thinking</span>
    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)

        ans, tier, source = smartloop(
            q,
            st.session_state.grade,
            messages[:-1]
        )

        thinking.empty()
        st.markdown(ans)

        if tier == "pdf" and source:
            st.markdown(
                f'<span class="source-badge src-pdf">'
                f'📖 {source}</span>',
                unsafe_allow_html=True
            )
        elif tier == "ai":
            st.markdown(
                '<span class="source-badge src-ai">'
                '💡 AI general knowledge</span>',
                unsafe_allow_html=True
            )
        elif tier == "wiki":
            st.markdown(
                '<span class="source-badge src-wiki">'
                '🌐 Wikipedia</span>',
                unsafe_allow_html=True
            )
        elif tier == "calc":
            st.markdown(
                '<span class="source-badge src-calc">'
                '🧮 Calculator</span>',
                unsafe_allow_html=True
            )

    messages.append({
        "role":    "assistant",
        "content": ans,
        "tier":    tier,
        "source":  source
    })
