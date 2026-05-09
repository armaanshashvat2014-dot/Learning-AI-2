import streamlit as st
import re, os, time, itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
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
# API KEYS — accepts OPENAI_API_KEY or OPENAI_API_KEY_1..5 (same for Google)
# =============================================================================
def _collect_keys(numbered_prefix, plain_name):
    keys = [st.secrets.get(f"{numbered_prefix}_{i}") for i in range(1, 6)]
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
 
# Phrases that mean the LLM refused — we detect and discard these
REFUSAL_PHRASES = [
    "i cannot", "i can't", "i am unable", "i'm unable",
    "i don't have", "i do not have", "not able to",
    "cannot provide", "unable to provide", "cannot answer",
    "no information", "not found in", "not covered",
    "beyond my", "outside my", "i'm sorry, but",
    "i am sorry", "as an ai", "as a language model",
    "i lack", "i cannot find",
]
 
def is_refusal(text):
    low = text.lower()
    return any(p in low for p in REFUSAL_PHRASES)
 
def call_llm(messages, max_tokens=900, temperature=0.3, stream_ph=None):
    """
    Unified LLM caller. Tries Gemini first, then all OpenAI keys.
    Detects refusal responses and retries with a stronger prompt.
    Never raises — returns str or None.
    """
    # ── Gemini ──
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
                if len(txt) > 15 and not is_refusal(txt):
                    if stream_ph:
                        stream_ph.markdown(txt)
                    return txt
            except Exception as e:
                print(f"Gemini error: {e}")
                time.sleep(0.3)
 
    # ── OpenAI — try every key ──
    if _openai_cycle:
        for _ in range(len(ALL_OPENAI_KEYS)):
            try:
                client = OpenAI(api_key=next(_openai_cycle))
                if stream_ph:
                    stream = client.chat.completions.create(
                        model="gpt-3.5-turbo",
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
                    if len(ans) > 15 and not is_refusal(ans):
                        return ans
                    if stream_ph:
                        stream_ph.empty()   # wipe refusal, retry
                else:
                    r = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    ans = r.choices[0].message.content.strip()
                    if len(ans) > 15 and not is_refusal(ans):
                        return ans
            except Exception as e:
                print(f"OpenAI error: {e}")
                time.sleep(0.3)
 
    # ── Second pass: strip system prompt, add hard "never refuse" directive ──
    fallback_msgs = [
        {
            "role": "system",
            "content": (
                "You are a helpful tutor. You MUST always give a complete answer. "
                "NEVER say you cannot help or cannot find information. "
                "If unsure, give your best explanation. Silence or refusal is not acceptable."
            )
        }
    ] + [m for m in messages if m["role"] != "system"]
 
    if _openai_cycle:
        for _ in range(len(ALL_OPENAI_KEYS)):
            try:
                client = OpenAI(api_key=next(_openai_cycle))
                r = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=fallback_msgs,
                    max_tokens=max_tokens,
                    temperature=0.5,
                )
                ans = r.choices[0].message.content.strip()
                if len(ans) > 15:
                    if stream_ph:
                        stream_ph.markdown(ans)
                    return ans
            except Exception as e:
                print(f"OpenAI fallback error: {e}")
                time.sleep(0.3)
 
    return None
 
def call_llm_short(prompt, max_tokens=60):
    """Quick single-turn call, no streaming."""
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
            "Grade",
            [f"Grade {i}" for i in range(1, 11)],
            index=5,
            label_visibility="collapsed"
        )
        if st.button("Get Started →", use_container_width=True, type="primary"):
            st.session_state.grade = int(grade.split()[1])
            st.rerun()
    st.stop()
 
# =============================================================================
# PDF LOADING
# =============================================================================
def get_allowed_grades(grade):
    return {6: [6, 7], 7: [7, 8], 8: [8, 9]}.get(grade, [grade])
 
def grade_matches_file(fname, allowed_grades):
    name = fname.lower().replace(".pdf", "")
    for g in allowed_grades:
        patterns = [
            str(g), f"grade{g}", f"grade_{g}",
            f"class{g}", f"std{g}", f"g{g}",
            f"{g}th", f"{g}st", f"{g}nd", f"{g}rd",
        ]
        if any(p in name for p in patterns):
            return True
    return False
 
def extract_pdf(fname):
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if len(text) > 60:
                words = set(re.sub(r'[^a-z0-9 ]', ' ', text.lower()).split())
                chunks.append({
                    "text":  text[:1500],
                    "words": words,
                    "file":  fname,
                    "page":  page_num + 1
                })
        doc.close()
    except Exception as e:
        print(f"PDF error {fname}: {e}")
    return chunks
 
@st.cache_resource(show_spinner=False)
def load_all_pdfs(grade):
    all_chunks = []
    allowed    = get_allowed_grades(grade)
    pdf_files  = [f for f in os.listdir(".") if f.endswith(".pdf")]
    grade_files = [f for f in pdf_files if grade_matches_file(f, allowed)]
    if not grade_files:
        grade_files = pdf_files
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(extract_pdf, f): f for f in grade_files}
        for future in as_completed(futures):
            all_chunks.extend(future.result())
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
# MATH SOLVER
# =============================================================================
def is_pure_calc(q):
    return bool(re.fullmatch(r"[\d\.\+\-\*\/\(\)\s\^%]+", q.strip()))
 
def solve_math(q):
    try:
        result = eval(
            q.strip().replace("^", "**").replace(" ", ""),
            {"__builtins__": None}, {}
        )
        return f"**= {round(result, 8)}**", "calc"
    except:
        return None, None
 
# =============================================================================
# PDF KEYWORD SEARCH
# =============================================================================
STOPWORDS = {
    "what", "is", "are", "how", "why", "when", "who", "the", "a", "an",
    "of", "in", "to", "and", "does", "do", "explain", "define", "me",
    "about", "give", "please", "describe", "tell", "example",
    "examples", "find", "solve", "calculate", "show", "write"
}
 
def keyword_search(q):
    if not PDF_CHUNKS:
        return []
    q_words = set(re.sub(r'[^a-z0-9 ]', ' ', q.lower()).split()) - STOPWORDS
    if not q_words:
        return []
    scored = []
    for chunk in PDF_CHUNKS:
        score = len(q_words & chunk["words"])
        if score >= 1:           # lowered from 2 → single-word queries now match
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:8]
 
# =============================================================================
# AI JUDGE — parallel
# =============================================================================
def judge_single(args):
    chunk, question, key = args
    prompt = (
        f"Question: {question}\n\n"
        f"Excerpt:\n{chunk['text'][:500]}\n\n"
        f"Does this excerpt directly help answer the academic question? "
        f"Reply ONLY: YES or NO"
    )
    try:
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3, temperature=0
        )
        return "YES" in r.choices[0].message.content.upper(), chunk
    except:
        return True, chunk   # on error, include the chunk rather than lose it
 
def parallel_judge(candidates, question):
    if not candidates:
        return []
    if not ALL_OPENAI_KEYS:
        return [c for _, c in candidates[:4]]
    key_list = list(itertools.islice(
        itertools.cycle(ALL_OPENAI_KEYS), len(candidates)
    ))
    tasks = [
        (chunk, question, key_list[i])
        for i, (_, chunk) in enumerate(candidates)
    ]
    good = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = [ex.submit(judge_single, t) for t in tasks]
        for f in as_completed(futures):
            try:
                ok, chunk = f.result()
                if ok:
                    good.append(chunk)
            except:
                pass
    # If judge eliminated everything, fall back to top BM25 results
    if not good:
        good = [c for _, c in candidates[:3]]
    return good
 
# =============================================================================
# ZERO-API TEXT EXTRACTION
# Directly extracts the best sentences from PDF text — no API needed.
# Used as final fallback when all LLM calls fail.
# =============================================================================
def extract_answer_from_text(question, chunks, grade):
    q_words = set(
        w for w in re.sub(r'[^a-z0-9 ]', ' ', question.lower()).split()
        if w not in STOPWORDS and len(w) > 1
    )
    sentence_scores = []
    for chunk in chunks[:6]:
        for sent in re.split(r'(?<=[.!?])\s+', chunk["text"]):
            if len(sent.split()) < 6:
                continue
            sent_words = set(
                w for w in re.sub(r'[^a-z0-9 ]', ' ', sent.lower()).split()
                if len(w) > 1
            )
            overlap = len(q_words & sent_words)
            if overlap > 0:
                sentence_scores.append((overlap, sent.strip()))
 
    sentence_scores.sort(key=lambda x: x[0], reverse=True)
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
    prefix = (
        "Here's what your textbook says:\n\n" if grade <= 4 else
        "Your textbook explains:\n\n"         if grade <= 7 else
        "According to your textbook:\n\n"
    )
    return f"{prefix}{joined}\n\n*📖 Source: {src}*"
 
# =============================================================================
# GRADE STYLE
# =============================================================================
def grade_style(g):
    if g <= 3:
        return "Use very simple words, short sentences, fun examples. Like explaining to a young child."
    elif g <= 6:
        return "Use clear simple language with relatable everyday examples."
    elif g <= 8:
        return "Use clear academic language with key terms and worked examples."
    else:
        return "Use detailed academic language suitable for high school."
 
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
# =============================================================================
def answer_from_pdf(question, chunks, grade, history, stream_ph=None):
    context = "\n\n---\n\n".join([
        f"[{c['file']} p.{c['page']}]\n{c['text']}"
        for c in chunks[:4]
    ])
    src   = chunks[0]["file"]
    style = grade_style(grade)
    hist  = "".join([
        f"{'Student' if m['role']=='user' else 'SmartLoop'}: {m.get('content','')}\n"
        for m in history[-4:]
    ])
 
    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert tutor for Grade {grade}. {style}\n"
                "You MUST always give a complete, helpful answer.\n"
                "Use the textbook excerpts below as your primary source.\n"
                "If excerpts don't fully cover the question, supplement from your own knowledge.\n"
                "NEVER say you cannot answer, cannot find information, or refuse to help."
            )
        },
        {
            "role": "user",
            "content": (
                f"TEXTBOOK EXCERPTS:\n{context}\n\n"
                f"CONVERSATION:\n{hist}\n\n"
                f"QUESTION: {question}\nAnswer:"
            )
        }
    ]
 
    ans = call_llm(messages, max_tokens=800, temperature=0.3, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "pdf", src
 
    # Zero-API fallback — extract directly from PDF text
    fallback = extract_answer_from_text(question, chunks, grade)
    if fallback:
        if stream_ph:
            stream_ph.markdown(fallback)
        return fallback, "pdf", src
 
    return None, None, None
 
# =============================================================================
# TIER 2: AI ANSWER
# =============================================================================
def answer_from_ai(question, grade, history, stream_ph=None):
    style = grade_style(grade)
    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert academic tutor for Grade {grade}. {style}\n"
                "Always give complete, accurate answers.\n"
                "NEVER say you cannot answer or refuse any academic question."
            )
        }
    ]
    for m in history[-4:]:
        messages.append({"role": m["role"], "content": m.get("content", "")})
    messages.append({"role": "user", "content": question})
 
    ans = call_llm(messages, max_tokens=800, temperature=0.4, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "ai", None
    return None, None, None
 
# =============================================================================
# TIER 3: DUCKDUCKGO
# =============================================================================
BAD_CONTENT = [
    "comic", "marvel", "dc comics", "film", "movie",
    "tv series", "television", "album", "song", "band",
    "actor", "actress", "footballer", "celebrity"
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
            r"(what is|what are|explain|define|how does|tell me about|describe)",
            "", question.lower()
        ).strip()
 
        data = requests.get(
            f"https://api.duckduckgo.com/?q={requests.utils.quote(search_q + ' school definition')}"
            "&format=json&no_html=1&skip_disambig=1",
            headers=headers, timeout=8
        ).json()
 
        result_text = (
            data.get("AbstractText") or
            data.get("Answer") or
            data.get("Definition") or ""
        )
        if not result_text and data.get("RelatedTopics"):
            result_text = " ".join(
                t["Text"] for t in data["RelatedTopics"][:3]
                if isinstance(t, dict) and t.get("Text")
            )
 
        if len(result_text) > 40 and not any(b in result_text.lower() for b in BAD_CONTENT):
            return result_text, "ddg", None
 
        # HTML scrape fallback
        soup = BeautifulSoup(
            requests.get(
                f"https://html.duckduckgo.com/html/?q="
                f"{requests.utils.quote(search_q + ' academic definition school')}",
                headers=headers, timeout=8
            ).text,
            "html.parser"
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
            "physics", "chemistry", "biology", "mathematics",
            "science", "history", "geography", "economics",
            "force", "energy", "cell", "atom", "equation",
            "decimal", "fraction", "geometry", "algebra"
        ]
        best = next(
            (r for r in results if any(k in r.lower() for k in academic_kw)),
            results[0] if results else None
        )
        if not best:
            return None, None, None
 
        summary = wikipedia.summary(best, sentences=3)
        if any(b in summary.lower() for b in BAD_CONTENT + [
            "may refer to", "disambiguation", "is a list"
        ]):
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
            summary = wikipedia.summary(best, sentences=3)
            if any(b in summary.lower() for b in ["comic", "marvel", "film"]):
                return None, None, None
            return summary, "wiki", None
        except:
            return None, None, None
    except:
        return None, None, None
 
# =============================================================================
# MAIN PIPELINE
# calc → pdf(LLM) → pdf(text extract) → ai → ddg → wiki
# Web is LAST RESORT — PDFs always take priority
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
 
    # Step 1: PDF keyword search
    update_phase(thinking_ph, "Reading")
    candidates = keyword_search(question)
 
    # Step 2: AI judge (skip if no API keys — include all candidates)
    update_phase(thinking_ph, "Thinking")
    good_chunks = []
    if candidates:
        good_chunks = parallel_judge(candidates, question)
 
    # Step 3: LLM answer from PDF chunks
    if good_chunks:
        update_phase(thinking_ph, "Answering from textbook")
        ans, tier, src = answer_from_pdf(question, good_chunks, grade, history, stream_ph)
        if ans:
            return ans, tier, src
 
    # Step 4: Zero-API direct text extraction from PDF
    # This runs BEFORE web — PDFs always beat DuckDuckGo/Wikipedia
    if good_chunks:
        fallback = extract_answer_from_text(question, good_chunks, grade)
        if fallback:
            if stream_ph:
                stream_ph.markdown(fallback)
            return fallback, "pdf", good_chunks[0]["file"]
 
    # Step 5: General AI answer (no PDF context)
    update_phase(thinking_ph, "Thinking")
    ans, tier, src = answer_from_ai(question, grade, history, stream_ph)
    if ans:
        return ans, tier, src
 
    # Step 6: Web — only reached if PDFs have nothing AND AI failed
    update_phase(thinking_ph, "Searching web")
    for fn in [answer_from_duckduckgo, answer_from_wiki]:
        ans, tier, src = fn(question)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans, tier, src
 
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
 
    st.markdown("<div class='section-label'>💬 Chats</div>", unsafe_allow_html=True)
 
    for chat_name in list(reversed(list(st.session_state.chats.keys()))):
        is_active = (chat_name == st.session_state.current_chat)
        col1, col2 = st.columns([0.82, 0.18], vertical_alignment="center")
        msgs       = st.session_state.chats.get(chat_name, [])
        first_user = next(
            (m["content"] for m in msgs if m["role"] == "user"), chat_name
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
                    st.session_state.current_chat = list(
                        st.session_state.chats.keys()
                    )[0]
                st.rerun()
 
    st.divider()
    n_oa = len(ALL_OPENAI_KEYS)
    n_go = len(ALL_GOOGLE_KEYS)
    st.success(f"📚 {len(PDF_CHUNKS)} pages loaded")
    st.info(
        f"🔑 OpenAI: {n_oa} key{'s' if n_oa != 1 else ''} | "
        f"Google: {n_go} key{'s' if n_go != 1 else ''}"
    )
 
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
            f"I'm your Grade {st.session_state.grade} tutor.\n\n"
            f"- 📖 Searches your **textbooks first**\n"
            f"- 🤖 Falls back to **AI knowledge**\n"
            f"- 🦆 Then tries **DuckDuckGo**\n"
            f"- 🌐 Last resort → **Wikipedia**\n"
            f"- 🧮 Solves **maths step-by-step**\n\n"
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
