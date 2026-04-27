import streamlit as st
import re, math, os, itertools
import PyPDF2
from google import genai
from openai import OpenAI

# =========================
# 🔑 SAFE API SETUP
# =========================
GOOGLE_KEYS = [
    st.secrets.get("GOOGLE_API_KEY_1"),
    st.secrets.get("GOOGLE_API_KEY_2"),
    st.secrets.get("GOOGLE_API_KEY_3"),
    st.secrets.get("GOOGLE_API_KEY_4")
]

OPENAI_KEYS = [
    st.secrets.get("OPENAI_API_KEY_1"),
    st.secrets.get("OPENAI_API_KEY_2"),
    st.secrets.get("OPENAI_API_KEY_3")
]

GOOGLE_KEYS = [k for k in GOOGLE_KEYS if k]
OPENAI_KEYS = [k for k in OPENAI_KEYS if k]

google_cycle = itertools.cycle(GOOGLE_KEYS) if GOOGLE_KEYS else None
openai_cycle = itertools.cycle(OPENAI_KEYS) if OPENAI_KEYS else None

def get_google():
    if not google_cycle:
        return None
    try:
        return genai.Client(api_key=next(google_cycle))
    except:
        return None

def get_openai():
    if not openai_cycle:
        return None
    try:
        return OpenAI(api_key=next(openai_cycle))
    except:
        return None

# =========================
# 📄 LOAD ALL PDFs
# =========================
@st.cache_data
def load_books():
    text = ""

    for file in os.listdir():
        if file.endswith(".pdf"):
            try:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += (page.extract_text() or "") + "\n"
            except:
                continue

    return text.lower()

PDF_TEXT = load_books()

# =========================
# 🧠 CLEAN
# =========================
def clean(q):
    return q.lower().strip()

# =========================
# 🧮 MATH
# =========================
def solve_math(q):
    try:
        if re.fullmatch(r"[0-9+\-*/().\s^]+", q):
            q = q.replace("^", "**")
            result = eval(q, {"__builtins__": None}, {})
            return f"🧮 {q} = {result}"
    except:
        pass
    return None

# =========================
# 📖 SMART DEFINITION SEARCH
# =========================
def defining(q):
    if not PDF_TEXT:
        return None

    keywords = [w for w in q.split() if len(w) > 3]
    chunks = PDF_TEXT.split("\n")

    best = None
    best_score = 0

    for chunk in chunks:
        chunk = chunk.strip()

        if len(chunk) < 40:
            continue

        # skip exercises
        if any(x in chunk for x in [
            "match","fill","answer","exercise",
            "write","solve","complete"
        ]):
            continue

        if not any(k in chunk for k in keywords):
            continue

        score = 0

        # keyword match
        for k in keywords:
            if k in chunk:
                score += 3

        # strong definition patterns
        if chunk.startswith(("a decimal", "decimals are", "decimal numbers are")):
            score += 10

        if any(x in chunk for x in [" is ", " are ", " means ", " refers to "]):
            score += 5

        if score > best_score:
            best_score = score
            best = chunk

    if best:
        return "📖 Definition:\n" + best[:400]

    return None

# =========================
# 🔁 FALLBACK
# =========================
def fallback(q):
    if "decimal" in q:
        return ("📖 Definition:\n"
                "Decimals are numbers that contain a decimal point. "
                "They represent parts of a whole.\n\n"
                "Example:\n0.5 = half\n1.25 = one and twenty-five hundredths.")

    return None

# =========================
# 🤖 API BACKUP
# =========================
def api_answer(q):
    prompt = f"Explain clearly for a student:\n{q}"

    # Google
    for _ in range(2):
        c = get_google()
        if c:
            try:
                r = c.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if r.text:
                    return r.text
            except:
                continue

    # OpenAI
    for _ in range(2):
        c = get_openai()
        if c:
            try:
                r = c.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":prompt}]
                )
                return r.choices[0].message.content
            except:
                continue

    return None

# =========================
# 🤖 MAIN AI
# =========================
def ai(q):
    q = clean(q)

    # math
    math_res = solve_math(q)
    if math_res:
        return math_res

    # PDF
    pdf_res = defining(q)
    if pdf_res:
        return pdf_res

    # fallback knowledge
    fb = fallback(q)
    if fb:
        return fb

    # API
    api_res = api_answer(q)
    if api_res:
        return api_res

    return "⚠️ I couldn't find a good answer anywhere."

# =========================
# 🎨 UI
# =========================
st.title("🧠 SmartBot FINAL")

q = st.text_input("Ask anything...")

if q:
    st.write("🧑", q)

    with st.spinner("🧠 Thinking..."):
        answer = ai(q)

    st.write("🤖", answer)
