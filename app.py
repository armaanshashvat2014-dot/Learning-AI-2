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

st.set_page_config(page_title="SmartLoop AI", page_icon="🧠", layout="wide")

st.markdown("""
<style>
.stApp {
    background: radial-gradient(800px circle at 50% 0%,
        rgba(0,212,255,0.10), rgba(0,212,255,0.00) 60%), #0a0a1a !important;
    color: #f5f5f7 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
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
[data-testid="stChatMessage"] pre, [data-testid="stChatMessage"] code {
    white-space: pre-wrap !important; word-break: break-word !important;
}
.stChatInputContainer {
    background: rgba(20,20,35,0.85) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 20px !important;
}
.stTextInput>div>div>input, .stTextArea>div>textarea, .stSelectbox>div>div>div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important; color: #fff !important;
}
.stButton>button {
    background: linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.02) 100%) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 18px !important; backdrop-filter: blur(20px) !important;
    color: #fff !important; font-weight: 600 !important; transition: all 0.25s !important;
}
@media (hover: hover) and (pointer: fine) {
    .stButton>button:hover {
        background: linear-gradient(180deg, rgba(255,255,255,0.20) 0%, rgba(255,255,255,0.05) 100%) !important;
        border-color: rgba(255,255,255,0.35) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
    }
}
.stButton>button:active { transform: translateY(1px) !important; }
.thinking-container {
    display: flex; align-items: center; gap: 8px; padding: 12px 16px;
    background: rgba(255,255,255,0.04); border-radius: 14px; margin: 8px 0;
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
    text-transform: uppercase; letter-spacing: 1px; margin: 12px 0 6px;
}
.welcome-card {
    background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(123,47,247,0.08));
    border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
    padding: 12px 16px; margin-bottom: 8px; font-weight: 600;
    color: #2ecc71; font-size: 14px;
}
.source-badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; margin-top: 6px;
}
.src-pdf  { background:rgba(0,212,255,0.15); color:#00d4ff; border:1px solid rgba(0,212,255,0.3); }
.src-ai   { background:rgba(252,132,4,0.15); color:#fc8404; border:1px solid rgba(252,132,4,0.3); }
.src-ddg  { background:rgba(255,69,0,0.15);  color:#ff6b35; border:1px solid rgba(255,69,0,0.3); }
.src-wiki { background:rgba(52,152,219,0.15); color:#3498db; border:1px solid rgba(52,152,219,0.3); }
.src-calc { background:rgba(155,89,182,0.2);  color:#9b59b6; border:1px solid rgba(155,89,182,0.4); }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# API KEYS
# =============================================================================
def _collect_keys(prefix):
    keys = []
    for i in range(1, 6):
        k = st.secrets.get(f"{prefix}_{i}")
        if k:
            keys.append(k)
    return keys

ALL_OPENAI_KEYS = _collect_keys("OPENAI_API_KEY")
ALL_GOOGLE_KEYS = _collect_keys("GOOGLE_API_KEY")
MY_API_KEY      = st.secrets.get("MY_API_KEY")

if not ALL_OPENAI_KEYS and not ALL_GOOGLE_KEYS and not MY_API_KEY:
    st.error("No API keys found.")
    st.stop()

_openai_cycle = itertools.cycle(ALL_OPENAI_KEYS) if ALL_OPENAI_KEYS else None
_google_cycle = itertools.cycle(ALL_GOOGLE_KEYS) if ALL_GOOGLE_KEYS else None

# =============================================================================
# REFUSAL DETECTOR
# =============================================================================
REFUSAL_PHRASES = [
    "i cannot","i can't","i am unable","i'm unable",
    "i don't have","i do not have","not able to",
    "cannot provide","unable to provide","cannot answer",
    "no information","not found in","not covered",
    "beyond my","outside my","i'm sorry, but",
    "i am sorry","as an ai","as a language model",
    "i lack","i cannot find",
]

def is_refusal(text):
    low = text.lower()
    return any(p in low for p in REFUSAL_PHRASES)

# =============================================================================
# LOVABLE API
# =============================================================================
def call_my_api(messages):
    if not MY_API_KEY:
        return None
    try:
        headers  = {
            "Authorization": f"Bearer {MY_API_KEY}",
            "Content-Type":  "application/json"
        }
        response = requests.post(
            "https://raujzsawwpmixwlcgcgs.supabase.co/functions/v1/public-ai-api",
            headers=headers, json={"messages": messages}, timeout=45
        )
        data = response.json()
        text = ""
        if isinstance(data, dict):
            text = (
                data.get("response") or data.get("content") or
                data.get("message") or data.get("reply") or ""
            )
            if not text and "choices" in data:
                text = data["choices"][0]["message"]["content"]
        elif isinstance(data, str):
            text = data
        text = str(text).strip()
        if len(text) > 10 and not is_refusal(text):
            return text
    except Exception as e:
        print(f"My API error: {e}")
    return None

# =============================================================================
# MAIN LLM CALLER
# =============================================================================
def call_llm(messages, max_tokens=900, temperature=0.3, stream_ph=None):

    if _google_cycle:
        for _ in range(len(ALL_GOOGLE_KEYS)):
            try:
                client = genai.Client(api_key=next(_google_cycle))
                prompt = "\n\n".join(
                    f"[{m['role'].upper()}]: {m['content']}" for m in messages
                )
                r   = client.models.generate_content(
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

    if _openai_cycle:
        for _ in range(len(ALL_OPENAI_KEYS)):
            try:
                client = OpenAI(api_key=next(_openai_cycle))
                if stream_ph:
                    stream  = client.chat.completions.create(
                        model="gpt-3.5-turbo", messages=messages,
                        max_tokens=max_tokens, temperature=temperature, stream=True,
                    )
                    ans = ""
                    for chunk in stream:
                        piece = chunk.choices[0].delta.content or ""
                        ans  += piece
                        stream_ph.markdown(ans + "▌")
                    stream_ph.markdown(ans)
                    if len(ans) > 15 and not is_refusal(ans):
                        return ans
                    stream_ph.empty()
                else:
                    r   = client.chat.completions.create(
                        model="gpt-3.5-turbo", messages=messages,
                        max_tokens=max_tokens, temperature=temperature,
                    )
                    ans = r.choices[0].message.content.strip()
                    if len(ans) > 15 and not is_refusal(ans):
                        return ans
            except Exception as e:
                print(f"OpenAI error: {e}")
                time.sleep(0.3)

    try:
        ans = call_my_api(messages)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans
    except Exception as e:
        print(f"My API failed: {e}")

    fallback_msgs = [
        {"role":"system","content":"You are a helpful tutor. Always answer completely."}
    ] + [m for m in messages if m["role"] != "system"]

    if _openai_cycle:
        for _ in range(len(ALL_OPENAI_KEYS)):
            try:
                client = OpenAI(api_key=next(_openai_cycle))
                r   = client.chat.completions.create(
                    model="gpt-3.5-turbo", messages=fallback_msgs,
                    max_tokens=max_tokens, temperature=0.5,
                )
                ans = r.choices[0].message.content.strip()
                if len(ans) > 15:
                    if stream_ph:
                        stream_ph.markdown(ans)
                    return ans
            except Exception as e:
                print(f"Fallback error: {e}")
                time.sleep(0.3)
    return None

def call_llm_short(prompt, max_tokens=60):
    return call_llm(
        [{"role":"user","content":prompt}],
        max_tokens=max_tokens, temperature=0
    )

# =============================================================================
# GRADE SELECTION
# =============================================================================
if "grade" not in st.session_state:
    st.session_state.grade = None

if st.session_state.grade is None:
    st.markdown("""
<div style='max-width:400px;margin:100px auto;background:rgba(255,255,255,0.05);
border:1px solid rgba(255,255,255,0.15);border-radius:28px;padding:40px;
text-align:center;backdrop-filter:blur(40px);'>
<div style='font-size:40px;margin-bottom:12px;'>🧠</div>
<div style='font-size:28px;font-weight:800;color:#00d4ff;margin-bottom:6px;'>SmartLoop AI</div>
<div style='color:rgba(255,255,255,0.5);margin-bottom:28px;font-size:15px;'>
Select your grade to get started</div></div>
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
# PDF LOADING
# Grade X loads grade X and X+1 books
# =============================================================================
def get_allowed_grades(grade):
    return [grade, grade + 1] if grade < 10 else [grade]

def grade_matches_file(fname, allowed_grades):
    name = fname.lower().replace(".pdf", "")
    for g in allowed_grades:
        if any(p in name for p in [
            str(g), f"grade{g}", f"grade_{g}", f"class{g}",
            f"std{g}", f"g{g}", f"{g}th", f"{g}st", f"{g}nd", f"{g}rd"
        ]):
            return True
    return False

def extract_pdf(fname):
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            try:
                blocks = page.get_text("dict")["blocks"]
                lines  = []
                for block in blocks:
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            words    = []
                            prev_x1  = None
                            for span in line.get("spans", []):
                                span_text = span.get("text","").strip()
                                if not span_text:
                                    continue
                                if prev_x1 is not None:
                                    gap = span["origin"][0] - prev_x1
                                    if gap > 2:
                                        words.append(" ")
                                words.append(span_text)
                                prev_x1 = span["bbox"][2]
                            line_text = "".join(words).strip()
                            if line_text:
                                lines.append(line_text)
                text = "\n".join(lines).strip()
            except Exception:
                text = page.get_text().strip()

            if len(text) > 60:
                text  = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
                text  = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)
                words = set(re.sub(r'[^a-z0-9 ]',' ',text.lower()).split())
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
    allowed     = get_allowed_grades(grade)
    pdf_files   = [f for f in os.listdir(".") if f.endswith(".pdf")]
    grade_files = [f for f in pdf_files if grade_matches_file(f, allowed)]
    if not grade_files:
        grade_files = pdf_files
    all_chunks = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(extract_pdf, f): f for f in grade_files}
        for future in as_completed(futures):
            all_chunks.extend(future.result())
    return all_chunks

# Load PDFs while showing AI knowledge message
load_col = st.columns([1, 2, 1])[1]
with st.spinner(""):
    thinking_load = st.empty()
    thinking_load.markdown("""
<div class="thinking-container" style="max-width:500px;margin:0 auto;">
    <span class="thinking-text">📚 Loading your textbooks using AI knowledge</span>
    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)
    PDF_CHUNKS = load_all_pdfs(st.session_state.grade)
    thinking_load.empty()

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
            q.strip().replace("^","**").replace(" ",""),
            {"__builtins__": None}, {}
        )
        return f"**= {round(result, 8)}**", "calc"
    except:
        return None, None

# =============================================================================
# STOPWORDS + KEYWORD SEARCH
# =============================================================================
STOPWORDS = {
    "what","is","are","how","why","when","who","the","a","an",
    "of","in","to","and","does","do","explain","define","me",
    "about","give","please","describe","tell","example","examples",
    "find","solve","calculate","show","write","give","some","for",
    "questions","question","on","from","chapter","topic","subject",
    "create","make","generate","write","list","provide"
}

def keyword_search(q):
    if not PDF_CHUNKS:
        return []
    q_words = set(re.sub(r'[^a-z0-9 ]',' ',q.lower()).split()) - STOPWORDS
    if not q_words:
        return []
    scored = []
    for chunk in PDF_CHUNKS:
        score = len(q_words & chunk["words"])
        if score >= 1:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:8]

# =============================================================================
# QUESTION REQUEST DETECTOR
# =============================================================================
QUESTION_REQUEST_WORDS = [
    "give me questions","give questions","make questions",
    "create questions","generate questions","write questions",
    "some questions","practice questions","exam questions",
    "test questions","quiz","questions on","questions about",
    "questions from","give me some","create a test",
    "make a test","make a quiz","create a quiz",
]

def is_question_request(q):
    ql = q.lower()
    return any(phrase in ql for phrase in QUESTION_REQUEST_WORDS)

# =============================================================================
# AI JUDGE
# =============================================================================
def judge_single(args):
    chunk, question, key = args
    prompt = (
        f"Question: {question}\n\nExcerpt:\n{chunk['text'][:500]}\n\n"
        f"Does this excerpt contain teaching content (definitions, explanations) "
        f"relevant to the question? Reply ONLY: YES or NO"
    )
    try:
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=3, temperature=0
        )
        return "YES" in r.choices[0].message.content.upper(), chunk
    except:
        return True, chunk

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
    return good if good else [c for _, c in candidates[:3]]

# =============================================================================
# ZERO-API TEXT EXTRACTION
# =============================================================================
def extract_answer_from_text(question, chunks, grade):
    q_words = set(
        w for w in re.sub(r'[^a-z0-9 ]',' ',question.lower()).split()
        if w not in STOPWORDS and len(w) > 1
    )
    sentence_scores = []
    for chunk in chunks[:6]:
        for sent in re.split(r'(?<=[.!?])\s+', chunk["text"]):
            if len(sent.split()) < 6:
                continue
            sent_words = set(re.sub(r'[^a-z0-9 ]',' ',sent.lower()).split())
            overlap    = len(q_words & sent_words)
            if overlap > 0:
                sentence_scores.append((overlap, sent.strip()))
    sentence_scores.sort(key=lambda x: x[0], reverse=True)
    seen, top = set(), []
    for _, sent in sentence_scores:
        key = sent[:40]
        if key not in seen:
            seen.add(key)
            top.append(sent)
        if len(top) >= 6:
            break
    if not top and chunks:
        top = [chunks[0]["text"][:600]]
    if not top:
        return None
    src    = chunks[0]["file"]
    joined = " ".join(top)
    prefix = (
        "Here's what your textbook says:\n\n" if grade <= 4 else
        "Your textbook explains:\n\n"          if grade <= 7 else
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
</div>""", unsafe_allow_html=True)

# =============================================================================
# UNDERSTAND INTENT
# =============================================================================
def understand_intent(question, history):
    hist = "".join([
        f"{'Student' if m['role']=='user' else 'AI'}: {m.get('content','')[:150]}\n"
        for m in history[-4:]
    ])
    prompt = (
        f"A student asked: \"{question}\"\n"
        f"Recent conversation:\n{hist}\n\n"
        "In ONE short sentence, what does the student want to learn? "
        "Be specific. Example: 'Understand what decimals are and how they work.'\nIntent:"
    )
    result = call_llm_short(prompt, max_tokens=40)
    return result.strip() if result else question

# =============================================================================
# SAFETY — detect bad intent
# =============================================================================
BAD_INTENT_KEYWORDS = [
    "hack","weapon","bomb","kill","drug","poison","suicide",
    "self harm","self-harm","violence","explicit","adult content",
    "sexual","illegal","steal","cheat","plagiarize","explosives",
    "hurt","attack","abuse","racism","racist","terrorism",
    "extremist","murder","assault","trafficking","pornograph",
]

def is_bad_intent(question, intent):
    combined = (question + " " + (intent or "")).lower()
    # Fast keyword check first
    if any(b in combined for b in BAD_INTENT_KEYWORDS):
        return True
    # AI judge for edge cases
    prompt = (
        f"A student asked: \"{question}\"\n"
        f"Detected intent: {intent}\n\n"
        "Is this question harmful, dangerous, inappropriate, "
        "or completely unrelated to education?\n"
        "Answer ONLY: YES or NO"
    )
    result = call_llm_short(prompt, max_tokens=3)
    return bool(result and "YES" in result.upper())

def bad_intent_response(grade):
    if grade <= 4:
        return "I can only help with school subjects! Ask me about maths, science, or anything from your textbooks. 😊"
    elif grade <= 7:
        return "I'm an educational tutor and can only help with school topics. Please ask me about your subjects!"
    else:
        return "I can only assist with academic and educational content. Please keep questions related to your studies."

# =============================================================================
# CONTEXT RELEVANCE CHECK
# =============================================================================
def context_is_relevant(intent, chunks):
    if not chunks:
        return False
    if not ALL_OPENAI_KEYS and not ALL_GOOGLE_KEYS:
        intent_words = set(
            w for w in re.sub(r'[^a-z0-9 ]',' ',intent.lower()).split()
            if w not in STOPWORDS and len(w) > 2
        )
        combined = " ".join(c["text"][:300] for c in chunks[:3]).lower()
        return sum(1 for w in intent_words if w in combined) >= 2
    sample = "\n---\n".join(c["text"][:400] for c in chunks[:3])
    prompt = (
        f"Student intent: {intent}\n\n"
        f"Textbook excerpts:\n{sample}\n\n"
        "Do these excerpts contain actual teaching content — definitions, "
        "explanations, or worked examples — that directly teaches this topic?\n"
        "Answer ONLY: YES or NO"
    )
    result = call_llm_short(prompt, max_tokens=3)
    return bool(result and "YES" in result.upper())

# =============================================================================
# GENERATE QUESTIONS
# =============================================================================
def generate_questions(question, chunks, grade, history, stream_ph=None):
    style      = grade_style(grade)
    topic_prompt = (
        f"The student asked: \"{question}\"\n"
        "What subject and topic/chapter are they asking questions about? "
        "Reply in format: Subject: X | Topic: Y\n"
        "If unclear, make a reasonable guess."
    )
    topic_info = call_llm_short(topic_prompt, max_tokens=30) or "General"

    if chunks:
        context = "\n\n---\n\n".join(c["text"] for c in chunks[:4])
        context_instruction = (
            f"Use the following textbook content as the basis for your questions:\n\n"
            f"{context}\n\nGenerate questions that test understanding of this content."
        )
        src = chunks[0]["file"]
    else:
        context_instruction = (
            f"No specific textbook content is available. "
            f"Generate realistic, curriculum-appropriate questions based on your knowledge of: {topic_info}"
        )
        src = None

    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert tutor for Grade {grade}. {style}\n\n"
                "Generate practice questions when asked.\n"
                "RULES:\n"
                "- Generate exactly what the student asked for\n"
                "- Include a mix of question types: short answer, fill in the blank, MCQ\n"
                "- Number each question clearly\n"
                "- Add answers at the end under '## Answers'\n"
                f"- Make questions appropriate for Grade {grade}\n"
                "- NEVER refuse"
            )
        },
        {
            "role": "user",
            "content": (
                f"Topic info: {topic_info}\n\n"
                f"{context_instruction}\n\n"
                f"Student request: {question}\n\nGenerate the questions now:"
            )
        }
    ]
    ans = call_llm(messages, max_tokens=1000, temperature=0.5, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "pdf" if src else "ai", src
    return None, None, None

# =============================================================================
# TIER 1 — PDF ANSWER
# =============================================================================
def answer_from_pdf(question, intent, chunks, grade, history, stream_ph=None):
    src     = chunks[0]["file"]
    style   = grade_style(grade)
    hist    = "".join([
        f"{'Student' if m['role']=='user' else 'SmartLoop'}: {m.get('content','')}\n"
        for m in history[-4:]
    ])
    context = "\n\n---\n\n".join(c["text"] for c in chunks[:4])
    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert tutor for Grade {grade}. {style}\n\n"
                f"The student wants to: {intent}\n\n"
                "RULES:\n"
                "- Use the textbook content as your knowledge source.\n"
                "- Write a clear, friendly EXPLANATION in your own words.\n"
                "- Structure: definition → real-world example → how it works.\n"
                "- Do NOT copy raw text, exercise lists, page numbers, or file names.\n"
                "- Do NOT output answer keys or table of contents.\n"
                "- NEVER refuse or say you cannot answer."
            )
        },
        {
            "role": "user",
            "content": (
                f"TEXTBOOK CONTENT:\n{context}\n\n"
                f"CONVERSATION:\n{hist}\n\n"
                f"QUESTION: {question}\nAnswer:"
            )
        }
    ]
    ans = call_llm(messages, max_tokens=800, temperature=0.3, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "pdf", src
    fallback = extract_answer_from_text(question, chunks, grade)
    if fallback:
        if stream_ph:
            stream_ph.markdown(fallback)
        return fallback, "pdf", src
    return None, None, None

# =============================================================================
# TIER 2 — AI ANSWER
# =============================================================================
def answer_from_ai(question, intent, grade, history, stream_ph=None):
    style    = grade_style(grade)
    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert academic tutor for Grade {grade}. {style}\n\n"
                f"The student wants to: {intent}\n\n"
                "Give a clear, complete, friendly explanation.\n"
                "Structure: definition → real-world example → how it works.\n"
                "NEVER refuse or say you cannot answer."
            )
        }
    ]
    for m in history[-4:]:
        messages.append({"role": m["role"], "content": m.get("content","")})
    messages.append({"role":"user","content":question})
    ans = call_llm(messages, max_tokens=800, temperature=0.4, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "ai", None
    return None, None, None

# =============================================================================
# TIER 3 — DUCKDUCKGO
# =============================================================================
BAD_CONTENT = [
    "comic","marvel","dc comics","film","movie","tv series",
    "television","album","song","band","actor","actress",
    "footballer","celebrity"
]

def answer_from_duckduckgo(question):
    try:
        headers  = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
        search_q = re.sub(
            r"(what is|what are|explain|define|how does|tell me about|describe)",
            "", question.lower()
        ).strip()
        data = requests.get(
            f"https://api.duckduckgo.com/?q={requests.utils.quote(search_q + ' school definition')}&format=json&no_html=1&skip_disambig=1",
            headers=headers, timeout=8
        ).json()
        result_text = data.get("AbstractText") or data.get("Answer") or data.get("Definition") or ""
        if not result_text and data.get("RelatedTopics"):
            result_text = " ".join(
                t["Text"] for t in data["RelatedTopics"][:3]
                if isinstance(t, dict) and t.get("Text")
            )
        if len(result_text) > 40 and not any(b in result_text.lower() for b in BAD_CONTENT):
            return result_text, "ddg", None
        soup     = BeautifulSoup(
            requests.get(
                f"https://html.duckduckgo.com/html/?q={requests.utils.quote(search_q + ' academic definition school')}",
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
# TIER 4 — WIKIPEDIA
# =============================================================================
def answer_from_wiki(question):
    try:
        search_q = re.sub(
            r"(what is|what are|explain|define|how does|tell me about|describe)",
            "", question.lower()
        ).strip()
        results = wikipedia.search(search_q + " mathematics science", results=5)
        academic_kw = [
            "physics","chemistry","biology","mathematics","science",
            "history","geography","economics","force","energy","cell",
            "atom","equation","decimal","fraction","geometry","algebra"
        ]
        best = next(
            (r for r in results if any(k in r.lower() for k in academic_kw)),
            results[0] if results else None
        )
        if not best:
            return None, None, None
        summary = wikipedia.summary(best, sentences=3)
        if any(b in summary.lower() for b in BAD_CONTENT + [
            "may refer to","disambiguation","is a list"
        ]):
            return None, None, None
        return summary, "wiki", None
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            bad  = ["film","comic","song","album","band","tv"]
            best = next(
                (o for o in e.options if not any(b in o.lower() for b in bad)),
                e.options[0] if e.options else None
            )
            if not best:
                return None, None, None
            summary = wikipedia.summary(best, sentences=3)
            if any(b in summary.lower() for b in ["comic","marvel","film"]):
                return None, None, None
            return summary, "wiki", None
        except:
            return None, None, None
    except:
        return None, None, None

# =============================================================================
# MAIN PIPELINE
# =============================================================================
def smartloop(question, grade, history, thinking_ph, stream_ph=None):

    # Math shortcut
    if is_pure_calc(question):
        update_phase(thinking_ph, "Calculating")
        ans, tier = solve_math(question)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans, tier, None

    # Step 1: Understand intent
    update_phase(thinking_ph, "Understanding question")
    intent = understand_intent(question, history)

    # Step 2: Safety check
    update_phase(thinking_ph, "Checking safety")
    if is_bad_intent(question, intent):
        msg = bad_intent_response(grade)
        if stream_ph:
            stream_ph.markdown(msg)
        return msg, "", None

    # Step 3: Question generation request
    if is_question_request(question):
        update_phase(thinking_ph, "Finding relevant content")
        candidates  = keyword_search(question)
        good_chunks = parallel_judge(candidates, question) if candidates else []
        update_phase(thinking_ph, "Generating questions")
        ans, tier, src = generate_questions(
            question, good_chunks, grade, history, stream_ph
        )
        if ans:
            return ans, tier, src

    # Step 4: Search PDFs
    update_phase(thinking_ph, "Searching textbooks")
    candidates  = keyword_search(question)
    good_chunks = parallel_judge(candidates, question) if candidates else []

    # Step 5: Relevance check
    update_phase(thinking_ph, "Checking relevance")
    pdf_relevant = context_is_relevant(intent, good_chunks)

    update_phase(thinking_ph, "Answering")

    if pdf_relevant and good_chunks:
        ans, tier, src = answer_from_pdf(
            question, intent, good_chunks, grade, history, stream_ph
        )
        if ans:
            return ans, tier, src

    # AI knowledge
    ans, tier, src = answer_from_ai(question, intent, grade, history, stream_ph)
    if ans:
        return ans, tier, src

    # Web fallback
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
# BADGE
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
    allowed = get_allowed_grades(st.session_state.grade)
    st.markdown(
        f"<div class='welcome-card'>"
        f"👋 Welcome! Grade {st.session_state.grade}"
        f"<br><span style='font-size:11px;opacity:0.8;'>"
        f"📚 Using Grade {allowed[0]}"
        f"{' & ' + str(allowed[1]) if len(allowed) > 1 else ''} books"
        f"</span></div>",
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
        is_active  = (chat_name == st.session_state.current_chat)
        col1, col2 = st.columns([0.82, 0.18], vertical_alignment="center")
        msgs       = st.session_state.chats.get(chat_name, [])
        first_user = next(
            (m["content"] for m in msgs if m["role"] == "user"), chat_name
        )
        title = first_user[:22] + "..." if len(first_user) > 22 else first_user
        if col1.button(
            f"{'🟢' if is_active else '💬'} {title}",
            key=f"ch_{chat_name}", use_container_width=True
        ):
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
    st.success(f"📚 {len(PDF_CHUNKS)} pages loaded")
    st.info(
        f"🔑 OpenAI: {len(ALL_OPENAI_KEYS)} | "
        f"Google: {len(ALL_GOOGLE_KEYS)}"
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
            if code == st.secrets.get("TEACHER_CODE",""):
                st.success("✅ Teacher access granted!")
            else:
                st.error("Invalid code.")

# =============================================================================
# MAIN CHAT UI
# =============================================================================
st.markdown(f"""
<div style='text-align:center;padding:20px 0 8px;'>
    <span style='font-size:44px;font-weight:800;color:#00d4ff;
        letter-spacing:-2px;text-shadow:0 0 16px rgba(0,212,255,0.45);'>
        🧠 SmartLoop AI
    </span>
    <span class='beta-badge'>BETA</span>
</div>
<div style='text-align:center;color:rgba(255,255,255,0.4);font-size:15px;margin-bottom:24px;'>
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
            f"- ❓ Can **generate practice questions** on any topic\n"
            f"- 🦆 Web only as **last resort**\n"
            f"- 🧮 Solves **maths step-by-step**\n\n"
            f"*What would you like to learn today?*"
        )

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content",""))
        show_badge(msg.get("tier",""), msg.get("source",""))

# =============================================================================
# CHAT INPUT
# =============================================================================
q = st.chat_input("Ask SmartLoop...")

if q:
    messages = st.session_state.chats[st.session_state.current_chat]
    messages.append({"role":"user","content":q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        thinking_ph = st.empty()
        stream_ph   = st.empty()
        ans, tier, source = smartloop(
            q, st.session_state.grade, messages[:-1],
            thinking_ph, stream_ph
        )
        thinking_ph.empty()
        if not ans:
            ans = "Sorry, something went wrong. Please try again."
        stream_ph.markdown(ans)
        show_badge(tier, source)
    messages.append({
        "role":"assistant","content":ans,"tier":tier,"source":source
    })
