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

# =============================================================================
# API KEY SETUP
# Accepts both OPENAI_API_KEY and OPENAI_API_KEY_1..5 (same for Google).
# All keys are pooled — any key can be used for any purpose.
# =============================================================================
def _collect_keys(prefix, plain_name):
    keys = [st.secrets.get(f"{prefix}_{i}") for i in range(1, 6)]
    keys = [k for k in keys if k]
    plain = st.secrets.get(plain_name)
    if plain and plain not in keys:
        keys.insert(0, plain)
    return keys

ALL_OPENAI_KEYS = _collect_keys("OPENAI_API_KEY", "OPENAI_API_KEY")
ALL_GOOGLE_KEYS = _collect_keys("GOOGLE_API_KEY", "GOOGLE_API_KEY")

if not ALL_OPENAI_KEYS and not ALL_GOOGLE_KEYS:
    st.error("No API keys found. Add OPENAI_API_KEY or GOOGLE_API_KEY to Streamlit secrets.")
    st.stop()

_openai_cycle = itertools.cycle(ALL_OPENAI_KEYS) if ALL_OPENAI_KEYS else None
_google_cycle = itertools.cycle(ALL_GOOGLE_KEYS) if ALL_GOOGLE_KEYS else None


def call_llm(messages: list, max_tokens: int = 900,
             temperature: float = 0.3, stream_ph=None) -> str | None:
    """
    Unified LLM caller. Tries Google Gemini first (fast/free quota),
    then cycles through all OpenAI keys. Handles streaming.
    Never raises — returns str or None.
    """
    # --- Google Gemini ---
    if _google_cycle:
        for _ in range(min(2, len(ALL_GOOGLE_KEYS))):
            try:
                client = genai.Client(api_key=next(_google_cycle))
                prompt = "\n\n".join(
                    f"[{m['role'].upper()}]: {m['content']}" for m in messages
                )
                r = client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt
                )
                txt = (r.text or "").strip()
                if len(txt) > 15:
                    if stream_ph:
                        stream_ph.markdown(txt)
                    return txt
            except Exception as e:
                print(f"Gemini error: {e}")
                time.sleep(0.3)

    # --- OpenAI — try every key once ---
    if _openai_cycle:
        for _ in range(len(ALL_OPENAI_KEYS)):
            try:
                client = OpenAI(api_key=next(_openai_cycle))
                if stream_ph:
                    stream = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=True,
                    )
                    ans = ""
                    for chunk in stream:
                        piece = chunk.choices[0].delta.content or ""
                        ans += piece
                        stream_ph.markdown(ans + "▌")
                    stream_ph.markdown(ans)
                    if len(ans) > 15:
                        return ans
                else:
                    r = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    ans = r.choices[0].message.content.strip()
                    if len(ans) > 15:
                        return ans
            except Exception as e:
                print(f"OpenAI error: {e}")
                time.sleep(0.3)

    return None


def call_llm_short(prompt: str, max_tokens: int = 60) -> str | None:
    """Quick single-turn call for classify/rewrite tasks. No streaming."""
    return call_llm(
        [{"role": "user", "content": prompt}],
        max_tokens=max_tokens, temperature=0
    )

# =============================================================================
# GRADE SELECTION
# =============================================================================
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
            "Grade", [f"Grade {i}" for i in range(1, 11)],
            index=5, label_visibility="collapsed"
        )
        if st.button("Get Started →", use_container_width=True, type="primary"):
            st.session_state.grade = int(grade.split()[1])
            st.rerun()
    st.stop()

# =============================================================================
# PDF LOADING — overlapping BM25-ready chunks
# =============================================================================
def get_allowed_grades(grade):
    return {6: [6, 7], 7: [7, 8], 8: [8, 9]}.get(grade, [grade])

def grade_matches_file(fname, allowed_grades):
    name = fname.lower().replace(".pdf", "")
    for g in allowed_grades:
        if any(p in name for p in [
            str(g), f"grade{g}", f"grade_{g}", f"class{g}",
            f"std{g}", f"g{g}", f"{g}th", f"{g}st", f"{g}nd", f"{g}rd"
        ]):
            return True
    return False

def extract_pdf_smart(fname):
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if len(text) < 60:
                continue
            words = text.split()
            step, size = 250, 400
            for i in range(0, max(1, len(words)), step):
                chunk_words = words[i:i + size]
                if len(chunk_words) < 20:
                    continue
                chunk_text = " ".join(chunk_words)
                clean = re.sub(r'[^a-z0-9 ]', ' ', chunk_text.lower())
                freq = defaultdict(int)
                for w in clean.split():
                    freq[w] += 1
                chunks.append({
                    "text":      chunk_text,
                    "word_freq": dict(freq),
                    "words":     set(freq.keys()),
                    "file":      fname,
                    "page":      page_num + 1,
                    "chunk_i":   i,
                })
        doc.close()
    except Exception as e:
        print(f"PDF error {fname}: {e}")
    return chunks

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
        w: math.log((_CORPUS_SIZE - freq + 0.5) / (freq + 0.5) + 1)
        for w, freq in df.items()
    }

@st.cache_resource(show_spinner=False)
def load_all_pdfs(grade):
    allowed    = get_allowed_grades(grade)
    pdf_files  = [f for f in os.listdir(".") if f.endswith(".pdf")]
    grade_pdfs = [f for f in pdf_files if grade_matches_file(f, allowed)]
    if not grade_pdfs:
        grade_pdfs = pdf_files
    all_chunks = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(extract_pdf_smart, f): f for f in grade_pdfs}
        for fut in as_completed(futures):
            all_chunks.extend(fut.result())
    _build_idf(all_chunks)
    return all_chunks

with st.spinner("📚 Loading library..."):
    PDF_CHUNKS = load_all_pdfs(st.session_state.grade)

# =============================================================================
# SESSION STATE
# =============================================================================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# =============================================================================
# MATH SHORTCUT
# =============================================================================
def is_pure_calc(q):
    return bool(re.fullmatch(r"[\d\.\+\-\*\/\(\)\s\^%]+", q.strip()))

def solve_math(q):
    try:
        result = eval(q.strip().replace("^", "**").replace(" ", ""),
                      {"__builtins__": None}, {})
        return f"**= {round(result, 8)}**", "calc"
    except:
        return None, None

# =============================================================================
# BM25 RETRIEVAL
# =============================================================================
STOPWORDS = {
    "what", "is", "are", "how", "why", "when", "who", "the", "a", "an",
    "of", "in", "to", "and", "does", "do", "explain", "define", "me",
    "about", "give", "please", "describe", "tell", "example", "examples",
    "find", "solve", "calculate", "show", "write", "can", "you", "i",
    "my", "we", "our", "its", "it", "was", "were", "will", "be", "for"
}

def tokenize(q: str) -> list:
    return [
        w for w in re.sub(r'[^a-z0-9 ]', ' ', q.lower()).split()
        if w not in STOPWORDS and len(w) > 1
    ]

def bm25_score(chunk, q_words, k1=1.5, b=0.75):
    dl = sum(chunk["word_freq"].values())
    score = 0.0
    for w in q_words:
        if w not in chunk["word_freq"]:
            continue
        tf  = chunk["word_freq"][w]
        idf = _IDF.get(w, 0.5)
        num = tf * (k1 + 1)
        den = tf + k1 * (1 - b + b * dl / max(_AVG_DL, 1))
        score += idf * (num / den)
    return score

def bm25_search(query: str, top_k: int = 12) -> list:
    if not PDF_CHUNKS:
        return []
    q_words = tokenize(query)
    if not q_words:
        return []
    scored = [(bm25_score(c, q_words), c) for c in PDF_CHUNKS]
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][0] if scored else 0
    if best <= 0:
        return []
    threshold = max(0.3, best * 0.10)
    return [c for sc, c in scored[:top_k] if sc >= threshold]

def reciprocal_rank_fusion(ranked_lists: list, k: int = 60) -> list:
    scores    = defaultdict(float)
    chunk_map = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            key = (chunk["file"], chunk["page"], chunk.get("chunk_i", 0))
            scores[key] += 1.0 / (k + rank + 1)
            chunk_map[key] = chunk
    return [chunk_map[k] for k in sorted(scores, key=lambda x: scores[x], reverse=True)]

# =============================================================================
# QUERY REWRITING
# =============================================================================
def rewrite_query(question: str, history: list) -> str:
    if len(history) < 2:
        return question
    recent = "\n".join([
        f"{'Student' if m['role']=='user' else 'AI'}: {m.get('content','')[:200]}"
        for m in history[-4:]
    ])
    prompt = (
        f"Conversation:\n{recent}\n\n"
        f"Rewrite the student's question as a self-contained textbook search query "
        f"(no pronouns, include the topic). Return ONLY the rewritten query.\n"
        f"Question: {question}\nRewritten:"
    )
    result = call_llm_short(prompt, max_tokens=60)
    return result.strip() if result else question

# =============================================================================
# ZERO-API TEXT EXTRACTION FALLBACK
# Works even when all API keys are unavailable or rate-limited.
# Extracts the most relevant sentences directly from PDF text.
# =============================================================================
def extract_answer_from_text(question: str, chunks: list, grade: int) -> str | None:
    q_words = set(tokenize(question))
    sentence_scores = []

    for chunk in chunks[:6]:
        sentences = re.split(r'(?<=[.!?])\s+', chunk["text"])
        for sent in sentences:
            if len(sent.split()) < 6:
                continue
            overlap = len(q_words & set(tokenize(sent)))
            if overlap > 0:
                sentence_scores.append((overlap, sent.strip()))

    sentence_scores.sort(key=lambda x: x[0], reverse=True)
    # Deduplicate
    seen, top = set(), []
    for _, sent in sentence_scores:
        key = sent[:40]
        if key not in seen:
            seen.add(key)
            top.append(sent)
        if len(top) >= 7:
            break

    if not top and chunks:
        top = [chunks[0]["text"][:800]]

    if not top:
        return None

    src    = chunks[0]["file"]
    joined = " ".join(top)

    if grade <= 4:
        prefix = "Here's what your textbook says:\n\n"
    elif grade <= 7:
        prefix = "Your textbook explains:\n\n"
    else:
        prefix = "According to your textbook:\n\n"

    return f"{prefix}{joined}\n\n*📖 Source: {src}*"

# =============================================================================
# GRADE STYLE
# =============================================================================
def grade_style(g):
    if g <= 3:
        return "Use very simple words, short sentences, and fun examples like a story."
    elif g <= 6:
        return "Use clear simple language with relatable everyday examples."
    elif g <= 8:
        return "Use clear academic language with key terms and worked examples."
    else:
        return "Use detailed academic language suitable for high school students."

# =============================================================================
# THINKING ANIMATION
# =============================================================================
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

# =============================================================================
# TIER 1: PDF ANSWER
# LLM-assisted answer from retrieved chunks; falls back to raw text extraction.
# =============================================================================
def answer_from_pdf(question, chunks, grade, history, stream_ph=None):
    context = "\n\n---\n\n".join([
        f"[{c['file']}, page {c['page']}]\n{c['text']}"
        for c in chunks[:5]
    ])
    src   = chunks[0]["file"]
    style = grade_style(grade)
    hist  = "\n".join([
        f"{'Student' if m['role']=='user' else 'SmartLoop'}: {m.get('content','')[:300]}"
        for m in history[-6:]
    ])

    system = (
        f"You are SmartLoop AI, an expert tutor for Grade {grade}. {style}\n"
        "INSTRUCTIONS:\n"
        "- Answer using the textbook excerpts below.\n"
        "- Be thorough, accurate, and age-appropriate.\n"
        "- Mention the page number where you found the information.\n"
        "- If excerpts are insufficient, say so briefly then help from your knowledge.\n"
        "- Always provide a complete, helpful answer."
    )
    user_msg = (
        f"TEXTBOOK EXCERPTS:\n{context}\n\n"
        f"CONVERSATION HISTORY:\n{hist}\n\n"
        f"STUDENT QUESTION: {question}\n\nAnswer:"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_msg},
    ]

    ans = call_llm(messages, max_tokens=1000, temperature=0.3, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "pdf", src

    # Zero-API fallback
    fallback = extract_answer_from_text(question, chunks, grade)
    if fallback:
        if stream_ph:
            stream_ph.markdown(fallback)
        return fallback, "pdf", src

    return None, None, None

# =============================================================================
# TIER 2: GENERAL AI ANSWER
# =============================================================================
def answer_from_ai(question, grade, history, stream_ph=None):
    style = grade_style(grade)
    messages = [{
        "role": "system",
        "content": (
            f"You are SmartLoop AI, expert academic tutor for Grade {grade}. "
            f"{style} Give complete, structured, accurate answers. "
            "Use numbered steps or bullet points where helpful. "
            "Never refuse academic questions."
        ),
    }]
    for m in history[-6:]:
        messages.append({"role": m["role"], "content": m.get("content", "")[:500]})
    messages.append({"role": "user", "content": question})

    ans = call_llm(messages, max_tokens=900, temperature=0.4, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "ai", None
    return None, None, None

# =============================================================================
# TIER 3: DUCKDUCKGO
# =============================================================================
BAD_CONTENT = [
    "comic", "marvel", "dc comics", "film", "movie", "tv series",
    "television", "album", "song", "band", "actor", "actress",
    "footballer", "celebrity"
]

def answer_from_duckduckgo(question):
    try:
        headers = {"User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )}
        search_q = re.sub(
            r"(what is|what are|explain|define|how does|tell me about|describe)",
            "", question.lower()
        ).strip()

        data = requests.get(
            f"https://api.duckduckgo.com/?q={requests.utils.quote(search_q + ' school definition')}"
            f"&format=json&no_html=1&skip_disambig=1",
            headers=headers, timeout=8
        ).json()

        result_text = (
            data.get("AbstractText") or data.get("Answer") or data.get("Definition") or ""
        )
        if not result_text:
            topics = data.get("RelatedTopics", [])
            result_text = " ".join(
                t["Text"] for t in topics[:3]
                if isinstance(t, dict) and t.get("Text")
            )

        if len(result_text) > 40 and not any(b in result_text.lower() for b in BAD_CONTENT):
            return result_text, "ddg", None

        # HTML scrape fallback
        soup = BeautifulSoup(
            requests.get(
                f"https://html.duckduckgo.com/html/?q={requests.utils.quote(search_q + ' academic school')}",
                headers=headers, timeout=8
            ).text, "html.parser"
        )
        snippets = [
            r.get_text(strip=True) for r in soup.select(".result__snippet")[:5]
            if len(r.get_text(strip=True)) > 40
            and not any(b in r.get_text(strip=True).lower() for b in BAD_CONTENT)
        ]
        if snippets:
            combined = " ".join(snippets[:2])
            if len(combined) > 50:
                return combined, "ddg", None
    except Exception as e:
        print(f"DDG error: {e}")
    return None, None, None

# =============================================================================
# TIER 4: WIKIPEDIA
# =============================================================================
def answer_from_wiki(question):
    try:
        search_q = re.sub(
            r"(what is|what are|explain|define|how does|tell me about|describe)",
            "", question.lower()
        ).strip()
        results = wikipedia.search(search_q + " mathematics science", results=5)
        academic_kw = [
            "physics", "chemistry", "biology", "mathematics", "science",
            "history", "geography", "economics", "force", "energy", "cell",
            "atom", "equation", "decimal", "fraction", "geometry", "algebra"
        ]
        best = next(
            (r for r in results if any(k in r.lower() for k in academic_kw)),
            results[0] if results else None
        )
        if not best:
            return None, None, None
        summary = wikipedia.summary(best, sentences=4)
        if any(b in summary.lower() for b in BAD_CONTENT + ["may refer to", "disambiguation"]):
            return None, None, None
        return summary, "wiki", None
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            bad = ["film", "comic", "song", "album", "band", "tv"]
            best = next(
                (o for o in e.options if not any(b in o.lower() for b in bad)),
                e.options[0] if e.options else None
            )
            if not best:
                return None, None, None
            summary = wikipedia.summary(best, sentences=4)
            if any(b in summary.lower() for b in ["comic", "marvel", "film"]):
                return None, None, None
            return summary, "wiki", None
        except:
            return None, None, None
    except:
        return None, None, None

# =============================================================================
# MAIN PIPELINE
# calc → rewrite → BM25+RRF → pdf_answer → ai → ddg → wiki → text_extract
# =============================================================================
def smartloop(question, grade, history, thinking_ph, stream_ph=None):

    # Step 0: Math shortcut
    if is_pure_calc(question):
        update_phase(thinking_ph, "Calculating")
        ans, tier = solve_math(question)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans, tier, None

    # Step 1: Query rewriting
    update_phase(thinking_ph, "Understanding question")
    rewritten = rewrite_query(question, history)

    # Step 2: BM25 multi-query retrieval
    update_phase(thinking_ph, "Searching textbooks")
    queries = list(dict.fromkeys([question, rewritten]))  # deduplicate, preserve order
    ranked_lists = [r for r in (bm25_search(q, top_k=12) for q in queries) if r]
    good_chunks  = reciprocal_rank_fusion(ranked_lists)[:8] if ranked_lists else []

    # Step 3: PDF answer (LLM + zero-API fallback baked in)
    update_phase(thinking_ph, "Reading textbook")
    if good_chunks:
        ans, tier, src = answer_from_pdf(question, good_chunks, grade, history, stream_ph)
        if ans:
            return ans, tier, src

    # Step 4: General AI answer
    update_phase(thinking_ph, "Thinking")
    ans, tier, src = answer_from_ai(question, grade, history, stream_ph)
    if ans:
        return ans, tier, src

    # Step 5: Web
    update_phase(thinking_ph, "Searching web")
    for fn in [answer_from_duckduckgo, answer_from_wiki]:
        ans, tier, src = fn(question)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans, tier, src

    # Step 6: Last resort — raw text extraction (no API needed)
    if good_chunks:
        fallback = extract_answer_from_text(question, good_chunks, grade)
        if fallback:
            if stream_ph:
                stream_ph.markdown(fallback)
            return fallback, "pdf", good_chunks[0]["file"]

    msg = "I couldn't find a good answer right now. Try rephrasing your question!"
    if stream_ph:
        stream_ph.markdown(msg)
    return msg, "", None

# =============================================================================
# BADGE HELPER
# =============================================================================
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

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown(
        f"<div class='welcome-card'>👋 Welcome! Grade {st.session_state.grade}</div>",
        unsafe_allow_html=True
    )
    st.divider()

    st.markdown("<div class='section-label'>🎯 Active Grade</div>", unsafe_allow_html=True)
    new_grade = st.selectbox(
        "Grade", [f"Grade {i}" for i in range(1, 11)],
        index=st.session_state.grade - 1, label_visibility="collapsed"
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

    st.markdown("<div class='section-label'>💬 Chats</div>", unsafe_allow_html=True)

    for chat_name in list(reversed(list(st.session_state.chats.keys()))):
        is_active = (chat_name == st.session_state.current_chat)
        col1, col2 = st.columns([0.82, 0.18], vertical_alignment="center")
        msgs = st.session_state.chats.get(chat_name, [])
        first_user = next((m["content"] for m in msgs if m["role"] == "user"), chat_name)
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
    n_oa = len(ALL_OPENAI_KEYS)
    n_go = len(ALL_GOOGLE_KEYS)
    st.info(f"🔑 OpenAI: {n_oa} key{'s' if n_oa!=1 else ''} | Google: {n_go} key{'s' if n_go!=1 else ''}")

    with st.expander("⚙️ Pipeline"):
        st.caption("**Retrieval:** BM25 + RRF multi-query")
        st.caption("**LLM:** Gemini Flash → GPT-4o-mini")
        st.caption("**Fallback:** Direct PDF text extraction")
        st.caption("**Context:** Last 6 conversation turns")

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

# =============================================================================
# MAIN CHAT UI
# =============================================================================
st.markdown(f"""
<div style='text-align:center; padding:20px 0 8px;'>
    <span style='font-size:44px; font-weight:800; color:#00d4ff;
        letter-spacing:-2px; text-shadow:0 0 16px rgba(0,212,255,0.45);'>
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
            f"I'm your Grade {st.session_state.grade} tutor.\n\n"
            f"- 📖 **Textbooks first** — BM25 search across your PDFs\n"
            f"- 🤖 **AI fallback** — Gemini Flash or GPT-4o-mini\n"
            f"- 🦆 **Web backup** — DuckDuckGo + Wikipedia\n"
            f"- 📄 **Always answers** — even if APIs go down\n"
            f"- 🧮 **Maths solver** — instant calculations\n\n"
            f"*What would you like to learn today?*"
        )

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content", ""))
        show_badge(msg.get("tier", ""), msg.get("source", ""))

# =============================================================================
# CHAT INPUT
# =============================================================================
q = st.chat_input("Ask SmartLoop...")

if q:
    messages = st.session_state.chats[st.session_state.current_chat]
    messages.append({"role": "user", "content": q})

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        thinking_ph = st.empty()
        stream_ph   = st.empty()

        ans, tier, source = smartloop(
            q,
            st.session_state.grade,
            messages[:-1],
            thinking_ph,
            stream_ph,
        )

        thinking_ph.empty()

        # Ensure answer is always visible (covers non-streaming paths)
        if not ans:
            ans = "Sorry, something went wrong. Please try again."
        stream_ph.markdown(ans)

        show_badge(tier, source)

    messages.append({
        "role":    "assistant",
        "content": ans,
        "tier":    tier,
        "source":  source,
    })
