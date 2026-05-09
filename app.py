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

PDF_JUDGE_KEYS   = ALL_OPENAI_KEYS.copy()
PRIMARY_ANS_KEYS = [k for i,k in enumerate(ALL_OPENAI_KEYS) if i in [1,2]]
EXTRA_ANS_KEYS   = [k for i,k in enumerate(ALL_OPENAI_KEYS) if i == 3]

pdf_judge_cycle   = itertools.cycle(PDF_JUDGE_KEYS)   if PDF_JUDGE_KEYS   else None
primary_ans_cycle = itertools.cycle(PRIMARY_ANS_KEYS) if PRIMARY_ANS_KEYS else None
extra_ans_cycle   = itertools.cycle(EXTRA_ANS_KEYS)   if EXTRA_ANS_KEYS   else None
google_cycle      = itertools.cycle(ALL_GOOGLE_KEYS)  if ALL_GOOGLE_KEYS  else None

# Collect errors for debug panel
if "api_errors" not in st.session_state:
    st.session_state.api_errors = []

def log_error(source, error):
    msg = f"[{source}] {str(error)[:120]}"
    st.session_state.api_errors.append(msg)
    print(msg)

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
# PDF LOADING
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

def extract_pdf(fname):
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()
            if len(text) > 60:
                words = set(
                    re.sub(r'[^a-z0-9 ]',' ',text.lower()).split()
                )
                chunks.append({
                    "text":  text[:1500],
                    "words": words,
                    "file":  fname,
                    "page":  page_num + 1
                })
        doc.close()
    except Exception as e:
        log_error("PDF", e)
    return chunks

@st.cache_resource(show_spinner=False)
def load_all_pdfs(grade):
    all_chunks  = []
    allowed     = get_allowed_grades(grade)
    pdf_files   = [f for f in os.listdir(".") if f.endswith(".pdf")]
    grade_files = [
        f for f in pdf_files if grade_matches_file(f, allowed)
    ]
    if not grade_files:
        grade_files = pdf_files
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(extract_pdf, f): f for f in grade_files}
        for future in as_completed(futures):
            all_chunks.extend(future.result())
    return all_chunks

with st.spinner("📚 Loading library..."):
    PDF_CHUNKS = load_all_pdfs(st.session_state.grade)

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
        re.sub(r'[^a-z0-9 ]',' ',q.lower()).split()
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
# AI JUDGE — parallel
# =========================
def judge_single(args):
    chunk, question, key = args
    prompt = (
        f"Question: {question}\n\n"
        f"Excerpt:\n{chunk['text'][:500]}\n\n"
        f"Does this excerpt directly help answer "
        f"the academic question? Reply ONLY: YES or NO"
    )
    try:
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=3, temperature=0
        )
        return "YES" in r.choices[0].message.content.upper(), chunk
    except Exception as e:
        log_error("Judge", e)
        # If judging fails, include the chunk anyway
        # so we don't lose good content
        return True, chunk

def parallel_judge(candidates, question):
    if not candidates:
        return [c for _, c in candidates[:4]]
    if not PDF_JUDGE_KEYS:
        return [c for _, c in candidates[:4]]
    key_list = list(itertools.islice(
        itertools.cycle(PDF_JUDGE_KEYS), len(candidates)
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
    # If nothing passed judging, return top candidates anyway
    if not good:
        good = [c for _, c in candidates[:3]]
    return good

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
# TIER 1: PDF ANSWER
# =========================
def answer_from_pdf(question, chunks, grade, history):
    context = "\n\n---\n\n".join([
        f"[{c['file']} p.{c['page']}]\n{c['text']}"
        for c in chunks[:4]
    ])
    src   = chunks[0]["file"]
    style = grade_style(grade)
    hist  = "".join([
        f"{'Student' if m['role']=='user' else 'SmartLoop'}: "
        f"{m.get('content','')}\n"
        for m in history[-4:]
    ])
    prompt = f"""You are SmartLoop AI, expert tutor for Grade {grade}.
{style}
Use the textbook excerpts to answer accurately.
If excerpts don't fully cover it, supplement with your knowledge.

TEXTBOOK:
{context}

CONVERSATION:
{hist}

QUESTION: {question}
Answer:"""

    for _ in range(max(1, len(PRIMARY_ANS_KEYS))):
        try:
            c = get_primary()
            if c:
                r = c.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role":"user","content":prompt}],
                    max_tokens=800
                )
                ans = r.choices[0].message.content.strip()
                if ans and len(ans) > 20:
                    return ans, "pdf", src
        except Exception as e:
            log_error("PDF-Primary", e)
            time.sleep(1)

    try:
        c = get_extra()
        if c:
            r = c.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=800
            )
            ans = r.choices[0].message.content.strip()
            if ans and len(ans) > 20:
                return ans, "pdf", src
    except Exception as e:
        log_error("PDF-Extra", e)

    return None, None, None

# =========================
# TIER 2: AI ANSWER
# =========================
def answer_from_ai(question, grade, history):
    style = grade_style(grade)
    hist  = "".join([
        f"{'Student' if m['role']=='user' else 'SmartLoop'}: "
        f"{m.get('content','')}\n"
        for m in history[-4:]
    ])
    prompt = f"""You are SmartLoop AI, expert academic tutor for Grade {grade}.
{style}
Answer completely and accurately. Never refuse.

CONVERSATION:
{hist}

QUESTION: {question}
Answer:"""

    # Google Gemini first
    for _ in range(min(2, max(1, len(ALL_GOOGLE_KEYS)))):
        try:
            c = get_google()
            if c:
                r = c.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                if r.text and len(r.text.strip()) > 20:
                    return r.text.strip(), "ai", None
        except Exception as e:
            log_error("Gemini", e)
            time.sleep(1)

    # Primary OpenAI
    for _ in range(max(1, len(PRIMARY_ANS_KEYS))):
        try:
            c = get_primary()
            if c:
                msgs = [{
                    "role": "system",
                    "content": (
                        f"You are SmartLoop AI, expert academic tutor "
                        f"for Grade {grade}. {style} "
                        f"Always give complete accurate answers."
                    )
                }]
                for m in history[-4:]:
                    msgs.append({
                        "role": m["role"],
                        "content": m.get("content","")
                    })
                msgs.append({"role":"user","content":question})
                r = c.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=msgs,
                    max_tokens=800
                )
                ans = r.choices[0].message.content.strip()
                if ans and len(ans) > 20:
                    return ans, "ai", None
        except Exception as e:
            log_error("OpenAI-Primary", e)
            time.sleep(1)

    # Extra OpenAI key
    try:
        c = get_extra()
        if c:
            r = c.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                max_tokens=800
            )
            ans = r.choices[0].message.content.strip()
            if ans and len(ans) > 20:
                return ans, "ai", None
    except Exception as e:
        log_error("OpenAI-Extra", e)

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

        # HTML scrape fallback
        search_url = (
            f"https://html.duckduckgo.com/html/?q="
            f"{requests.utils.quote(search_q + ' academic definition school')}"
        )
        resp2    = requests.get(search_url, headers=headers, timeout=8)
        soup     = BeautifulSoup(resp2.text, "html.parser")
        snippets = []
        for result in soup.select(".result__snippet")[:5]:
            text = result.get_text(strip=True)
            if len(text) > 40 and not any(
                b in text.lower() for b in BAD_CONTENT
            ):
                snippets.append(text)
        if snippets:
            combined = " ".join(snippets[:2])
            if len(combined) > 50:
                return combined, "ddg", None

    except Exception as e:
        log_error("DuckDuckGo", e)

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
            "force","energy","cell","atom","equation
