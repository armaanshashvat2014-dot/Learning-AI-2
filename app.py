import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import re
import time
import pickle
import hashlib
import json
import uuid
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER

st.set_page_config(page_title="SmartLoop AI", page_icon="🧠", layout="wide")

st.markdown("""
<style>
.stApp {
    background: radial-gradient(800px circle at 50% 0%, rgba(0,212,255,0.10), rgba(0,212,255,0.00) 60%), #0a0a1a !important;
    color: #f5f5f7 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}
[data-testid="stSidebar"] {
    background: rgba(25,25,35,0.4) !important;
    backdrop-filter: blur(40px) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stForm"],
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.04) !important;
    backdrop-filter: blur(40px) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 24px !important;
    padding: 20px !important;
    margin: 12px 0 !important;
}
.stTextInput>div>div>input,
.stTextArea>div>textarea,
.stSelectbox>div>div>div,
.stNumberInput>div>div>input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 12px !important;
    color: #fff !important;
}
.stButton>button {
    background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.02) 100%) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 20px !important;
    color: #fff !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
@media (hover: hover) and (pointer: fine) {
    .stButton>button:hover {
        background: linear-gradient(180deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.05) 100%) !important;
        transform: translateY(-1px) !important;
    }
}
.big-title {
    color: #00d4ff;
    text-align: center;
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -2px;
    text-shadow: 0 0 12px rgba(0,212,255,0.4);
}
.sub-title {
    text-align: center;
    color: rgba(255,255,255,0.5);
    font-size: 15px;
    margin-bottom: 24px;
}
.tier-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-top: 6px;
}
.tier-calc { background: rgba(155,89,182,0.2); color: #9b59b6; border: 1px solid rgba(155,89,182,0.4); }
.tier-pdf  { background: rgba(0,212,255,0.15); color: #00d4ff; border: 1px solid rgba(0,212,255,0.3); }
.tier-kb   { background: rgba(46,204,113,0.15); color: #2ecc71; border: 1px solid rgba(46,204,113,0.3); }
.tier-wiki { background: rgba(52,152,219,0.15); color: #3498db; border: 1px solid rgba(52,152,219,0.3); }
.tier-ai   { background: rgba(252,132,4,0.15); color: #fc8404; border: 1px solid rgba(252,132,4,0.3); }
.chat-title {
    font-size: 13px;
    font-weight: 700;
    color: #00d4ff;
    padding: 4px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
}
.quiz-question-text {
    font-size: 22px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 20px;
    line-height: 1.5;
    color: #fff;
}
.quiz-counter {
    color: #a0a0ab;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 10px;
    text-align: center;
}
.share-code {
    font-size: 36px;
    font-weight: 800;
    color: #00d4ff;
    text-align: center;
    letter-spacing: 6px;
    padding: 20px;
    background: rgba(0,212,255,0.1);
    border: 2px solid rgba(0,212,255,0.3);
    border-radius: 16px;
    margin: 16px 0;
}
</style>
""", unsafe_allow_html=True)

# ======================================
# SYSTEM PROMPTS
# ======================================
TUTOR_SYSTEM = """
You are SmartLoop AI, a concise IGCSE tutor for Grade 6-8 students.
Answer clearly and simply using bullet points or short paragraphs.
Never write more than needed. Stay at Grade 6-8 level.
"""

QUIZ_SYSTEM = """
You are an IGCSE quiz engine. Output ONLY a valid raw JSON array.
No markdown, no explanation, no text outside the array.
Each object must have exactly:
{
  "question": "Question text",
  "type": "MCQ",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "Exact text of correct option",
  "explanation": "Why it is correct"
}
Generate 100% unique questions. Never copy from textbooks directly.
Hard difficulty = complex scenarios using only given concepts.
"""

PAPER_SYSTEM = """
You are an IGCSE examiner generating a full practice paper.
Format the paper professionally with:
- Header: Subject, Grade, Total Marks, Time Allowed
- Numbered questions with marks in brackets
- Mix of short answer, structured, and extended questions
- Mark scheme at the end under ## Mark Scheme
- Append [PDF_READY] at the very end.
Generate 100% original questions. Never copy from textbooks.
"""

# ======================================
# BUILT-IN KNOWLEDGE BASE
# ======================================
QUICK_KNOWLEDGE = {
    "photosynthesis": "Photosynthesis: plants use sunlight, CO2 and water to make glucose and oxygen. Formula: 6CO2 + 6H2O + light → C6H12O6 + 6O2. Occurs in chloroplasts.",
    "cell": "Basic unit of life. Animal cells: nucleus, mitochondria, membrane, cytoplasm, ribosomes. Plant cells also have: cell wall, chloroplasts, large vacuole.",
    "mitosis": "Cell division producing 2 identical daughter cells. Stages: Prophase, Metaphase, Anaphase, Telophase, Cytokinesis (PMATC).",
    "meiosis": "Cell division producing 4 genetically different cells with half the chromosome number. Occurs in reproductive organs.",
    "atom": "Smallest unit of an element. Nucleus: protons (+) and neutrons. Electrons (-) orbit the nucleus.",
    "decimals": "Numbers with whole and fractional parts separated by a decimal point. 3.14 = 3 whole and 14 hundredths.",
    "fractions": "Part of a whole. Numerator (top) ÷ denominator (bottom). To add: make denominators equal first.",
    "percentage": "Number out of 100. Fraction to %: divide then ×100. 3/4 = 75%.",
    "algebra": "Uses letters for unknowns. Solve by doing same to both sides. x + 5 = 10 → x = 5.",
    "pythagoras": "a² + b² = c² in a right-angled triangle. c is the hypotenuse.",
    "gravity": "Force pulling objects together. Earth: 9.8 m/s². F = mg.",
    "newton": "1) Object stays at rest/motion unless force acts. 2) F=ma. 3) Every action = equal and opposite reaction.",
    "speed": "Speed = Distance ÷ Time. Velocity = speed with direction. Acceleration = ΔSpeed ÷ Time.",
    "energy": "Ability to do work. Types: Kinetic, Potential, Thermal, Chemical, Electrical. Cannot be created or destroyed.",
    "periodic table": "Elements arranged by atomic number. Same group = similar properties. Metals left, non-metals right.",
    "acid": "Acids: pH < 7. Bases: pH > 7. Neutral: pH 7. Acid + base → salt + water.",
    "water cycle": "Evaporation → Condensation → Precipitation → Collection → repeat.",
    "solar system": "8 planets: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune.",
    "ecosystem": "All living/non-living things in an area. Food chain: Producer → Primary → Secondary → Tertiary Consumer.",
    "sound": "Energy waves through a medium. Fastest in solids. Speed in air ≈ 343 m/s. Frequency = pitch. Amplitude = loudness.",
    "light": "Electromagnetic radiation at 300,000 km/s. Can be reflected, refracted, absorbed. White light = ROYGBIV.",
    "magnetism": "Like poles repel, opposite attract. Earth is a giant magnet.",
    "electricity": "Flow of electrons. V = IR (Ohm's Law). Series = one path. Parallel = multiple paths.",
    "osmosis": "Water moves from high to low concentration through semi-permeable membrane. Passive.",
    "diffusion": "Particles move from high to low concentration. Passive — no energy needed.",
    "respiration": "Aerobic: glucose + O2 → CO2 + H2O + ATP. Anaerobic: glucose → lactic acid (animals) or ethanol + CO2 (yeast).",
    "dna": "Carries genetic information. Double helix. Base pairs: A-T, C-G. Found in cell nucleus.",
    "evolution": "Change in species over time through natural selection. Proposed by Charles Darwin.",
    "plate tectonics": "Earth's crust = moving plates. Collision → mountains. Separation → rift valleys. Boundaries → earthquakes/volcanoes.",
    "climate change": "Burning fossil fuels releases CO2. CO2 traps heat (greenhouse effect) → global warming.",
    "area": "Rectangle = l×w. Triangle = ½bh. Circle = πr². Units: cm², m².",
    "volume": "Cuboid = lwh. Cylinder = πr²h. Sphere = 4/3πr³. Units: cm³, m³.",
    "ratio": "Compares quantities. 3:2. Simplify by dividing both by HCF.",
    "probability": "Favourable outcomes ÷ total outcomes. Range: 0 to 1.",
    "forces": "Push or pull. Newtons. Types: gravity, friction, tension, normal, air resistance.",
    "pressure": "Pressure = Force ÷ Area. Units: Pascals (Pa).",
    "waves": "Transfer energy. Transverse: perpendicular vibration (light). Longitudinal: parallel vibration (sound).",
    "reflection": "Light bounces off surface. Angle of incidence = angle of reflection.",
    "refraction": "Light bends between media of different densities.",
    "density": "Density = Mass ÷ Volume. g/cm³. Less dense than water = floats.",
    "states of matter": "Solid: fixed shape/volume. Liquid: fixed volume. Gas: fills container.",
    "circle": "Circumference = 2πr. Area = πr². Diameter = 2r.",
    "angles": "Acute <90°. Right = 90°. Obtuse 90–180°. Straight = 180°. Triangle = 180°.",
    "indices": "aᵐ×aⁿ = aᵐ⁺ⁿ. a⁰ = 1. Powers/exponents.",
    "coordinates": "Points as (x,y). x = horizontal, y = vertical. Origin = (0,0).",
    "food chain": "Energy flow: Producer → Primary Consumer → Secondary → Tertiary.",
    "hormones": "Chemical messengers in blood. Insulin = blood sugar. Adrenaline = fight or flight.",
    "nervous system": "Brain + spinal cord = CNS. Reflex arc: stimulus → receptor → relay neuron → effector.",
    "rock cycle": "Igneous → Sedimentary → Metamorphic → back to Igneous.",
    "quadratic": "ax² + bx + c = 0. Formula: x = (-b ± √(b²-4ac)) / 2a.",
    "trigonometry": "SOH CAH TOA. sin=opp/hyp. cos=adj/hyp. tan=opp/adj.",
    "sequences": "Arithmetic: add same number. Geometric: multiply same number.",
    "digestive system": "Mouth → oesophagus → stomach → small intestine → large intestine → rectum → anus.",
    "circulatory system": "Heart pumps blood. Arteries: away from heart. Veins: back to heart.",
    "lungs": "Gas exchange. O2 enters blood, CO2 leaves. Diaphragm controls breathing.",
    "world war 2": "1939–1945. Allies (UK, USA, USSR) vs Axis (Germany, Italy, Japan). Germany surrendered May 1945.",
    "napoleon": "Napoleon Bonaparte (1769–1821) was a French military leader and Emperor who conquered much of Europe. Defeated at Waterloo (1815) and exiled to Saint Helena.",
    "napoleon bonaparte": "Napoleon Bonaparte (1769–1821) was a French military leader and Emperor who conquered much of Europe. Defeated at Waterloo (1815) and exiled to Saint Helena.",
    "democracy": "Citizens vote to elect leaders. Direct or representative.",
    "continent": "7 continents: Africa, Antarctica, Asia, Australia, Europe, North America, South America.",
    "shakespeare": "1564–1616. Romeo and Juliet, Hamlet, Macbeth. 37 plays, 154 sonnets.",
    "adjective": "Describes a noun. Comparative: bigger. Superlative: biggest.",
    "verb": "Action or state word. Past (ran), present (run), future (will run).",
    "noun": "Person, place, thing, or idea.",
    "simultaneous equations": "Two equations, two unknowns. Solve by substitution or elimination.",
    "climate": "Long-term average weather. Affected by latitude, altitude, distance from sea.",
    "vectors": "Quantities with magnitude and direction. Represented as arrows.",
    "human body": "Systems: skeletal, muscular, digestive, respiratory, circulatory, nervous, excretory.",
    "ionic bonding": "Transfer of electrons between metals and non-metals. Forms ions. Example: NaCl.",
    "covalent bonding": "Sharing of electrons between non-metals. Example: H2O, CO2.",
    "enzymes": "Biological catalysts. Speed up reactions. Each enzyme has a specific active site. Denatured by high temperature or wrong pH.",
    "genetics": "Study of inheritance. Genes are sections of DNA. Alleles are different versions of a gene. Dominant alleles mask recessive ones.",
    "chemical reactions": "Reactants → Products. Types: combustion, neutralisation, oxidation, reduction, decomposition.",
    "electromagnetic spectrum": "Radio → Microwave → Infrared → Visible → UV → X-ray → Gamma. All travel at speed of light.",
    "motion": "Described by distance, displacement, speed, velocity, acceleration. SUVAT equations used for uniform acceleration.",
    "work": "Work = Force × Distance. Units: Joules (J). Work is done when a force moves an object.",
    "power": "Power = Work ÷ Time. Units: Watts (W). Rate of doing work or transferring energy.",
}

def get_quick_answer(q):
    q_lower = q.lower().strip()
    if q_lower in QUICK_KNOWLEDGE:
        return QUICK_KNOWLEDGE[q_lower]
    for keyword, answer in QUICK_KNOWLEDGE.items():
        if keyword in q_lower:
            return answer
    return None

def fuzzy_match_knowledge(q):
    q_lower = q.lower().strip()
    q_words = set(q_lower.split())
    best_score = 0
    best_answer = None
    for keyword, answer in QUICK_KNOWLEDGE.items():
        k_words = set(keyword.lower().split())
        overlap = len(q_words & k_words)
        char_score = 0
        for qw in q_words:
            for kw in k_words:
                if len(qw) >= 4 and len(kw) >= 4:
                    matches = sum(1 for c in qw if c in kw)
                    ratio = matches / max(len(qw), len(kw))
                    if ratio > 0.75:
                        char_score += 1
        score = overlap * 2 + char_score
        if score > best_score:
            best_score = score
            best_answer = answer
    return best_answer if best_score >= 2 else None

# ======================================
# API KEYS
# ======================================
def get_keys(prefix):
    keys = []
    i = 1
    while True:
        k = st.secrets.get(f"{prefix}_{i}")
        if not k:
            break
        keys.append(k)
        i += 1
    single = st.secrets.get(prefix)
    if single and single not in keys:
        keys.append(single)
    return keys

GEMINI_KEYS = get_keys("GEMINI_API_KEY")
OPENAI_KEYS = get_keys("OPENAI_API_KEY")

if not GEMINI_KEYS and not OPENAI_KEYS:
    st.error("No API keys found.")
    st.stop()

# ======================================
# SESSION STATE
# ======================================
for key, default in [
    ("cache",          {}),
    ("chats",          {}),
    ("current_chat",   None),
    ("g_idx",          0),
    ("o_idx",          0),
    ("quiz_store",     {}),
    ("mode",           "💬 AI Tutor"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def new_chat():
    cid = str(uuid.uuid4())[:8]
    st.session_state.chats[cid] = {
        "title": "New Chat",
        "messages": []
    }
    st.session_state.current_chat = cid
    return cid

def current_messages():
    cid = st.session_state.current_chat
    if not cid or cid not in st.session_state.chats:
        cid = new_chat()
    return st.session_state.chats[cid]["messages"]

def set_chat_title(cid, first_message):
    title = first_message[:30].strip()
    if len(first_message) > 30:
        title += "..."
    st.session_state.chats[cid]["title"] = title

# Create initial chat if none
if not st.session_state.current_chat:
    new_chat()

# ======================================
# PDF LOADING
# ======================================
def detect_subject(filename):
    n = filename.lower()
    if any(k in n for k in ["math", "maths", "algebra"]):  return "math"
    if any(k in n for k in ["phys"]):                       return "physics"
    if any(k in n for k in ["chem"]):                       return "chemistry"
    if any(k in n for k in ["biol"]):                       return "biology"
    if any(k in n for k in ["eng", "english"]):             return "english"
    if any(k in n for k in ["sci"]):                        return "science"
    if any(k in n for k in ["hist"]):                       return "history"
    if any(k in n for k in ["geo"]):                        return "geography"
    return "general"

def get_pdf_hash():
    h = hashlib.md5()
    for f in sorted(os.listdir(".")):
        if f.endswith(".pdf"):
            h.update(f.encode())
            h.update(str(os.path.getmtime(f)).encode())
    return h.hexdigest()

@st.cache_resource
def load_pdfs():
    cache_file = "smartloop_index.pkl"
    hash_file  = "smartloop_hash.txt"
    current_hash = get_pdf_hash()
    if os.path.exists(cache_file) and os.path.exists(hash_file):
        try:
            with open(hash_file, "r") as f:
                if f.read() == current_hash:
                    with open(cache_file, "rb") as f:
                        return pickle.load(f)
        except:
            pass
    data = []
    for fname in os.listdir("."):
        if not fname.endswith(".pdf"):
            continue
        subject = detect_subject(fname)
        try:
            reader = PdfReader(fname)
            for i, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt and len(txt.strip()) > 30:
                    clean = re.sub(r'[^a-z0-9 ]', ' ', txt.lower())
                    words = set(clean.split())
                    data.append({
                        "text":    txt[:1200],
                        "words":   words,
                        "file":    fname,
                        "page":    i + 1,
                        "subject": subject
                    })
        except:
            pass
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        with open(hash_file, "w") as f:
            f.write(current_hash)
    except:
        pass
    return data

STOPWORDS = {
    "what","is","are","how","why","when","who","the","a","an","of",
    "in","to","and","does","do","explain","define","tell","me","about",
    "give","can","you","please","describe","mean","means","example",
    "examples","write","state","list","find","solve","calculate"
}

def search_pdf(q, subject_hint, pages_db):
    if not pages_db:
        return None
    q_clean = re.sub(r'[^a-z0-9 ]', ' ', q.lower())
    q_words = set(q_clean.split()) - STOPWORDS
    if not q_words:
        return None
    best_score = 0
    best_page  = None
    for page in pages_db:
        subj_bonus = 2 if (
            subject_hint != "general" and
            page["subject"] == subject_hint
        ) else 0
        score = len(q_words & page["words"]) + subj_bonus
        if score > best_score:
            best_score = score
            best_page  = page
    return best_page if best_score >= 2 else None

# ======================================
# AI CALLS
# ======================================
def ask_gemini(prompt, system=None):
    if not GEMINI_KEYS:
        return None
    for _ in range(len(GEMINI_KEYS)):
        key = GEMINI_KEYS[st.session_state.g_idx % len(GEMINI_KEYS)]
        st.session_state.g_idx += 1
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                "gemini-1.5-flash",
                system_instruction=system
            ) if system else genai.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(prompt).text
        except Exception as e:
            if "429" in str(e):
                time.sleep(3)
            continue
    return None

def ask_openai(prompt, system=None):
    if not OPENAI_KEYS:
        return None
    for _ in range(len(OPENAI_KEYS)):
        key = OPENAI_KEYS[st.session_state.o_idx % len(OPENAI_KEYS)]
        st.session_state.o_idx += 1
        try:
            client = openai.OpenAI(api_key=key)
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            r = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=msgs,
                max_tokens=500
            )
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                time.sleep(3)
            continue
    return None

def ask_ai(prompt, system=None):
    return ask_gemini(prompt, system) or ask_openai(prompt, system)

# ======================================
# WIKIPEDIA
# ======================================
def wiki(q):
    try:
        wikipedia.set_rate_limiting(True)
        return wikipedia.summary(
            q[:60], sentences=2, auto_suggest=False
        )
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            return wikipedia.summary(e.options[0], sentences=2)
        except:
            return None
    except:
        return None

# ======================================
# MATH SOLVER
# ======================================
def is_pure_calculation(q):
    return bool(re.fullmatch(
        r"[\d\.\+\-\*\/\(\)\s\^%]+", q.strip()
    ))

def solve_math(q):
    try:
        return str(round(eval(
            q.strip().replace("^", "**").replace(" ", "")
        ), 6))
    except:
        return None

# ======================================
# ANSWER ENGINE
# ======================================
def get_answer(query, pages_db):
    if query in st.session_state.cache:
        return st.session_state.cache[query]

    if ":" in query:
        subj_raw, q = query.split(":", 1)
        subject = subj_raw.strip().lower()
        q = q.strip()
    else:
        subject = "general"
        q = query.strip()

    def save(result):
        st.session_state.cache[query] = result
        return result

    if is_pure_calculation(q):
        ans = solve_math(q)
        if ans:
            return save((f"= **{ans}**", "🧮 Calculator", "calc"))

    pdf_page = search_pdf(q, subject, pages_db)
    if pdf_page:
        prompt = (
            f"You are a concise IGCSE tutor. "
            f"Use ONLY the textbook extract below. "
            f"Do not add outside information.\n\n"
            f"EXTRACT:\n{pdf_page['text'][:2500]}\n\n"
            f"QUESTION: {q}"
        )
        ans = ask_ai(prompt, TUTOR_SYSTEM)
        if ans:
            return save((
                ans.strip(),
                f"📖 {pdf_page['file']} — Page {pdf_page['page']}",
                "pdf"
            ))

    quick = get_quick_answer(q)
    if quick:
        return save((quick, "📚 Built-in knowledge", "kb"))

    fuzzy = fuzzy_match_knowledge(q)
    if fuzzy:
        return save((
            fuzzy,
            "📚 Built-in knowledge (auto-corrected)",
            "kb"
        ))

    wiki_ans = wiki(q)
    if wiki_ans:
        return save((wiki_ans, "🌐 Wikipedia", "wiki"))

    prompt = (
        f"You are SmartLoop AI, a concise IGCSE tutor "
        f"for Grade 6-8 students. Answer clearly and simply:\n{q}"
    )
    ans = ask_ai(prompt, TUTOR_SYSTEM)
    if ans:
        return save((ans.strip(), "💡 AI general knowledge", "ai"))

    return save(("Could not find an answer. Please rephrase.", "", ""))

# ======================================
# QUIZ ENGINE
# ======================================
def generate_quiz(subject, grade, difficulty, topic, num_q):
    prompt = f"""
Generate EXACTLY {num_q} IGCSE quiz questions.
Subject: {subject} | Grade: {grade} | Difficulty: {difficulty}
Topic: {topic}
Output only a valid JSON array. No markdown.
"""
    raw = ask_ai(prompt, QUIZ_SYSTEM)
    if not raw:
        return None
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    return None

def evaluate_answer(question, user_ans, correct):
    prompt = f"""
Evaluate this student answer.
Question: {question}
Student: {user_ans}
Correct: {correct}
Output ONLY valid JSON:
{{"is_correct": true/false, "explanation": "brief feedback"}}
"""
    raw = ask_ai(prompt)
    if raw:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    return {"is_correct": False, "explanation": "Could not evaluate."}

# ======================================
# PDF PAPER GENERATOR
# ======================================
def md_to_rl(text):
    s = (text or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(\S.+?)\*(?!\*)", r"<i>\1</i>", s)
    return s

def create_pdf(content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch
    )
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle(
        "T", parent=styles["Heading1"],
        fontSize=18, textColor=colors.HexColor("#00d4ff"),
        spaceAfter=10, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    h2_s = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=13, spaceAfter=8, spaceBefore=10,
        fontName="Helvetica-Bold"
    )
    body_s = ParagraphStyle(
        "B", parent=styles["BodyText"],
        fontSize=11, spaceAfter=6,
        alignment=TA_LEFT, fontName="Helvetica"
    )
    story = []
    table_rows = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        ncols = max(len(r) for r in table_rows)
        norm = [
            [Paragraph(md_to_rl(c), body_s)
             for c in r + [""] * (ncols - len(r))]
            for r in table_rows
        ]
        t = Table(norm, colWidths=[doc.width/max(1,ncols)]*ncols)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#00d4ff")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("BACKGROUND",(0,1),(-1,-1),colors.HexColor("#f8f9fa")),
            ("GRID",(0,0),(-1,-1),0.5,colors.grey),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
        ]))
        story.extend([t, Spacer(1,0.12*inch)])
        table_rows.clear()

    for line in str(content or "").split("\n"):
        if "[PDF_READY]" in line.upper():
            continue
        s = line.strip()
        if "|" in s and s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                table_rows.append(cells)
            continue
        flush_table()
        if not s:
            story.append(Spacer(1, 0.1*inch))
        elif s.startswith("# "):
            story.append(Paragraph(md_to_rl(s[2:].strip()), title_s))
        elif s.startswith("## "):
            story.append(Paragraph(md_to_rl(s[3:].strip()), h2_s))
        elif s.startswith("### "):
            story.append(Paragraph(f"<b>{md_to_rl(s[4:].strip())}</b>", body_s))
        else:
            story.append(Paragraph(md_to_rl(s), body_s))

    flush_table()
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("<i>Generated by SmartLoop AI</i>", body_s))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ======================================
# QUIZ UI
# ======================================
def render_quiz():
    # Quiz setup screen
    if not st.session_state.get("quiz_active") and \
       not st.session_state.get("quiz_finished"):

        st.markdown(
            "<div class='big-title' style='font-size:32px;'>⚡ Quiz Engine</div>",
            unsafe_allow_html=True
        )

        tab_create, tab_join = st.tabs(["🎯 Create Quiz", "🔑 Join Quiz"])

        with tab_create:
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                q_subj = c1.selectbox(
                    "Subject",
                    ["Math","Science","Physics","Chemistry",
                     "Biology","English","History","Geography"]
                )
                q_grade = c2.selectbox(
                    "Grade",
                    ["Grade 6","Grade 7","Grade 8","Grade 9","Grade 10"]
                )
                q_diff = c3.selectbox(
                    "Difficulty", ["Easy","Medium","Hard"]
                )
                c4, c5 = st.columns([3,1])
                q_topic = c4.text_input(
                    "Topic",
                    placeholder="e.g. Forces, Fractions, WW2..."
                )
                q_num = c5.selectbox("Questions", [5,10,15,20])

                col1, col2 = st.columns(2)
                start_btn = col1.button(
                    "🚀 Start Quiz",
                    type="primary",
                    use_container_width=True
                )
                code_btn = col2.button(
                    "🔗 Generate ShareCode",
                    use_container_width=True
                )

                if start_btn or code_btn:
                    if not q_topic.strip():
                        st.warning("Please enter a topic.")
                    else:
                        with st.spinner("Generating quiz..."):
                            questions = generate_quiz(
                                q_subj, q_grade,
                                q_diff, q_topic, q_num
                            )
                        if questions:
                            code = str(uuid.uuid4())[:6].upper()
                            st.session_state.quiz_store[code] = {
                                "questions": questions,
                                "subject": q_subj,
                                "grade": q_grade,
                                "topic": q_topic
                            }
                            if start_btn:
                                st.session_state.quiz_questions  = questions
                                st.session_state.quiz_subject     = q_subj
                                st.session_state.quiz_score       = 0
                                st.session_state.quiz_current_q   = 1
                                st.session_state.quiz_active      = True
                                st.session_state.quiz_finished    = False
                                st.session_state.quiz_user_answer = None
                                st.session_state.quiz_share_code  = code
                                st.rerun()
                            else:
                                st.markdown(
                                    f"<div class='share-code'>{code}</div>",
                                    unsafe_allow_html=True
                                )
                                st.success(
                                    f"Quiz saved! Share this code with students."
                                )
                        else:
                            st.error("Failed to generate. Check API keys.")

        with tab_join:
            with st.container(border=True):
                code_input = st.text_input(
                    "Enter ShareCode",
                    placeholder="e.g. A1B2C3",
                    max_chars=6
                ).upper()
                if st.button("Join Quiz", use_container_width=True):
                    store = st.session_state.get("quiz_store", {})
                    if code_input in store:
                        data = store[code_input]
                        st.session_state.quiz_questions  = data["questions"]
                        st.session_state.quiz_subject     = data["subject"]
                        st.session_state.quiz_score       = 0
                        st.session_state.quiz_current_q   = 1
                        st.session_state.quiz_active      = True
                        st.session_state.quiz_finished    = False
                        st.session_state.quiz_user_answer = None
                        st.session_state.quiz_share_code  = code_input
                        st.rerun()
                    else:
                        st.error("Invalid ShareCode. Ask your teacher for the correct code.")

    # Finished screen
    elif st.session_state.get("quiz_finished"):
        score = st.session_state.get("quiz_score", 0)
        total = len(st.session_state.get("quiz_questions", []))
        pct   = int((score/total)*100) if total else 0

        st.balloons()
        with st.container(border=True):
            st.markdown(
                "<h1 style='text-align:center;color:#2ecc71;'>"
                "🎉 Quiz Complete!</h1>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<h2 style='text-align:center;'>"
                f"Score: <span style='color:#00d4ff;'>"
                f"{score} / {total} ({pct}%)</span></h2>",
                unsafe_allow_html=True
            )
            grade_msg = (
                "🌟 Excellent!" if pct >= 80 else
                "👍 Good effort!" if pct >= 60 else
                "📚 Keep practising!"
            )
            st.markdown(
                f"<p style='text-align:center;font-size:18px;'>"
                f"{grade_msg}</p>",
                unsafe_allow_html=True
            )
            if st.session_state.get("quiz_share_code"):
                st.info(
                    f"Challenge friends with code: "
                    f"**{st.session_state.quiz_share_code}**"
                )

        if st.button(
            "Take Another Quiz",
            type="primary",
            use_container_width=True
        ):
            for k in list(st.session_state.keys()):
                if k.startswith("quiz_"):
                    del st.session_state[k]
            st.rerun()

    # Active quiz
    elif st.session_state.get("quiz_active"):
        q_list = st.session_state.get("quiz_questions", [])
        q_idx  = st.session_state.get("quiz_current_q", 1) - 1

        if q_idx >= len(q_list):
            st.session_state.quiz_finished = True
            st.rerun()

        q_data = q_list[q_idx]
        progress = (q_idx) / len(q_list)
        st.progress(progress)

        with st.container(border=True):
            st.markdown(
                f"<div class='quiz-counter'>"
                f"Question {q_idx+1} of {len(q_list)} | "
                f"Score: {st.session_state.get('quiz_score',0)}"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<div class='quiz-question-text'>"
                f"{q_data.get('question','')}</div>",
                unsafe_allow_html=True
            )

            if st.session_state.get("quiz_user_answer") is None:
                if q_data.get("type","MCQ") == "MCQ":
                    for oi, opt in enumerate(q_data.get("options",[])):
                        if st.button(
                            opt,
                            use_container_width=True,
                            key=f"opt_{q_idx}_{oi}"
                        ):
                            st.session_state.quiz_user_answer = opt
                            st.rerun()
                else:
                    sa = st.text_area("Your answer:")
                    if st.button("Submit Answer", type="primary"):
                        with st.spinner("Evaluating..."):
                            ev = evaluate_answer(
                                q_data.get("question"),
                                sa,
                                q_data.get("correct_answer")
                            )
                            st.session_state.quiz_sa_eval = ev
                        st.session_state.quiz_user_answer = sa
                        st.rerun()
            else:
                user_ans = st.session_state.quiz_user_answer
                if q_data.get("type","MCQ") == "MCQ":
                    is_correct  = (user_ans == q_data.get("correct_answer"))
                    explanation = q_data.get("explanation","")
                else:
                    ev          = st.session_state.get("quiz_sa_eval",{})
                    is_correct  = ev.get("is_correct", False)
                    explanation = ev.get("explanation","")

                if is_correct:
                    st.success(f"✅ Correct! {explanation}")
                    if not st.session_state.get(f"scored_{q_idx}"):
                        st.session_state.quiz_score += 1
                        st.session_state[f"scored_{q_idx}"] = True
                else:
                    st.error(
                        f"❌ Incorrect. "
                        f"Answer: **{q_data.get('correct_answer')}**"
                        f"\n\n{explanation}"
                    )

                is_last = (q_idx + 1 == len(q_list))
                if st.button(
                    "Finish Quiz" if is_last else "Next Question ➡️",
                    type="primary",
                    use_container_width=True
                ):
                    if is_last:
                        st.session_state.quiz_finished = True
                    else:
                        st.session_state.quiz_current_q += 1
                    st.session_state.quiz_user_answer = None
                    st.session_state.pop("quiz_sa_eval", None)
                    st.rerun()

# ======================================
# PAPER GENERATOR UI
# ======================================
def render_paper_generator():
    st.markdown(
        "<div class='big-title' style='font-size:32px;'>📝 IGCSE Paper Generator</div>",
        unsafe_allow_html=True
    )

    with st.container(border=True):
        c1, c2 = st.columns(2)
        subj  = c1.selectbox(
            "Subject",
            ["Mathematics","Physics","Chemistry","Biology",
             "Combined Science","English Language","English Literature",
             "History","Geography","Economics"]
        )
        grade = c2.selectbox(
            "Grade / Year",
            ["Grade 8","Grade 9","Grade 10","IGCSE Year 1","IGCSE Year 2"]
        )
        diff  = c1.selectbox("Difficulty", ["Foundation","Core","Extended"])
        marks = c2.number_input("Total Marks", 20, 100, 50, 5)
        time_allowed = c1.selectbox(
            "Time Allowed",
            ["45 minutes","1 hour","1 hour 30 minutes","2 hours","2 hours 30 minutes"]
        )
        topic = st.text_input(
            "Topic / Chapter Focus",
            placeholder="e.g. Forces and Motion, Algebra, World War 1..."
        )
        extra = st.text_area(
            "Extra Instructions",
            placeholder="e.g. Include a data analysis question, focus on calculations..."
        )

        if st.button(
            "🤖 Generate IGCSE Paper",
            type="primary",
            use_container_width=True
        ):
            if not topic.strip():
                st.warning("Please enter a topic.")
            else:
                prompt = f"""
Generate a full IGCSE {subj} practice paper.
Grade: {grade} | Difficulty: {diff} | Total Marks: {marks}
Time Allowed: {time_allowed} | Topic Focus: {topic}
Extra: {extra}

Format:
# SmartLoop AI — Practice Paper
## {subj}
**Grade:** {grade} | **Total Marks:** {marks} | **Time:** {time_allowed}

Instructions to candidates:
- Answer ALL questions
- Show all working for full marks
- Marks are shown in brackets

---

[Questions here — number them, include mark allocations in brackets]

## Mark Scheme

[Detailed mark scheme here]

[PDF_READY]
"""
                with st.spinner("Writing paper... this may take 30 seconds"):
                    paper = ask_ai(prompt, PAPER_SYSTEM)

                if paper:
                    st.session_state.draft_paper = paper
                    st.rerun()
                else:
                    st.error("Failed to generate. Check API keys.")

    if st.session_state.get("draft_paper"):
        with st.expander("📄 Preview Paper", expanded=True):
            clean = re.sub(
                r"\[PDF_READY\]","",
                st.session_state.draft_paper,
                flags=re.IGNORECASE
            )
            st.markdown(clean)

        col1, col2 = st.columns(2)
        try:
            pdf_buf = create_pdf(st.session_state.draft_paper)
            col1.download_button(
                "📥 Download PDF",
                data=pdf_buf,
                file_name="SmartLoop_Paper.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            col1.error(f"PDF error: {e}")

        if col2.button(
            "🔄 Regenerate",
            use_container_width=True
        ):
            del st.session_state["draft_paper"]
            st.rerun()

# ======================================
# LOAD PDFs
# ======================================
with st.spinner("📚 Loading PDF library..."):
    pages_db = load_pdfs()

# ======================================
# SIDEBAR
# ======================================
with st.sidebar:
    st.markdown(
        "<div style='color:#00d4ff;font-weight:800;"
        "font-size:18px;margin-bottom:8px;'>"
        "🧠 SmartLoop AI</div>",
        unsafe_allow_html=True
    )

    # Mode selector
    mode = st.radio(
        "Mode",
        ["💬 AI Tutor", "⚡ Quiz", "📝 Paper Generator"],
        label_visibility="collapsed",
        key="mode"
    )

    st.divider()

    # Chat management — only show in tutor mode
    if mode == "💬 AI Tutor":
        if st.button(
            "➕ New Chat",
            use_container_width=True,
            type="primary"
        ):
            new_chat()
            st.rerun()

        st.markdown(
            "<div style='font-size:12px;color:#a0a0ab;"
            "margin:8px 0 4px;'>Recent Chats</div>",
            unsafe_allow_html=True
        )

        # List all chats
        for cid, chat_data in reversed(
            list(st.session_state.chats.items())
        ):
            col1, col2 = st.columns([0.82, 0.18],
                                     vertical_alignment="center")
            is_active = (cid == st.session_state.current_chat)

            title = chat_data.get("title", "New Chat")
            btn_label = f"{'🟢' if is_active else '💬'} {title}"

            if col1.button(
                btn_label,
                key=f"chat_{cid}",
                use_container_width=True
            ):
                st.session_state.current_chat = cid
                st.rerun()

            if col2.button(
                "🗑",
                key=f"del_{cid}",
                use_container_width=True
            ):
                del st.session_state.chats[cid]
                if st.session_state.current_chat == cid:
                    if st.session_state.chats:
                        st.session_state.current_chat = list(
                            st.session_state.chats.keys()
                        )[-1]
                    else:
                        new_chat()
                st.rerun()

    st.divider()

    # Status
    st.success(f"📚 {len(pages_db)} pages indexed")
    st.info(
        f"🔑 Gemini: {len(GEMINI_KEYS)} | "
        f"OpenAI: {len(OPENAI_KEYS)}"
    )

    # Quiz share codes
    if st.session_state.get("quiz_store"):
        st.divider()
        st.markdown(
            "<div style='font-size:12px;color:#a0a0ab;'>"
            "Active Quiz Codes:</div>",
            unsafe_allow_html=True
        )
        for code in st.session_state.quiz_store:
            q_data = st.session_state.quiz_store[code]
            st.code(
                f"{code} — {q_data['subject']} "
                f"({len(q_data['questions'])}Q)"
            )

# ======================================
# MAIN CONTENT
# ======================================
if mode == "⚡ Quiz":
    render_quiz()

elif mode == "📝 Paper Generator":
    render_paper_generator()

else:
    # AI TUTOR CHAT
    st.markdown(
        "<div class='big-title'>🧠 SmartLoop AI</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div class='sub-title'>"
        "Use <b>Subject: Question</b> — e.g. "
        "<i>Math: What is algebra?</i>"
        "</div>",
        unsafe_allow_html=True
    )

    messages = current_messages()

    # Display messages
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("source"):
                badge = {
                    "calc": "tier-calc",
                    "pdf":  "tier-pdf",
                    "kb":   "tier-kb",
                    "wiki": "tier-wiki",
                    "ai":   "tier-ai"
                }.get(msg.get("tier",""), "tier-ai")
                st.markdown(
                    f'<span class="tier-badge {badge}">'
                    f'{msg["source"]}</span>',
                    unsafe_allow_html=True
                )

    # Chat input
    q = st.chat_input("Ask your question...")

    if q:
        cid = st.session_state.current_chat
        messages = current_messages()

        # Set title from first message
        if not messages:
            set_chat_title(cid, q)

        messages.append({"role": "user", "content": q})

        with st.chat_message("user"):
            st.markdown(q)

        with st.chat_message("assistant"):
            is_cached = q in st.session_state.cache
            if not is_cached:
                thinking = st.empty()
                thinking.markdown(
                    "<span style='color:#00d4ff;font-size:13px;'>"
                    "⏳ Searching sources...</span>",
                    unsafe_allow_html=True
                )

            ans, src, tier = get_answer(q, pages_db)

            if not is_cached:
                thinking.empty()

            st.markdown(ans)
            if src:
                badge = {
                    "calc": "tier-calc",
                    "pdf":  "tier-pdf",
                    "kb":   "tier-kb",
                    "wiki": "tier-wiki",
                    "ai":   "tier-ai"
                }.get(tier, "tier-ai")
                st.markdown(
                    f'<span class="tier-badge {badge}">'
                    f'{src}</span>',
                    unsafe_allow_html=True
                )

        messages.append({
            "role":    "assistant",
            "content": ans,
            "source":  src,
            "tier":    tier
        })
