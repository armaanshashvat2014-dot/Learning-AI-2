import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import time
import re
import json
import uuid
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    border-radius: 28px !important;
    padding: 24px !important;
    box-shadow: 0 16px 40px 0 rgba(0,0,0,0.3) !important;
    margin: 20px 0 !important;
}
.stTextInput>div>div>input,
.stTextArea>div>textarea,
.stSelectbox>div>div>div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 12px !important;
    color: #fff !important;
}
.stButton>button {
    background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.02) 100%) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 20px !important;
    backdrop-filter: blur(20px) !important;
    color: #fff !important;
    font-weight: 600 !important;
    transition: all 0.3s !important;
}
@media (hover: hover) and (pointer: fine) {
    .stButton>button:hover {
        background: linear-gradient(180deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.05) 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
    }
}
.stButton>button:active { transform: translateY(1px) !important; }
.big-title {
    color: #00d4ff;
    text-align: center;
    font-size: 48px;
    font-weight: 800;
    letter-spacing: -2px;
    text-shadow: 0 0 12px rgba(0,212,255,0.4);
    margin-bottom: 4px;
}
.sub-title {
    text-align: center;
    color: rgba(255,255,255,0.5);
    font-size: 16px;
    margin-bottom: 30px;
}
.card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 24px;
    padding: 24px;
    margin: 16px 0;
    color: #f5f5f7;
    word-wrap: break-word;
    overflow-wrap: break-word;
}
.quiz-question-text {
    font-size: 24px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 24px;
    line-height: 1.5;
    color: #fff;
}
.quiz-counter {
    color: #a0a0ab;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 12px;
    text-align: center;
}
.thinking-container {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    margin: 10px 0;
    border-left: 3px solid #00d4ff;
}
.thinking-text { color: #00d4ff; font-size: 14px; font-weight: 600; }
.thinking-dots { display: flex; gap: 4px; }
.thinking-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #00d4ff;
    animation: tp 1.4s infinite;
}
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes tp {
    0%,60%,100% { opacity:0.3; transform:scale(0.8); }
    30% { opacity:1; transform:scale(1.2); }
}
.weak-spot-item {
    background: rgba(231,76,60,0.1);
    border: 1px solid rgba(231,76,60,0.2);
    border-radius: 12px;
    padding: 10px 14px;
    color: #f5f5f7;
    margin-bottom: 8px;
}
.success-item {
    background: rgba(46,204,113,0.1);
    border: 1px solid rgba(46,204,113,0.2);
    border-radius: 12px;
    padding: 10px 14px;
    color: #f5f5f7;
}
.mastery-value { font-size: 48px; color: #00d4ff; font-weight: 800; }
.tier-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-top: 8px;
}
.tier-pdf { background: rgba(0,212,255,0.15); color: #00d4ff; border: 1px solid rgba(0,212,255,0.3); }
.tier-kb  { background: rgba(46,204,113,0.15); color: #2ecc71; border: 1px solid rgba(46,204,113,0.3); }
.tier-ai  { background: rgba(252,132,4,0.15);  color: #fc8404; border: 1px solid rgba(252,132,4,0.3); }
</style>
""", unsafe_allow_html=True)

# ======================================
# SYSTEM PROMPTS
# ======================================
TUTOR_SYSTEM = """
You are SmartLoop AI, an elite IGCSE/Cambridge tutor for Grade 6-8 students.

RULES:
1. Answer clearly and simply at Grade 6-8 level.
2. Use markdown tables and bullet points where helpful.
3. For practice papers: include ## Mark Scheme at the end and append [PDF_READY].
4. Keep explanations concise and student-friendly.
5. Every 6th message, silently check for weak spots and output ONLY if clear:
===ANALYTICS_START===
{"subject": "Math", "weak_point": "Fractions"}
===ANALYTICS_END===
"""

QUIZ_SYSTEM = """
You are a quiz engine. Output ONLY a valid raw JSON array. No markdown, no text, no explanation.
Each object must have exactly:
{
  "question": "Question text",
  "type": "MCQ",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "Exact text of correct option",
  "explanation": "Why it is correct"
}
Generate 100% new unique questions. Never copy from textbooks.
"""

PAPER_SYSTEM = TUTOR_SYSTEM + "\nCRITICAL: Always append [PDF_READY] at the very end. Always include ## Mark Scheme."

# ======================================
# BUILT-IN KNOWLEDGE BASE (TIER 2)
# ======================================
QUICK_KNOWLEDGE = {
    "photosynthesis": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy (glucose). Formula: 6CO2 + 6H2O + light → C6H12O6 + 6O2. Occurs in chloroplasts.",
    "cell": "A cell is the basic unit of life. Animal cells: nucleus, mitochondria, cell membrane, cytoplasm, ribosomes. Plant cells also have: cell wall, chloroplasts, large vacuole.",
    "mitosis": "Mitosis produces two identical daughter cells. Stages: Prophase, Metaphase, Anaphase, Telophase, Cytokinesis (PMATC).",
    "meiosis": "Meiosis produces four genetically different cells with half the chromosome number. Occurs in reproductive organs.",
    "atom": "Smallest unit of an element. Nucleus has protons (+) and neutrons (neutral). Electrons (-) orbit the nucleus.",
    "decimals": "Numbers with a whole part and fractional part separated by a decimal point. Example: 3.14 = 3 whole and 14 hundredths.",
    "fractions": "Part of a whole. Numerator (top) ÷ denominator (bottom). To add: make denominators the same first.",
    "percentage": "A number out of 100. Fraction to %: divide then × 100. Example: 3/4 = 75%.",
    "algebra": "Uses letters for unknown numbers. Solve by doing same operation on both sides. Example: x + 5 = 10, x = 5.",
    "pythagoras": "a² + b² = c² in a right-angled triangle. c is the hypotenuse (longest side).",
    "gravity": "Force pulling objects together. On Earth: 9.8 m/s². Formula: F = mg.",
    "newton": "Newton's Laws: 1) Object stays at rest/motion unless a force acts. 2) F=ma. 3) Every action has equal and opposite reaction.",
    "speed": "Speed = Distance ÷ Time. Velocity = speed with direction. Acceleration = Change in Speed ÷ Time.",
    "energy": "Ability to do work. Types: Kinetic, Potential, Thermal, Chemical, Electrical. Cannot be created or destroyed — only converted.",
    "periodic table": "Elements arranged by atomic number. Same group = similar properties. Metals on left, non-metals on right.",
    "acid": "Acids: pH < 7. Bases: pH > 7. Neutral: pH 7. Acid + base → salt + water.",
    "water cycle": "Evaporation → Condensation → Precipitation → Collection → repeat.",
    "solar system": "8 planets: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune.",
    "ecosystem": "All living/non-living things in an area. Food chain: Producer → Primary → Secondary → Tertiary Consumer.",
    "sound": "Energy travelling as waves through a medium. Caused by vibrations. Fastest in solids. Speed in air ≈ 343 m/s. Frequency (Hz) = pitch. Amplitude = loudness.",
    "light": "Electromagnetic radiation at 300,000 km/s. Can be reflected, refracted, absorbed. White light = ROYGBIV.",
    "magnetism": "Like poles repel, opposite attract. Earth is a giant magnet. Field lines go north to south.",
    "electricity": "Flow of electrons. V = IR (Ohm's Law). Series = one path. Parallel = multiple paths.",
    "osmosis": "Water moves from high to low concentration through semi-permeable membrane. No energy needed.",
    "diffusion": "Particles move from high to low concentration. Passive process.",
    "respiration": "Aerobic: glucose + O2 → CO2 + H2O + ATP. Anaerobic: glucose → lactic acid (animals) or ethanol + CO2 (yeast).",
    "dna": "Carries genetic information. Double helix. Base pairs: A-T, C-G. Found in cell nucleus.",
    "evolution": "Change in species over time through natural selection. Proposed by Charles Darwin.",
    "plate tectonics": "Earth's crust = moving plates. Collision → mountains. Separation → rift valleys. Boundaries → earthquakes/volcanoes.",
    "climate change": "Burning fossil fuels releases CO2. CO2 traps heat (greenhouse effect) → global warming.",
    "area": "Rectangle = l×w. Triangle = ½×b×h. Circle = π×r². Units: cm², m².",
    "volume": "Cuboid = l×w×h. Cylinder = π×r²×h. Sphere = 4/3×π×r³. Units: cm³, m³.",
    "ratio": "Compares quantities. Example 3:2. Simplify by dividing both by HCF.",
    "probability": "Favourable outcomes ÷ total outcomes. Range: 0 (impossible) to 1 (certain).",
    "forces": "Push or pull. Measured in Newtons. Types: gravity, friction, tension, normal, air resistance.",
    "pressure": "Pressure = Force ÷ Area. Units: Pascals (Pa).",
    "waves": "Transfer energy. Transverse: vibration perpendicular (light). Longitudinal: vibration parallel (sound).",
    "reflection": "Light bounces off surface. Angle of incidence = angle of reflection.",
    "refraction": "Light bends between media of different densities.",
    "density": "Density = Mass ÷ Volume. Units: g/cm³. Objects less dense than water float.",
    "states of matter": "Solid: fixed shape/volume. Liquid: fixed volume. Gas: fills container.",
    "circle": "Circumference = 2πr. Area = πr². Diameter = 2r.",
    "angles": "Acute <90°. Right = 90°. Obtuse 90–180°. Straight = 180°. Reflex >180°. Triangle angles = 180°.",
    "indices": "aᵐ×aⁿ = aᵐ⁺ⁿ. a⁰ = 1. Also called powers or exponents.",
    "coordinates": "Points as (x,y). x = horizontal, y = vertical. Origin = (0,0).",
    "symmetry": "Line symmetry: mirror halves. Rotational: same after rotation.",
    "food chain": "Shows energy flow: Producer → Primary Consumer → Secondary → Tertiary.",
    "hormones": "Chemical messengers in blood. Examples: insulin (blood sugar), adrenaline (fight or flight).",
    "nervous system": "Brain + spinal cord = CNS. Reflex arc: stimulus → receptor → relay neuron → effector.",
    "rock cycle": "Igneous → Sedimentary → Metamorphic → back to Igneous.",
    "climate": "Long-term average weather. Affected by latitude, altitude, distance from sea.",
    "world war 2": "1939–1945. Allies (UK, USA, USSR) vs Axis (Germany, Italy, Japan).",
    "democracy": "Citizens vote to elect leaders. Direct or representative.",
    "continent": "7 continents: Africa, Antarctica, Asia, Australia, Europe, North America, South America.",
    "adjective": "Describes a noun. Comparative: bigger. Superlative: biggest.",
    "verb": "Action or state word. Past (ran), present (run), future (will run).",
    "noun": "Person, place, thing, or idea. Common: dog. Proper: London. Abstract: happiness.",
    "shakespeare": "1564–1616. Works: Romeo and Juliet, Hamlet, Macbeth. Wrote 37 plays and 154 sonnets.",
    "quadratic": "ax² + bx + c = 0. Solve by factorising or quadratic formula: x = (-b ± √(b²-4ac)) / 2a.",
    "simultaneous equations": "Two equations with two unknowns. Solve by substitution or elimination.",
    "trigonometry": "SOH CAH TOA. sin = opposite/hypotenuse. cos = adjacent/hypotenuse. tan = opposite/adjacent.",
    "sequences": "Arithmetic: add/subtract same number each time. Geometric: multiply/divide same number.",
    "vectors": "Quantities with both magnitude and direction. Represented as arrows.",
    "human body": "Systems: skeletal, muscular, digestive, respiratory, circulatory, nervous, excretory, reproductive.",
    "digestive system": "Mouth → oesophagus → stomach → small intestine → large intestine → rectum → anus.",
    "circulatory system": "Heart pumps blood. Arteries carry blood away from heart. Veins return blood to heart.",
    "lungs": "Organs of gas exchange. Oxygen enters blood, carbon dioxide leaves. Diaphragm controls breathing.",
}

def get_quick_answer(question):
    q = question.lower()
    for keyword, answer in QUICK_KNOWLEDGE.items():
        if keyword in q:
            return answer
    return None

# ======================================
# API KEY MANAGEMENT
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
    st.error("No API keys found. Add them to Streamlit Secrets.")
    st.stop()

def get_next_gemini_key():
    if "g_idx" not in st.session_state:
        st.session_state.g_idx = 0
    key = GEMINI_KEYS[st.session_state.g_idx % len(GEMINI_KEYS)]
    st.session_state.g_idx += 1
    return key

def get_next_openai_key():
    if "o_idx" not in st.session_state:
        st.session_state.o_idx = 0
    key = OPENAI_KEYS[st.session_state.o_idx % len(OPENAI_KEYS)]
    st.session_state.o_idx += 1
    return key

# ======================================
# PDF LOADING
# ======================================
@st.cache_resource
def load_pdfs():
    data = []
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                reader = PdfReader(f)
                for p in reader.pages:
                    txt = p.extract_text()
                    if txt and len(txt.strip()) > 20:
                        data.append({"text": txt[:1500], "file": f})
            except:
                pass
    return data

with st.spinner("Loading library..."):
    books = load_pdfs()

pdf_loaded = len(books) > 0

# ======================================
# AI CALLS
# ======================================
def ask_gemini(prompt, system=None):
    if not GEMINI_KEYS:
        return None
    for _ in range(len(GEMINI_KEYS)):
        key = get_next_gemini_key()
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                "gemini-1.5-flash",
                system_instruction=system
            ) if system else genai.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(prompt).text
        except Exception as e:
            err = str(e)
            st.sidebar.warning(f"Gemini: {err[:120]}")
            if "429" in err or "quota" in err.lower():
                time.sleep(5)
            continue
    return None

def ask_openai(prompt, system=None):
    if not OPENAI_KEYS:
        return None
    for _ in range(len(OPENAI_KEYS)):
        key = get_next_openai_key()
        try:
            client = openai.OpenAI(api_key=key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            r = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=600
            )
            return r.choices[0].message.content
        except Exception as e:
            err = str(e)
            st.sidebar.warning(f"OpenAI: {err[:120]}")
            if "429" in err or "quota" in err.lower():
                time.sleep(5)
            continue
    return None

def ask_ai(prompt, system=None):
    result = ask_gemini(prompt, system)
    if result:
        return result
    result = ask_openai(prompt, system)
    if result:
        return result
    return None

# ======================================
# WIKIPEDIA FALLBACK
# ======================================
def wiki(q):
    try:
        return wikipedia.summary(q, sentences=3, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            return wikipedia.summary(e.options[0], sentences=3)
        except:
            return ""
    except:
        return ""

# ======================================
# PDF SEARCH
# ======================================
def search_pdf(q):
    if not books:
        return None
    stopwords = {
        "what","is","are","how","why","when","who","the","a","an",
        "of","in","to","and","does","do","explain","define","tell",
        "me","about","give","can","you","please","describe","mean",
        "means","meaning","example","examples","write","state","list"
    }
    words = set(q.lower().split()) - stopwords
    if not words:
        return None

    scored = []
    for b in books:
        score = len(words & set(b["text"].lower().split()))
        if score > 0:
            scored.append((score, b["text"], b["file"]))

    scored.sort(reverse=True)

    if not scored or scored[0][0] < 2:
        return None

    top = scored[:3]
    combined = "\n\n---\n\n".join([t for _, t, _ in top])
    return {"text": combined, "file": top[0][2]}

# ======================================
# CLEAN ANSWER
# ======================================
def _clean_answer(answer):
    if not answer:
        return ""
    match = re.search(
        r"===ANALYTICS_START===(.*?)===ANALYTICS_END===",
        answer,
        flags=re.IGNORECASE | re.DOTALL
    )
    if match:
        try:
            data = json.loads(match.group(1).strip())
            wp = data.get("weak_point")
            if wp and wp.lower() != "none":
                if "weak_spots" not in st.session_state:
                    st.session_state.weak_spots = []
                if wp not in st.session_state.weak_spots:
                    st.session_state.weak_spots.append(wp)
        except:
            pass
        answer = answer[:match.start()].strip()

    answer = re.sub(
        r"===ANALYTICS_START===.*?===ANALYTICS_END===",
        "", answer, flags=re.IGNORECASE | re.DOTALL
    ).strip()
    answer = re.sub(
        r"\[PDF_READY\]", "", answer, flags=re.IGNORECASE
    ).strip()
    return answer

# ======================================
# THREE-TIER ANSWER ENGINE
# ======================================
def get_answer(query):
    if ":" in query:
        _, q = query.split(":", 1)
        q = q.strip()
    else:
        q = query.strip()

    # ── TIER 1: PDFs ──────────────────
    pdf_result = search_pdf(q)
    if pdf_result:
        prompt = f"""
You are SmartLoop AI, an IGCSE tutor.
Student asked: "{q}"

Relevant content from their textbook:
{pdf_result['text'][:3000]}

Using ONLY the textbook content above, give a clear simple answer.
Do not add outside information.
"""
        answer = ask_ai(prompt, TUTOR_SYSTEM)
        if answer:
            return (
                _clean_answer(answer),
                f"📖 Source: **{pdf_result['file']}**",
                "pdf"
            )

    # ── TIER 2: Built-in knowledge ────
    quick = get_quick_answer(q)
    if quick:
        return (
            quick,
            "📚 Answered from built-in knowledge base",
            "kb"
        )

    # ── TIER 3: Gemini / OpenAI ───────
    prompt = f"""
You are SmartLoop AI, an IGCSE tutor for Grade 6-8 students.
Student asked: "{q}"

Answer clearly and simply from your general knowledge.
Keep it at Grade 6-8 level.
"""
    answer = ask_ai(prompt, TUTOR_SYSTEM)
    if answer:
        return (
            _clean_answer(answer),
            "💡 Answered from AI general knowledge",
            "ai"
        )

    # ── Final fallback: Wikipedia ─────
    wiki_res = wiki(q)
    if wiki_res:
        return (
            wiki_res,
            "🌐 Answered from Wikipedia",
            "ai"
        )

    return (
        "All sources unavailable. Please try again in a moment.",
        "",
        ""
    )

# ======================================
# PDF GENERATION
# ======================================
def md_to_rl(text):
    s = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(\S.+?)\*(?!\*)", r"<i>\1</i>", s)
    return s

def create_pdf(content, filename="SmartLoop_Paper.pdf"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=18, textColor=colors.HexColor("#00d4ff"),
        spaceAfter=12, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, spaceAfter=10,
        spaceBefore=10, fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["BodyText"],
        fontSize=11, spaceAfter=8,
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
            [Paragraph(md_to_rl(c), body_style)
             for c in r + [""] * (ncols - len(r))]
            for r in table_rows
        ]
        t = Table(norm, colWidths=[doc.width / max(1, ncols)] * ncols)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#00d4ff")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#f8f9fa")),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.extend([t, Spacer(1, 0.15*inch)])
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
            story.append(Spacer(1, 0.12*inch))
        elif s.startswith("# "):
            story.append(Paragraph(md_to_rl(s[2:].strip()), title_style))
        elif s.startswith("## "):
            story.append(Paragraph(md_to_rl(s[3:].strip()), h2_style))
        elif s.startswith("### "):
            story.append(Paragraph(
                f"<b>{md_to_rl(s[4:].strip())}</b>", body_style
            ))
        else:
            story.append(Paragraph(md_to_rl(s), body_style))

    flush_table()
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        "<i>Generated by SmartLoop AI</i>", body_style
    ))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ======================================
# QUIZ GENERATION
# ======================================
def generate_quiz_ai(subject, grade, difficulty, topic, num_q):
    context = search_pdf(f"{subject} {topic}")
    ctx_text = context["text"][:2000] if context else ""
    prompt = f"""
Create EXACTLY {num_q} unique IGCSE quiz questions.
Subject: {subject} | Grade: {grade} | Difficulty: {difficulty} | Topic: {topic}

Context:
{ctx_text}
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

def evaluate_short_answer(question, user_ans, reference):
    prompt = f"""
Evaluate this student answer.
Question: {question}
Student: {user_ans}
Reference: {reference}
Output ONLY valid JSON: {{"is_correct": true/false, "explanation": "feedback"}}
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
# QUIZ ENGINE UI
# ======================================
def render_quiz_engine():
    if not st.session_state.get("quiz_active") and \
       not st.session_state.get("quiz_finished"):

        st.markdown(
            "<div class='big-title' style='font-size:32px;'>⚡ Quiz Engine</div>",
            unsafe_allow_html=True
        )

        tab_ai, tab_join = st.tabs(["🤖 AI Generator", "🔑 Join Quiz"])

        with tab_ai:
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                q_subj = c1.selectbox("Subject", ["Math","Science","English"])
                q_grade = c2.selectbox(
                    "Grade", ["Grade 6","Grade 7","Grade 8"]
                )
                q_diff = c3.selectbox(
                    "Difficulty", ["Easy","Medium","Hard"]
                )
                c4, c5 = st.columns([3, 1])
                q_topic = c4.text_input(
                    "Topic / Chapter",
                    placeholder="e.g. Fractions, Forces..."
                )
                q_num = c5.selectbox("Questions", [5, 10, 15, 20])

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
                    with st.spinner("Generating quiz..."):
                        questions = generate_quiz_ai(
                            q_subj, q_grade, q_diff, q_topic, q_num
                        )
                    if questions:
                        share_code = str(uuid.uuid4())[:6].upper()
                        if "quiz_store" not in st.session_state:
                            st.session_state.quiz_store = {}
                        st.session_state.quiz_store[share_code] = {
                            "questions": questions,
                            "params": {
                                "subj": q_subj, "grade": q_grade,
                                "diff": q_diff, "topic": q_topic
                            }
                        }
                        if start_btn:
                            st.session_state.quiz_questions = questions
                            st.session_state.quiz_params = {"subj": q_subj}
                            st.session_state.quiz_score = 0
                            st.session_state.quiz_current_q = 1
                            st.session_state.quiz_active = True
                            st.session_state.quiz_finished = False
                            st.session_state.quiz_user_answer = None
                            st.session_state.quiz_share_code = share_code
                            st.rerun()
                        else:
                            st.success(
                                f"Quiz ready! ShareCode: **{share_code}**"
                            )
                    else:
                        st.error("Failed to generate quiz. Check API keys.")

        with tab_join:
            with st.container(border=True):
                code_input = st.text_input(
                    "Enter ShareCode",
                    placeholder="e.g. A1B2C3"
                ).upper()
                if st.button("Join Quiz", use_container_width=True):
                    store = st.session_state.get("quiz_store", {})
                    if code_input in store:
                        q_data = store[code_input]
                        st.session_state.quiz_questions = \
                            q_data["questions"]
                        st.session_state.quiz_params = q_data["params"]
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_current_q = 1
                        st.session_state.quiz_active = True
                        st.session_state.quiz_finished = False
                        st.session_state.quiz_user_answer = None
                        st.session_state.quiz_share_code = code_input
                        st.rerun()
                    else:
                        st.error("Invalid ShareCode.")

    elif st.session_state.get("quiz_finished"):
        score = st.session_state.get("quiz_score", 0)
        total = len(st.session_state.get("quiz_questions", []))
        st.balloons()
        with st.container(border=True):
            st.markdown(
                "<h1 style='text-align:center;color:#2ecc71;'>"
                "🎉 Quiz Complete!</h1>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<h2 style='text-align:center;'>Score: "
                f"<span style='color:#00d4ff;'>{score} / {total}</span>"
                f"</h2>",
                unsafe_allow_html=True
            )
            if st.session_state.get("quiz_share_code"):
                st.info(
                    f"Challenge friends: "
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

    elif st.session_state.get("quiz_active"):
        q_list = st.session_state.get("quiz_questions", [])
        q_idx = st.session_state.get("quiz_current_q", 1) - 1

        if q_idx >= len(q_list):
            st.session_state.quiz_finished = True
            st.rerun()

        q_data = q_list[q_idx]

        with st.container(border=True):
            st.markdown(
                f"<div class='quiz-counter'>"
                f"Question {q_idx+1} of {len(q_list)}</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<div class='quiz-question-text'>"
                f"{q_data.get('question','')}</div>",
                unsafe_allow_html=True
            )

            if st.session_state.get("quiz_user_answer") is None:
                if q_data.get("type", "MCQ") == "MCQ":
                    for oi, opt in enumerate(q_data.get("options", [])):
                        if st.button(
                            opt,
                            use_container_width=True,
                            key=f"opt_{q_idx}_{oi}"
                        ):
                            st.session_state.quiz_user_answer = opt
                            st.rerun()
                else:
                    sa = st.text_area("Your answer:")
                    if st.button("Submit", type="primary"):
                        with st.spinner("Evaluating..."):
                            ev = evaluate_short_answer(
                                q_data.get("question"),
                                sa,
                                q_data.get("correct_answer")
                            )
                            st.session_state.quiz_sa_eval = ev
                        st.session_state.quiz_user_answer = sa
                        st.rerun()
            else:
                user_ans = st.session_state.quiz_user_answer
                if q_data.get("type", "MCQ") == "MCQ":
                    is_correct = (user_ans == q_data.get("correct_answer"))
                    explanation = q_data.get("explanation", "")
                else:
                    ev = st.session_state.get("quiz_sa_eval", {})
                    is_correct = ev.get("is_correct", False)
                    explanation = ev.get("explanation", "")

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
                    "Finish Quiz" if is_last else "Next Question",
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
        "<div class='big-title' style='font-size:32px;'>📝 Paper Generator</div>",
        unsafe_allow_html=True
    )
    with st.container(border=True):
        c1, c2 = st.columns(2)
        subj = c1.selectbox(
            "Subject",
            ["Math","Science","English","Physics","Chemistry","Biology"]
        )
        grade = c2.selectbox("Grade", ["Grade 6","Grade 7","Grade 8"])
        diff = c1.selectbox("Difficulty", ["Easy","Medium","Hard"])
        marks = c2.number_input("Total Marks", 10, 100, 40, 5)
        topic = st.text_input(
            "Topic / Chapter",
            placeholder="e.g. Chapter 3, Forces..."
        )
        extra = st.text_area("Extra Instructions (optional)")

        if st.button(
            "🤖 Generate Paper",
            type="primary",
            use_container_width=True
        ):
            pdf_result = search_pdf(f"{subj} {topic}")
            context = pdf_result["text"][:3000] if pdf_result else ""
            prompt = f"""
Generate a full CIE {subj} practice paper for {grade} students.
Difficulty: {diff}. Total Marks: {marks}. Topic: {topic}.
Extra: {extra}

Context from textbooks:
{context}

Format:
# SmartLoop AI
## Practice Paper
### {subj} - {grade}

Include numbered questions with marks.
End with ## Mark Scheme.
Append [PDF_READY] at the very end.
"""
            with st.spinner("Writing paper..."):
                paper = ask_ai(prompt, PAPER_SYSTEM)

            if paper:
                st.session_state.draft_paper = paper
                st.rerun()
            else:
                st.error("Failed to generate paper. Check API keys.")

    if st.session_state.get("draft_paper"):
        with st.expander("📄 Preview Paper", expanded=True):
            clean = re.sub(
                r"\[PDF_READY\]", "",
                st.session_state.draft_paper,
                flags=re.IGNORECASE
            )
            st.markdown(f'<div class="card">{clean}</div>',
                        unsafe_allow_html=True)
        try:
            pdf_buffer = create_pdf(st.session_state.draft_paper)
            st.download_button(
                "📥 Download PDF",
                data=pdf_buffer,
                file_name="SmartLoop_Paper.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF error: {e}")

# ======================================
# ANALYTICS UI
# ======================================
def render_analytics():
    st.markdown(
        "<div class='big-title' style='font-size:32px;'>📊 My Analytics</div>",
        unsafe_allow_html=True
    )

    quiz_history = st.session_state.get("quiz_history_log", [])
    total_q = len(quiz_history)
    correct = sum(1 for q in quiz_history if q.get("is_correct"))
    mastery = int((correct / total_q) * 100) if total_q > 0 else 0

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Questions Answered", total_q)
        col2.metric("Correct", correct)
        col3.metric("Mastery", f"{mastery}%")

    weak_spots = st.session_state.get("weak_spots", [])
    st.markdown("### ⚠️ Detected Weak Spots")
    if not weak_spots:
        st.markdown(
            "<div class='success-item'>"
            "No weak spots detected yet. Keep studying! 🎉"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        for i, ws in enumerate(weak_spots):
            col1, col2 = st.columns([0.85, 0.15])
            col1.markdown(
                f"<div class='weak-spot-item'>{ws}</div>",
                unsafe_allow_html=True
            )
            if col2.button("Dismiss", key=f"dismiss_{i}"):
                st.session_state.weak_spots.pop(i)
                st.rerun()

# ======================================
# SIDEBAR
# ======================================
with st.sidebar:
    st.markdown(
        "<div style='color:#00d4ff;font-weight:800;"
        "font-size:20px;'>🧠 SmartLoop AI</div>",
        unsafe_allow_html=True
    )
    st.divider()
    mode = st.radio(
        "Mode",
        ["💬 AI Tutor","⚡ Interactive Quiz",
         "📝 Paper Generator","📊 Analytics"],
        label_visibility="collapsed"
    )
    st.divider()

    if st.sidebar.button("🔍 Test APIs"):
        st.sidebar.write("Testing Gemini...")
        r1 = ask_gemini("Say hello in one word.")
        st.sidebar.write(f"Gemini: {r1 or 'FAILED'}")
        st.sidebar.write("Testing OpenAI...")
        r2 = ask_openai("Say hello in one word.")
        st.sidebar.write(f"OpenAI: {r2 or 'FAILED'}")

    if pdf_loaded:
        st.success(f"📚 {len(books)} PDF chunks loaded")
    else:
        st.info("No PDFs found")
    st.info(f"🔑 Gemini: {len(GEMINI_KEYS)} | OpenAI: {len(OPENAI_KEYS)}")

# ======================================
# MAIN APP ROUTER
# ======================================
if mode == "⚡ Interactive Quiz":
    render_quiz_engine()

elif mode == "📝 Paper Generator":
    render_paper_generator()

elif mode == "📊 Analytics":
    render_analytics()

else:
    # ======================================
    # AI TUTOR CHAT
    # ======================================
    st.markdown(
        "<div class='big-title'>🧠 SmartLoop AI</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div class='sub-title'>"
        "Your IGCSE AI Tutor — Use Subject: Question for faster answers"
        "</div>",
        unsafe_allow_html=True
    )

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": (
                "👋 **Hey! I'm SmartLoop AI!**\n\n"
                "I'm your IGCSE tutor for Grade 6-8.\n\n"
                "I search your **textbooks first**, then my "
                "**knowledge base**, then **Gemini/ChatGPT** — "
                "so you always get the most accurate answer!\n\n"
                "Tip: Use **Subject: Question** format.\n"
                "Example: *Math: What are fractions?*"
            ),
            "tier": ""
        }]
    if "msg_count" not in st.session_state:
        st.session_state.msg_count = 0

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg.get("content", "")
            content = re.sub(
                r"===ANALYTICS_START===.*?===ANALYTICS_END===",
                "", content, flags=re.IGNORECASE | re.DOTALL
            )
            content = re.sub(
                r"\[PDF_READY\]", "", content, flags=re.IGNORECASE
            )
            st.markdown(content)

            tier = msg.get("tier", "")
            source = msg.get("source", "")
            if source:
                badge_class = (
                    "tier-pdf" if tier == "pdf" else
                    "tier-kb"  if tier == "kb"  else
                    "tier-ai"
                )
                st.markdown(
                    f'<span class="tier-badge {badge_class}">'
                    f'{source}</span>',
                    unsafe_allow_html=True
                )

            if msg.get("is_downloadable"):
                try:
                    pdf_buf = create_pdf(msg.get("content", ""))
                    st.download_button(
                        "📥 Download PDF",
                        data=pdf_buf,
                        file_name="SmartLoop_Paper.pdf",
                        mime="application/pdf",
                        key=f"dl_{id(msg)}"
                    )
                except:
                    pass

    query = st.chat_input(
        "Ask SmartLoop... (Subject: Question)"
    )

    if query:
        st.session_state.messages.append({
            "role": "user",
            "content": query,
            "tier": ""
        })
        st.session_state.msg_count += 1
        st.rerun()

    if (st.session_state.messages and
            st.session_state.messages[-1]["role"] == "user"):

        with st.chat_message("assistant"):
            think = st.empty()
            think.markdown("""
<div class="thinking-container">
    <span class="thinking-text">Searching sources</span>
    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)

            last_query = st.session_state.messages[-1]["content"]

            if st.session_state.msg_count % 6 == 0:
                last_query += (
                    "\n\n[Silently check for weak spots "
                    "and output ANALYTICS block if found.]"
                )

            answer, source, tier = get_answer(last_query)
            think.empty()

            is_dl = bool(
                re.search(r"\[PDF_READY\]", answer or "", re.IGNORECASE) or
                re.search(r"##\s*Mark Scheme", answer or "", re.IGNORECASE)
            )

            clean = re.sub(
                r"\[PDF_READY\]", "", answer or "",
                flags=re.IGNORECASE
            ).strip()
            st.markdown(clean)

            if source:
                badge_class = (
                    "tier-pdf" if tier == "pdf" else
                    "tier-kb"  if tier == "kb"  else
                    "tier-ai"
                )
                st.markdown(
                    f'<span class="tier-badge {badge_class}">'
                    f'{source}</span>',
                    unsafe_allow_html=True
                )

            if is_dl:
                try:
                    pdf_buf = create_pdf(answer)
                    st.download_button(
                        "📥 Download PDF",
                        data=pdf_buf,
                        file_name="SmartLoop_Paper.pdf",
                        mime="application/pdf"
                    )
                except:
                    pass

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "source": source,
                "tier": tier,
                "is_downloadable": is_dl
            })
            st.rerun()
