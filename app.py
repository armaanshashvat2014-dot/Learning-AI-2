import streamlit as st
import re, os, time, itertools, math
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import warnings, logging
import wikipedia
import fitz
import requests
from bs4 import BeautifulSoup

from openai import OpenAI
from google import genai

warnings.filterwarnings("ignore")
logging.getLogger("pymupdf").setLevel(logging.ERROR)

st.set_page_config(
    page_title="SmartLoop AI",
    page_icon="🧠",
    layout="wide"
)

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
.src-ddg  { background:rgba(255,69,0,0.15);  color:#ff6b35; border:1px solid rgba(255,69,0,0.3); }
.src-wiki { background:rgba(52,152,219,0.15); color:#3498db; border:1px solid rgba(52,152,219,0.3); }
.src-calc { background:rgba(155,89,182,0.2);  color:#9b59b6; border:1px solid rgba(155,89,182,0.4); }
</style>
""", unsafe_allow_html=True)

# =========================
# API KEYS
# =========================
ALL_OPENAI_KEYS = [
    st.secrets.get(f"OPENAI_API_KEY_{i}") for i in range(1, 5)
]
ALL_OPENAI_KEYS = [k for k in ALL_OPENAI_KEYS if k]

ALL_GOOGLE_KEYS = [
    st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 5)
]
ALL_GOOGLE_KEYS = [k for k in ALL_GOOGLE_KEYS if k]

if not ALL_OPENAI_KEYS and not ALL_GOOGLE_KEYS:
    st.error("No API keys found.")
    st.stop()

PDF_JUDGE_KEYS   = ALL_OPENAI_KEYS.copy()
PRIMARY_ANS_KEYS = [k for i,k in enumerate(ALL_OPENAI_KEYS) if i in [1,2]]
EXTRA_ANS_KEYS   = [k for i,k in enumerate(ALL_OPENAI_KEYS) if i == 3]

pdf_judge_cycle   = itertools.cycle(PDF_JUDGE_KEYS)   if PDF_JUDGE_KEYS   else None
primary_ans_cycle = itertools.cycle(PRIMARY_ANS_KEYS) if PRIMARY_ANS_KEYS else None
extra_ans_cycle   = itertools.cycle(EXTRA_ANS_KEYS)   if EXTRA_ANS_KEYS   else None
google_cycle      = itertools.cycle(ALL_GOOGLE_KEYS)  if ALL_GOOGLE_KEYS  else None

def get_primary():
    if primary_ans_cycle:
        return OpenAI(api_key=next(primary_ans_cycle))
    if pdf_judge_cycle:
        return OpenAI(api_key=next(pdf_judge_cycle))
    return None

def get_extra():
    return OpenAI(api_key=next(extra_ans_cycle)) if extra_ans_cycle else None

def get_google():
    return genai.Client(api_key=next(google_cycle)) if google_cycle else None

# =========================
# GRADE SELECTION
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
    <div style='font-size:28px; font-weight:800;
        color:#00d4ff; margin-bottom:6px;'>SmartLoop AI</div>
    <div style='color:rgba(255,255,255,0.5);
        margin-bottom:28px; font-size:15px;'>
        Select your grade to get started
    </div>
</div>
""", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        grade = st.selectbox(
            "Grade",
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
# PDF LOADING — with better chunking
# =========================
def get_allowed_grades(grade):
    return {6:[6,7], 7:[7,8], 8:[8,9]}.get(grade, [grade])

def grade_matches_file(fname, allowed_grades):
    name = fname.lower().replace(".pdf","")
    for g in allowed_grades:
        patterns = [
            str(g), f"grade{g}", f"grade_{g}",
            f"class{g}", f"std{g}", f"g{g}",
            f"{g}th", f"{g}st", f"{g}nd", f"{g}rd",
        ]
        if any(p in name for p in patterns):
            return True
    return False

def extract_pdf_smart(fname):
    """
    UPGRADE: Overlapping paragraph-aware chunking instead of raw page truncation.
    Splits each page into ~400-word chunks with 100-word overlap for better retrieval.
    Also computes IDF-ready word frequency maps per chunk.
    """
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if len(text) < 60:
                continue

            # Split into paragraphs first, then chunk
            paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if len(p.strip()) > 40]
            if not paragraphs:
                paragraphs = [text]

            # Sliding window chunking: ~400 words, 100-word overlap
            words = text.split()
            step, size = 300, 400
            for i in range(0, max(1, len(words) - size + step), step):
                chunk_text = " ".join(words[i:i+size])
                if len(chunk_text) < 80:
                    continue
                clean = re.sub(r'[^a-z0-9 ]', ' ', chunk_text.lower())
                word_freq = defaultdict(int)
                for w in clean.split():
                    word_freq[w] += 1
                chunks.append({
                    "text":      chunk_text[:2000],
                    "word_freq": dict(word_freq),
                    "words":     set(word_freq.keys()),
                    "file":      fname,
                    "page":      page_num + 1,
                    "chunk_i":   i
                })
        doc.close()
    except Exception as e:
        print(f"PDF error {fname}: {e}")
    return chunks

@st.cache_resource(show_spinner=False)
def load_all_pdfs(grade):
    all_chunks  = []
    allowed     = get_allowed_grades(grade)
    pdf_files   = [f for f in os.listdir(".") if f.endswith(".pdf")]
    grade_files = [f for f in pdf_files if grade_matches_file(f, allowed)]
    if not grade_files:
        grade_files = pdf_files
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(extract_pdf_smart, f): f for f in grade_files}
        for future in as_completed(futures):
            all_chunks.extend(future.result())

    # Build corpus-level IDF for BM25
    _build_idf(all_chunks)
    return all_chunks

# =========================
# BM25 RETRIEVAL
# =========================
# Global IDF store (built once after PDF load)
_IDF: dict = {}
_CORPUS_SIZE: int = 0
_AVG_DL: float = 0.0

def _build_idf(chunks):
    global _IDF, _CORPUS_SIZE, _AVG_DL
    _CORPUS_SIZE = len(chunks)
    if not _CORPUS_SIZE:
        return
    df = defaultdict(int)
    total_len = 0
    for c in chunks:
        total_len += sum(c["word_freq"].values())
        for w in c["word_freq"]:
            df[w] += 1
    _AVG_DL = total_len / _CORPUS_SIZE
    _IDF = {
        w: math.log(((_CORPUS_SIZE - freq + 0.5) / (freq + 0.5)) + 1)
        for w, freq in df.items()
    }

def bm25_score(chunk, query_words, k1=1.5, b=0.75):
    """BM25 ranking — far superior to plain keyword overlap."""
    dl = sum(chunk["word_freq"].values())
    score = 0.0
    for w in query_words:
        if w not in chunk["word_freq"]:
            continue
        tf = chunk["word_freq"][w]
        idf = _IDF.get(w, 0.0)
        numerator   = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / max(_AVG_DL, 1))
        score += idf * (numerator / denominator)
    return score

STOPWORDS = {
    "what","is","are","how","why","when","who","the","a","an",
    "of","in","to","and","does","do","explain","define","me",
    "about","give","please","describe","tell","example",
    "examples","find","solve","calculate","show","write","can",
    "you","i","my","we","our","its","it","was","were","will","be"
}

def tokenize_query(q: str) -> list[str]:
    return [
        w for w in re.sub(r'[^a-z0-9 ]', ' ', q.lower()).split()
        if w not in STOPWORDS and len(w) > 1
    ]

def bm25_search(query: str, top_k: int = 12) -> list[dict]:
    """UPGRADE: BM25 retrieval replaces plain keyword overlap."""
    if not PDF_CHUNKS:
        return []
    q_words = tokenize_query(query)
    if not q_words:
        return []
    scored = [(bm25_score(c, q_words), c) for c in PDF_CHUNKS]
    scored.sort(key=lambda x: x[0], reverse=True)
    # Only return chunks with meaningful scores
    threshold = max(0.5, scored[0][0] * 0.15) if scored else 0
    return [c for sc, c in scored[:top_k] if sc >= threshold]

# =========================
# SESSION STATE
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# =========================
# MATH SOLVER
# =========================
def is_pure_calc(q):
    return bool(re.fullmatch(r"[\d\.\+\-\*\/\(\)\s\^%]+", q.strip()))

def solve_math(q):
    try:
        expr   = q.strip().replace("^","**").replace(" ","")
        result = eval(expr, {"__builtins__": None}, {})
        return f"**= {round(result, 8)}**", "calc"
    except:
        return None, None

# =========================
# UPGRADE 1: QUERY REWRITING
# Contextualises the question using conversation history
# =========================
def rewrite_query(question: str, history: list) -> str:
    """
    If the question is ambiguous or a follow-up, rewrite it into a
    self-contained search query using recent chat context.
    Returns the rewritten query (or original if rewrite fails).
    """
    if len(history) < 2:
        return question  # No context to leverage

    recent = history[-4:]
    hist_text = "\n".join([
        f"{'Student' if m['role']=='user' else 'AI'}: {m.get('content','')[:200]}"
        for m in recent
    ])

    prompt = (
        f"Given this conversation:\n{hist_text}\n\n"
        f"Rewrite the student's new question as a clear, self-contained "
        f"search query (no pronouns, no 'it'/'this'/'that', include topic context). "
        f"Return ONLY the rewritten query, nothing else.\n"
        f"Question: {question}\nRewritten:"
    )
    try:
        c = get_primary()
        if c:
            r = c.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0
            )
            rewritten = r.choices[0].message.content.strip()
            if rewritten and len(rewritten) > 5:
                return rewritten
    except:
        pass
    return question

# =========================
# UPGRADE 2: MULTI-QUERY EXPANSION
# Generate 3 variants of the query for broader retrieval
# =========================
def expand_queries(question: str) -> list[str]:
    """
    Generate 2 alternative phrasings of the question.
    Merges BM25 results from all variants (reciprocal rank fusion).
    """
    prompt = (
        f"Generate 2 alternative search queries for this academic question. "
        f"Each on a new line. No numbering, no explanations.\n"
        f"Question: {question}"
    )
    try:
        c = get_primary()
        if c:
            r = c.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.3
            )
            variants = [
                line.strip() for line in
                r.choices[0].message.content.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ]
            return [question] + variants[:2]
    except:
        pass
    return [question]

def reciprocal_rank_fusion(ranked_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """
    UPGRADE: Fuse multiple ranked retrieval lists using RRF.
    Deduplicates by (file, page, chunk_i).
    """
    scores = defaultdict(float)
    chunk_map = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            key = (chunk["file"], chunk["page"], chunk.get("chunk_i", 0))
            scores[key] += 1.0 / (k + rank + 1)
            chunk_map[key] = chunk
    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [chunk_map[k] for k in sorted_keys]

# =========================
# UPGRADE 3: GPT RERANKER
# Scores 0-10 instead of binary YES/NO
# =========================
def rerank_single(args):
    chunk, question, key = args
    prompt = (
        f"Question: {question}\n\n"
        f"Excerpt:\n{chunk['text'][:600]}\n\n"
        f"Score how relevant this excerpt is to answering the question.\n"
        f"Reply with ONLY a number from 0 to 10. No explanation."
    )
    try:
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3,
            temperature=0
        )
        score_str = r.choices[0].message.content.strip()
        score = float(re.search(r'\d+(\.\d+)?', score_str).group())
        return score, chunk
    except:
        return 0.0, chunk

def parallel_rerank(candidates: list[dict], question: str, threshold: float = 5.0) -> list[dict]:
    """
    UPGRADE: Numeric reranking (0-10) instead of binary YES/NO.
    Returns chunks sorted by score, above threshold.
    """
    if not candidates or not PDF_JUDGE_KEYS:
        return candidates[:4]  # Fallback: return top BM25 results

    key_list = list(itertools.islice(
        itertools.cycle(PDF_JUDGE_KEYS), len(candidates)
    ))
    tasks = [(chunk, question, key_list[i]) for i, chunk in enumerate(candidates)]

    results = []
    with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as ex:
        futures = [ex.submit(rerank_single, t) for t in tasks]
        for f in as_completed(futures):
            try:
                score, chunk = f.result()
                if score >= threshold:
                    results.append((score, chunk))
            except:
                pass

    results.sort(key=lambda x: x[0], reverse=True)
    good = [chunk for _, chunk in results]

    # If nothing passes threshold, relax it
    if not good and results:
        results_all = sorted(
            [rerank_single(t) for t in tasks[:3]],
            key=lambda x: x[0], reverse=True
        )
        good = [chunk for _, chunk in results_all if _ >= 3.0]

    return good[:5]

# =========================
# GRADE STYLE
# =========================
def grade_style(g):
    if g <= 3:
        return "Use very simple words, short sentences, fun examples. Like explaining to a young child."
    elif g <= 6:
        return "Use clear simple language with relatable everyday examples."
    elif g <= 8:
        return "Use clear academic language with key terms and worked examples."
    else:
        return "Use detailed academic language suitable for high school."

# =========================
# THINKING PHASES
# =========================
def update_phase(ph, text):
    ph.markdown(f"""
<div class="thinking-container">
    <span class="thinking-text">{text}</span>
    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================
# UPGRADE 4: ANSWER QUALITY GATE
# Self-critique + regenerate if answer is weak
# =========================
def is_weak_answer(answer: str, question: str) -> bool:
    """Heuristic + LLM check for low-quality answers."""
    # Heuristic checks
    if len(answer) < 40:
        return True
    weak_phrases = [
        "i don't know", "i cannot", "i'm not sure",
        "no information", "not available", "cannot find",
        "i am unable", "as an ai"
    ]
    if any(p in answer.lower() for p in weak_phrases):
        return True

    # LLM quality check for borderline cases
    if len(answer) < 150:
        try:
            c = get_primary()
            if c:
                r = c.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Question: {question}\n"
                            f"Answer: {answer}\n\n"
                            f"Is this a complete, useful answer? "
                            f"Reply ONLY: YES or NO"
                        )
                    }],
                    max_tokens=3,
                    temperature=0
                )
                return "NO" in r.choices[0].message.content.upper()
        except:
            pass
    return False

# =========================
# TIER 1: PDF ANSWER — with streaming
# =========================
def answer_from_pdf(question, chunks, grade, history, stream_placeholder=None):
    context = "\n\n---\n\n".join([
        f"[Source: {c['file']}, page {c['page']}]\n{c['text']}"
        for c in chunks[:5]  # UPGRADE: use top 5 instead of 4
    ])
    src   = chunks[0]["file"]
    style = grade_style(grade)
    hist  = "".join([
        f"{'Student' if m['role']=='user' else 'SmartLoop'}: "
        f"{m.get('content','')[:300]}\n"
        for m in history[-6:]  # UPGRADE: use last 6 turns
    ])

    # UPGRADE: Richer system prompt with explicit instructions
    system_prompt = f"""You are SmartLoop AI, an expert tutor for Grade {grade}.
{style}

INSTRUCTIONS:
- Answer ONLY from the provided textbook excerpts when possible
- If the excerpts cover the topic, cite which page/source your answer comes from
- If excerpts are insufficient, clearly say so and supplement from your knowledge
- Structure complex answers with clear steps or numbered points
- End with a one-sentence summary if the answer is long
- Never refuse to answer; always provide the most helpful response possible"""

    prompt = f"""TEXTBOOK EXCERPTS:
{context}

RECENT CONVERSATION:
{hist}

STUDENT QUESTION: {question}

Answer:"""

    # Try streaming with primary key
    for _ in range(max(1, len(PRIMARY_ANS_KEYS))):
        try:
            c = get_primary()
            if c and stream_placeholder:
                # Streaming response
                stream = c.chat.completions.create(
                    model="gpt-4o-mini",  # UPGRADE: use GPT-4o-mini for better quality
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    stream=True
                )
                ans = ""
                for delta in stream:
                    piece = delta.choices[0].delta.content or ""
                    ans += piece
                    stream_placeholder.markdown(ans + "▌")
                stream_placeholder.markdown(ans)
                if ans and len(ans) > 20 and not is_weak_answer(ans, question):
                    return ans, "pdf", src
            elif c:
                r = c.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000
                )
                ans = r.choices[0].message.content.strip()
                if ans and len(ans) > 20 and not is_weak_answer(ans, question):
                    return ans, "pdf", src
        except:
            time.sleep(0.5)

    # Fallback to extra key
    try:
        c = get_extra()
        if c:
            r = c.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": system_prompt + "\n\n" + prompt}],
                max_tokens=900
            )
            ans = r.choices[0].message.content.strip()
            if ans and len(ans) > 20:
                return ans, "pdf", src
    except:
        pass

    return None, None, None

# =========================
# TIER 2: AI ANSWER — upgraded model + streaming
# =========================
def answer_from_ai(question, grade, history, stream_placeholder=None):
    style = grade_style(grade)

    # Build proper message history
    messages = [{
        "role": "system",
        "content": (
            f"You are SmartLoop AI, an expert academic tutor for Grade {grade}. "
            f"{style} "
            f"Always give complete, accurate, structured answers. "
            f"Use numbered steps for processes, bullet points for lists. "
            f"Never refuse to answer academic questions."
        )
    }]
    for m in history[-6:]:
        messages.append({
            "role": m["role"],
            "content": m.get("content", "")[:500]
        })
    messages.append({"role": "user", "content": question})

    # Google Gemini first
    for _ in range(min(2, max(1, len(ALL_GOOGLE_KEYS)))):
        try:
            c = get_google()
            if c:
                hist_text = "\n".join([
                    f"{'Student' if m['role']=='user' else 'AI'}: {m.get('content','')[:200]}"
                    for m in history[-4:]
                ])
                full_prompt = (
                    f"You are SmartLoop AI for Grade {grade}. {style}\n"
                    f"Previous conversation:\n{hist_text}\n\n"
                    f"Question: {question}\nAnswer:"
                )
                r = c.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=full_prompt
                )
                if r.text and len(r.text.strip()) > 20:
                    ans = r.text.strip()
                    if not is_weak_answer(ans, question):
                        if stream_placeholder:
                            stream_placeholder.markdown(ans)
                        return ans, "ai", None
        except:
            time.sleep(0.5)

    # Primary OpenAI with streaming
    for _ in range(max(1, len(PRIMARY_ANS_KEYS))):
        try:
            c = get_primary()
            if c and stream_placeholder:
                stream = c.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=900,
                    stream=True
                )
                ans = ""
                for delta in stream:
                    piece = delta.choices[0].delta.content or ""
                    ans += piece
                    stream_placeholder.markdown(ans + "▌")
                stream_placeholder.markdown(ans)
                if ans and len(ans) > 20 and not is_weak_answer(ans, question):
                    return ans, "ai", None
            elif c:
                r = c.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=900
                )
                ans = r.choices[0].message.content.strip()
                if ans and len(ans) > 20 and not is_weak_answer(ans, question):
                    return ans, "ai", None
        except:
            time.sleep(0.5)

    # Extra OpenAI
    try:
        c = get_extra()
        if c:
            r = c.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=800
            )
            ans = r.choices[0].message.content.strip()
            if ans and len(ans) > 20:
                return ans, "ai", None
    except:
        pass

    return None, None, None

# =========================
# TIER 3: DUCKDUCKGO
# =========================
BAD_CONTENT = [
    "comic","marvel","dc comics","film","movie",
    "tv series","television","album","song","band",
    "actor","actress","footballer","celebrity"
]

def answer_from_duckduckgo(question):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        search_q = re.sub(
            r"(what is|what are|explain|define|"
            r"how does|tell me about|describe)",
            "", question.lower()
        ).strip()

        api_url = (
            f"https://api.duckduckgo.com/?q="
            f"{requests.utils.quote(search_q + ' school definition')}"
            f"&format=json&no_html=1&skip_disambig=1"
        )
        resp = requests.get(api_url, headers=headers, timeout=8)
        data = resp.json()

        result_text = ""
        if data.get("AbstractText") and len(data["AbstractText"]) > 50:
            result_text = data["AbstractText"]
        elif data.get("Answer") and len(data["Answer"]) > 10:
            result_text = data["Answer"]
        elif data.get("Definition") and len(data["Definition"]) > 20:
            result_text = data["Definition"]
        elif data.get("RelatedTopics"):
            snippets = []
            for topic in data["RelatedTopics"][:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    snippets.append(topic["Text"])
            if snippets:
                result_text = " ".join(snippets[:2])

        if result_text and len(result_text) > 40:
            if not any(b in result_text.lower() for b in BAD_CONTENT):
                return result_text, "ddg", None

        search_url = (
            f"https://html.duckduckgo.com/html/?q="
            f"{requests.utils.quote(search_q + ' academic definition school')}"
        )
        resp2   = requests.get(search_url, headers=headers, timeout=8)
        soup    = BeautifulSoup(resp2.text, "html.parser")
        snippets = []
        for result in soup.select(".result__snippet")[:5]:
            text = result.get_text(strip=True)
            if len(text) > 40 and not any(b in text.lower() for b in BAD_CONTENT):
                snippets.append(text)

        if snippets:
            combined = " ".join(snippets[:2])
            if len(combined) > 50:
                return combined, "ddg", None

    except Exception as e:
        print(f"DDG error: {e}")

    return None, None, None

# =========================
# TIER 4: WIKIPEDIA
# =========================
def answer_from_wiki(question):
    try:
        search_q = re.sub(
            r"(what is|what are|explain|define|"
            r"how does|tell me about|describe)",
            "", question.lower()
        ).strip()

        search_results = wikipedia.search(
            search_q + " mathematics science", results=5
        )
        academic_kw = [
            "physics","chemistry","biology","mathematics",
            "science","history","geography","economics",
            "force","energy","cell","atom","equation",
            "decimal","fraction","geometry","algebra"
        ]
        best = None
        for result in search_results:
            if any(k in result.lower() for k in academic_kw):
                best = result
                break
        if not best and search_results:
            best = search_results[0]
        if not best:
            return None, None, None

        result = wikipedia.summary(best, sentences=4)  # UPGRADE: 4 sentences
        if any(b in result.lower() for b in BAD_CONTENT + [
            "may refer to","disambiguation","is a list"
        ]):
            return None, None, None

        return result, "wiki", None

    except wikipedia.exceptions.DisambiguationError as e:
        try:
            bad_opts = ["film","comic","song","album","band","tv"]
            best = next(
                (o for o in e.options if not any(
                    b in o.lower() for b in bad_opts
                )),
                e.options[0] if e.options else None
            )
            if not best:
                return None, None, None
            result = wikipedia.summary(best, sentences=4)
            if any(b in result.lower() for b in ["comic","marvel","film"]):
                return None, None, None
            return result, "wiki", None
        except:
            return None, None, None
    except:
        return None, None, None

# =========================
# MAIN PIPELINE — upgraded
# calc → query_rewrite → multi_query_bm25 → rerank → pdf → ai → ddg → wiki
# =========================
def smartloop(question, grade, history, thinking_ph, stream_ph=None):

    # Step 0: Math shortcut
    if is_pure_calc(question):
        update_phase(thinking_ph, "Calculating")
        ans, tier = solve_math(question)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans, tier, None

    # Step 1: Contextual query rewriting
    update_phase(thinking_ph, "Understanding question")
    rewritten_q = rewrite_query(question, history)

    # Step 2: Multi-query expansion + BM25 retrieval
    update_phase(thinking_ph, "Searching textbooks")
    queries = expand_queries(rewritten_q)

    # Run BM25 for each query variant in parallel
    all_ranked_lists = []
    with ThreadPoolExecutor(max_workers=len(queries)) as ex:
        futures = [ex.submit(bm25_search, q, 10) for q in queries]
        for f in as_completed(futures):
            result = f.result()
            if result:
                all_ranked_lists.append(result)

    # Step 3: Reciprocal Rank Fusion
    if all_ranked_lists:
        fused_candidates = reciprocal_rank_fusion(all_ranked_lists)
    else:
        fused_candidates = []

    # Step 4: GPT Reranking
    update_phase(thinking_ph, "Ranking relevant content")
    good_chunks = []
    if fused_candidates:
        good_chunks = parallel_rerank(fused_candidates[:10], rewritten_q)

    # Step 5: Generate answer
    update_phase(thinking_ph, "Generating answer")

    if good_chunks:
        ans, tier, src = answer_from_pdf(
            question, good_chunks, grade, history, stream_ph
        )
        if ans:
            return ans, tier, src

    ans, tier, src = answer_from_ai(question, grade, history, stream_ph)
    if ans:
        return ans, tier, src

    update_phase(thinking_ph, "Searching web")
    ans, tier, src = answer_from_duckduckgo(question)
    if ans:
        if stream_ph:
            stream_ph.markdown(ans)
        return ans, tier, src

    ans, tier, src = answer_from_wiki(question)
    if ans:
        if stream_ph:
            stream_ph.markdown(ans)
        return ans, tier, src

    fallback = (
        "All sources are currently unavailable. "
        "Please check your API keys in Streamlit secrets."
    )
    if stream_ph:
        stream_ph.markdown(fallback)
    return fallback, "", None

# =========================
# BADGE HELPER
# =========================
def show_badge(tier, source):
    badges = {
        "pdf":  ("src-pdf",  f"📖 {source}"),
        "ai":   ("src-ai",   "💡 AI knowledge"),
        "ddg":  ("src-ddg",  "🦆 DuckDuckGo"),
        "wiki": ("src-wiki", "🌐 Wikipedia"),
        "calc": ("src-calc", "🧮 Calculator"),
    }
    if tier in badges:
        cls, label = badges[tier]
        if tier == "pdf" and not source:
            return
        st.markdown(
            f'<span class="source-badge {cls}">{label}</span>',
            unsafe_allow_html=True
        )

# =========================
# LOAD PDFs
# =========================
with st.spinner("📚 Loading library..."):
    PDF_CHUNKS = load_all_pdfs(st.session_state.grade)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(
        f"<div class='welcome-card'>"
        f"👋 Welcome! Grade {st.session_state.grade}"
        f"</div>",
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
        st.cache_resource.clear()
        st.rerun()

    st.divider()

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()

    st.markdown(
        "<div class='section-label'>💬 Chats</div>",
        unsafe_allow_html=True
    )

    for chat_name in list(reversed(list(st.session_state.chats.keys()))):
        is_active = (chat_name == st.session_state.current_chat)
        col1, col2 = st.columns([0.82, 0.18], vertical_alignment="center")
        msgs       = st.session_state.chats.get(chat_name, [])
        first_user = next(
            (m["content"] for m in msgs if m["role"] == "user"),
            chat_name
        )
        title = first_user[:22] + "..." if len(first_user) > 22 else first_user
        label = f"{'🟢' if is_active else '💬'} {title}"

        if col1.button(label, key=f"ch_{chat_name}", use_container_width=True):
            st.session_state.current_chat = chat_name
            st.rerun()

        if col2.button("🗑", key=f"dl_{chat_name}", use_container_width=True):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[chat_name]
                if st.session_state.current_chat == chat_name:
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                st.rerun()

    st.divider()
    st.success(f"📚 {len(PDF_CHUNKS)} chunks loaded")
    st.info(
        f"🔑 OpenAI: {len(ALL_OPENAI_KEYS)} | "
        f"Google: {len(ALL_GOOGLE_KEYS)}"
    )

    with st.expander("⚙️ RAG Info"):
        st.caption("**Retrieval:** BM25 + Multi-query RRF")
        st.caption("**Reranking:** GPT numeric scorer")
        st.caption("**Model:** GPT-4o-mini / Gemini Flash")
        st.caption("**Context:** 6-turn history")

    if st.button("🔄 Change Grade", use_container_width=True):
        st.session_state.grade = None
        st.cache_resource.clear()
        st.rerun()

    with st.expander("🏫 Are you a Teacher?"):
        code = st.text_input(
            "Code", type="password",
            placeholder="Enter school code...",
            label_visibility="collapsed"
        )
        if st.button("Verify", use_container_width=True):
            if code == st.secrets.get("TEACHER_CODE", ""):
                st.success("✅ Teacher access granted!")
            else:
                st.error("Invalid code.")

# =========================
# MAIN CHAT UI
# =========================
st.markdown(f"""
<div style='text-align:center; padding:20px 0 8px;'>
    <span style='font-size:44px; font-weight:800; color:#00d4ff;
        letter-spacing:-2px;
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

messages = st.session_state.chats.get(st.session_state.current_chat, [])

if not messages:
    with st.chat_message("assistant"):
        st.markdown(
            f"👋 **Hey! I'm SmartLoop AI!**\n\n"
            f"I'm your Grade {st.session_state.grade} tutor — now smarter than ever.\n\n"
            f"- 📖 **BM25 + Multi-query** textbook search\n"
            f"- 🔁 **Query rewriting** for follow-up questions\n"
            f"- 🎯 **GPT reranker** picks the best excerpts\n"
            f"- 🤖 **GPT-4o-mini** for higher quality answers\n"
            f"- ⚡ **Streaming** responses in real time\n\n"
            f"*What would you like to learn today?*"
        )

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content", ""))
        show_badge(msg.get("tier", ""), msg.get("source", ""))

# =========================
# CHAT INPUT
# =========================
q = st.chat_input("Ask SmartLoop...")

if q:
    messages = st.session_state.chats[st.session_state.current_chat]
    messages.append({"role": "user", "content": q})

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        thinking   = st.empty()
        stream_box = st.empty()  # Streaming target

        ans, tier, source = smartloop(
            q,
            st.session_state.grade,
            messages[:-1],
            thinking,
            stream_box
        )

        thinking.empty()

        # If stream_box already has content, don't re-render
        if not stream_box._provided_cursor:
            stream_box.markdown(ans)

        show_badge(tier, source)

    messages.append({
        "role":    "assistant",
        "content": ans,
        "tier":    tier,
        "source":  source
    })
