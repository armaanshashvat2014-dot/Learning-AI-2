import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import threading
import re
import pickle
import hashlib

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
.stChatMessage {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 20px !important;
    padding: 16px !important;
}
.stTextInput>div>div>input {
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
.status-bar {
    position: fixed;
    bottom: 80px;
    right: 20px;
    background: rgba(25,25,35,0.9);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 12px;
    color: #a0a0ab;
    backdrop-filter: blur(20px);
    z-index: 999;
}
</style>
""", unsafe_allow_html=True)

# ======================================
# BUILT-IN KNOWLEDGE BASE (TIER 2)
# ======================================
QUICK_KNOWLEDGE = {
    "photosynthesis": "Photosynthesis is the process by which plants use sunlight, water, and CO2 to produce glucose and oxygen. Formula: 6CO2 + 6H2O + light → C6H12O6 + 6O2. Occurs in chloroplasts.",
    "cell": "A cell is the basic unit of life. Animal cells: nucleus, mitochondria, cell membrane, cytoplasm, ribosomes. Plant cells also have: cell wall, chloroplasts, large vacuole.",
    "mitosis": "Mitosis produces two identical daughter cells. Stages: Prophase, Metaphase, Anaphase, Telophase, Cytokinesis (PMATC).",
    "meiosis": "Meiosis produces four genetically different cells with half the chromosome number. Occurs in reproductive organs.",
    "atom": "Smallest unit of an element. Nucleus: protons (+) and neutrons (neutral). Electrons (-) orbit the nucleus.",
    "decimals": "Numbers with whole and fractional parts separated by a decimal point. Example: 3.14 = 3 whole and 14 hundredths.",
    "fractions": "Part of a whole. Numerator (top) ÷ denominator (bottom). To add: make denominators equal first.",
    "percentage": "A number out of 100. To convert fraction: divide then ×100. Example: 3/4 = 75%.",
    "algebra": "Uses letters for unknowns. Solve by doing same operation on both sides. x + 5 = 10 → x = 5.",
    "pythagoras": "a² + b² = c² in a right-angled triangle. c is the hypotenuse (longest side).",
    "gravity": "Force pulling objects together. On Earth: 9.8 m/s². F = mg.",
    "newton": "1) Object stays at rest/motion unless force acts. 2) F=ma. 3) Every action has equal and opposite reaction.",
    "speed": "Speed = Distance ÷ Time. Velocity = speed with direction. Acceleration = ΔSpeed ÷ Time.",
    "energy": "Ability to do work. Types: Kinetic, Potential, Thermal, Chemical, Electrical. Cannot be created or destroyed.",
    "periodic table": "Elements arranged by atomic number. Same group = similar properties. Metals left, non-metals right.",
    "acid": "Acids: pH < 7. Bases: pH > 7. Neutral: pH 7 (water). Acid + base → salt + water.",
    "water cycle": "Evaporation → Condensation → Precipitation → Collection → repeat.",
    "solar system": "8 planets orbit the Sun: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune.",
    "ecosystem": "All living/non-living things in an area. Food chain: Producer → Primary → Secondary → Tertiary Consumer.",
    "sound": "Energy travelling as waves. Caused by vibrations. Fastest in solids. Speed in air ≈ 343 m/s. Frequency = pitch. Amplitude = loudness.",
    "light": "Electromagnetic radiation at 300,000 km/s. Can be reflected, refracted, absorbed. White light = ROYGBIV.",
    "magnetism": "Like poles repel, opposite attract. Earth is a giant magnet. Field lines go north to south.",
    "electricity": "Flow of electrons. V = IR (Ohm's Law). Series = one path. Parallel = multiple paths.",
    "osmosis": "Water moves from high to low concentration through semi-permeable membrane. Passive — no energy needed.",
    "diffusion": "Particles move from high to low concentration. Passive process. No energy needed.",
    "respiration": "Aerobic: glucose + O2 → CO2 + H2O + ATP. Anaerobic: glucose → lactic acid (animals) or ethanol + CO2 (yeast).",
    "dna": "Carries genetic information. Double helix. Base pairs: A-T, C-G. Found in cell nucleus.",
    "evolution": "Change in species over time through natural selection. Proposed by Charles Darwin.",
    "plate tectonics": "Earth's crust = moving plates. Collision → mountains. Separation → rift valleys. Boundaries → earthquakes/volcanoes.",
    "climate change": "Burning fossil fuels releases CO2. CO2 traps heat (greenhouse effect) → global warming.",
    "area": "Rectangle = l×w. Triangle = ½bh. Circle = πr². Units: cm², m².",
    "volume": "Cuboid = lwh. Cylinder = πr²h. Sphere = 4/3πr³. Units: cm³, m³.",
    "ratio": "Compares quantities. Example 3:2. Simplify by dividing both by HCF.",
    "probability": "Favourable outcomes ÷ total outcomes. Range: 0 (impossible) to 1 (certain).",
    "forces": "Push or pull. Measured in Newtons. Types: gravity, friction, tension, normal, air resistance.",
    "pressure": "Pressure = Force ÷ Area. Units: Pascals (Pa).",
    "waves": "Transfer energy. Transverse: vibration perpendicular (light). Longitudinal: vibration parallel (sound).",
    "reflection": "Light bounces off a surface. Angle of incidence = angle of reflection.",
    "refraction": "Light bends when passing between media of different densities.",
    "density": "Density = Mass ÷ Volume. Units: g/cm³. Less dense than water = floats.",
    "states of matter": "Solid: fixed shape/volume. Liquid: fixed volume. Gas: fills container.",
    "circle": "Circumference = 2πr. Area = πr². Diameter = 2r. π ≈ 3.14159.",
    "angles": "Acute <90°. Right = 90°. Obtuse 90–180°. Straight = 180°. Reflex >180°. Triangle = 180°.",
    "indices": "aᵐ×aⁿ = aᵐ⁺ⁿ. a⁰ = 1. Also called powers or exponents.",
    "coordinates": "Points as (x,y). x = horizontal, y = vertical. Origin = (0,0).",
    "food chain": "Energy flow: Producer → Primary Consumer → Secondary → Tertiary.",
    "hormones": "Chemical messengers in blood. Insulin = blood sugar. Adrenaline = fight or flight.",
    "nervous system": "Brain + spinal cord = CNS. Reflex arc: stimulus → receptor → relay neuron → effector.",
    "rock cycle": "Igneous → Sedimentary → Metamorphic → back to Igneous.",
    "quadratic": "ax² + bx + c = 0. Use quadratic formula: x = (-b ± √(b²-4ac)) / 2a.",
    "trigonometry": "SOH CAH TOA. sin=opp/hyp. cos=adj/hyp. tan=opp/adj.",
    "sequences": "Arithmetic: add/subtract same number. Geometric: multiply/divide same number.",
    "human body": "Systems: skeletal, muscular, digestive, respiratory, circulatory, nervous, excretory.",
    "digestive system": "Mouth → oesophagus → stomach → small intestine → large intestine → rectum → anus.",
    "circulatory system": "Heart pumps blood. Arteries: away from heart. Veins: back to heart.",
    "lungs": "Gas exchange organs. O2 enters blood, CO2 leaves. Diaphragm controls breathing.",
    "world war 2": "1939–1945. Allies (UK, USA, USSR) vs Axis (Germany, Italy, Japan).",
    "democracy": "Citizens vote to elect leaders. Direct or representative.",
    "continent": "7 continents: Africa, Antarctica, Asia, Australia, Europe, North America, South America.",
    "shakespeare": "1564–1616. Romeo and Juliet, Hamlet, Macbeth. 37 plays, 154 sonnets.",
    "adjective": "Describes a noun. Comparative: bigger. Superlative: biggest.",
    "verb": "Action or state word. Past (ran), present (run), future (will run).",
    "noun": "Person, place, thing, or idea.",
    "simultaneous equations": "Two equations, two unknowns. Solve by substitution or elimination.",
    "vectors": "Quantities with magnitude and direction. Represented as arrows.",
    "climate": "Long-term average weather. Affected by latitude, altitude, distance from sea.",
}

def get_quick_answer(q):
    q_lower = q.lower()
    # exact keyword match first
    for keyword, answer in QUICK_KNOWLEDGE.items():
        if keyword in q_lower:
            return answer
    return None

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
if "pages_db"    not in st.session_state: st.session_state.pages_db = []
if "loaded"      not in st.session_state: st.session_state.loaded = False
if "cache"       not in st.session_state: st.session_state.cache = {}
if "chat"        not in st.session_state: st.session_state.chat = []
if "g_idx"       not in st.session_state: st.session_state.g_idx = 0
if "o_idx"       not in st.session_state: st.session_state.o_idx = 0

# ======================================
# FAST PDF LOADER WITH DISK CACHE
# ======================================
def get_pdf_hash():
    h = hashlib.md5()
    for f in sorted(os.listdir(".")):
        if f.endswith(".pdf"):
            h.update(f.encode())
            h.update(str(os.path.getmtime(f)).encode())
    return h.hexdigest()

def detect_subject(filename):
    n = filename.lower()
    if any(k in n for k in ["math", "maths", "algebra", "geometry"]):
        return "math"
    if any(k in n for k in ["phys", "physics"]):
        return "physics"
    if any(k in n for k in ["chem", "chemistry"]):
        return "chemistry"
    if any(k in n for k in ["biol", "biology"]):
        return "biology"
    if any(k in n for k in ["eng", "english", "liter"]):
        return "english"
    if any(k in n for k in ["sci", "science"]):
        return "science"
    if any(k in n for k in ["hist", "history"]):
        return "history"
    if any(k in n for k in ["geo", "geography"]):
        return "geography"
    return "general"

def load_pdfs_background():
    cache_file = "smartloop_index.pkl"
    hash_file  = "smartloop_hash.txt"
    current_hash = get_pdf_hash()

    # Load from disk cache if unchanged
    if os.path.exists(cache_file) and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            if f.read() == current_hash:
                try:
                    with open(cache_file, "rb") as f:
                        data = pickle.load(f)
                    st.session_state.pages_db = data
                    st.session_state.loaded = True
                    return
                except:
                    pass

    # Re-index PDFs
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
                    # store clean words set for fast scoring
                    clean = txt.lower()
                    clean = re.sub(r'[^a-z0-9 ]', ' ', clean)
                    words = set(clean.split())
                    data.append({
                        "text":    txt[:1200],
                        "clean":   clean[:1200],
                        "words":   words,
                        "file":    fname,
                        "page":    i + 1,
                        "subject": subject
                    })
                # progressive updates every 20 pages
                if len(data) % 20 == 0:
                    st.session_state.pages_db = data.copy()
        except:
            pass

    st.session_state.pages_db = data
    st.session_state.loaded = True

    # Save to disk
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        with open(hash_file, "w") as f:
            f.write(current_hash)
    except:
        pass

# Start background loader once
if not st.session_state.loaded and not st.session_state.pages_db:
    threading.Thread(target=load_pdfs_background, daemon=True).start()

# ======================================
# SMART PDF SEARCH
# ======================================
STOPWORDS = {
    "what","is","are","how","why","when","who","the","a","an","of",
    "in","to","and","does","do","explain","define","tell","me","about",
    "give","can","you","please","describe","mean","means","meaning",
    "example","examples","write","state","list","find","solve","calculate"
}

def search_pdf(q, subject_hint="general"):
    if not st.session_state.pages_db:
        return None

    q_clean = re.sub(r'[^a-z0-9 ]', ' ', q.lower())
    q_words = set(q_clean.split()) - STOPWORDS
    if not q_words:
        return None

    best_score = 0
    best_page  = None

    for page in st.session_state.pages_db:
        # subject bonus: pages matching detected subject score higher
        subj_bonus = 2 if (
            subject_hint != "general" and
            page["subject"] == subject_hint
        ) else 0

        # word overlap score
        overlap = len(q_words & page["words"])
        score   = overlap + subj_bonus

        if score > best_score:
            best_score = score
            best_page  = page

    # require at least 2 meaningful keyword hits
    if best_score < 2:
        return None

    return best_page

# ======================================
# AI CALLS WITH KEY ROTATION
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
                import time; import time as t; t.sleep(3)
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
                max_tokens=400
            )
            return r.choices[0].message.content
        except Exception as e:
            if "429" in str(e):
                import time; import time as t; t.sleep(3)
            continue
    return None

def ask_ai(prompt, system=None):
    return ask_gemini(prompt, system) or ask_openai(prompt, system)

# ======================================
# WIKIPEDIA
# ======================================
def wiki(q):
    try:
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
    return bool(re.fullmatch(r"[\d\.\+\-\*\/\(\)\s\^%]+", q.strip()))

def solve_math(q):
    try:
        q = q.strip().replace("^", "**").replace(" ", "")
        return str(round(eval(q), 6))
    except:
        return None

# ======================================
# FOUR-TIER ANSWER ENGINE
# ======================================
SYSTEM = """
You are SmartLoop AI, a concise IGCSE tutor for Grade 6-8 students.
Answer clearly and simply. Use bullet points or short paragraphs.
Never write more than needed. Stay at Grade 6-8 level.
"""

def get_answer(query):
    # Cache hit — instant
    cached = st.session_state.cache.get(query)
    if cached:
        return cached

    # Parse subject prefix
    if ":" in query:
        subj_raw, q = query.split(":", 1)
        subject = subj_raw.strip().lower()
        q = q.strip()
    else:
        subject = "general"
        q = query.strip()

    # ── TIER 0: Pure calculation ──────
    if is_pure_calculation(q):
        ans = solve_math(q)
        if ans:
            result = (f"= **{ans}**", "🧮 Calculator", "calc")
            st.session_state.cache[query] = result
            return result

    # ── TIER 1: PDF search ────────────
    pdf_page = search_pdf(q, subject)
    if pdf_page:
        prompt = f"""
You are a concise IGCSE tutor.
Use ONLY the textbook extract below to answer.
Do not add outside information.

TEXTBOOK EXTRACT:
{pdf_page['text'][:2500]}

STUDENT QUESTION:
{q}
"""
        ans = ask_ai(prompt, SYSTEM)
        if ans:
            src    = f"📖 {pdf_page['file']} — Page {pdf_page['page']}"
            result = (ans.strip(), src, "pdf")
            st.session_state.cache[query] = result
            return result

    # ── TIER 2: Built-in knowledge ────
    quick = get_quick_answer(q)
    if quick:
        result = (quick, "📚 Built-in knowledge base", "kb")
        st.session_state.cache[query] = result
        return result

    # ── TIER 3: Wikipedia ─────────────
    wiki_ans = wiki(q)
    if wiki_ans:
        result = (wiki_ans, "🌐 Wikipedia", "wiki")
        st.session_state.cache[query] = result
        return result

    # ── TIER 4: Gemini / OpenAI ───────
    prompt = f"""
You are SmartLoop AI, a concise IGCSE tutor for Grade 6-8 students.
Answer this question clearly and simply:
{q}
"""
    ans = ask_ai(prompt, SYSTEM)
    if ans:
        result = (ans.strip(), "💡 AI general knowledge", "ai")
        st.session_state.cache[query] = result
        return result

    result = (
        "Could not find an answer. Please rephrase your question.",
        "", ""
    )
    st.session_state.cache[query] = result
    return result

# ======================================
# UI
# ======================================
st.markdown(
    "<div class='big-title'>🧠 SmartLoop AI</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div class='sub-title'>"
    "Use <b>Subject: Question</b> for faster answers — "
    "e.g. <i>Math: What is algebra?</i>"
    "</div>",
    unsafe_allow_html=True
)

# Chat history
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source"):
            badge = {
                "calc": "tier-calc",
                "pdf":  "tier-pdf",
                "kb":   "tier-kb",
                "wiki": "tier-wiki",
                "ai":   "tier-ai"
            }.get(msg.get("tier", ""), "tier-ai")
            st.markdown(
                f'<span class="tier-badge {badge}">'
                f'{msg["source"]}</span>',
                unsafe_allow_html=True
            )

# Chat input
q = st.chat_input("Ask your question...")

if q:
    st.session_state.chat.append({
        "role": "user", "content": q
    })

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        # Show thinking only if NOT cached
        if q not in st.session_state.cache:
            thinking = st.empty()
            thinking.markdown(
                "<span style='color:#00d4ff;font-size:13px;'>"
                "⏳ Searching sources...</span>",
                unsafe_allow_html=True
            )
        
        ans, src, tier = get_answer(q)
        
        if q not in st.session_state.cache:
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
                f'<span class="tier-badge {badge}">{src}</span>',
                unsafe_allow_html=True
            )

    st.session_state.chat.append({
        "role": "assistant",
        "content": ans,
        "source": src,
        "tier": tier
    })

# ======================================
# STATUS BAR
# ======================================
with st.sidebar:
    st.markdown(
        "<div style='color:#00d4ff;font-weight:800;"
        "font-size:18px;margin-bottom:12px;'>🧠 SmartLoop AI</div>",
        unsafe_allow_html=True
    )

    pages = len(st.session_state.pages_db)
    cached = len(st.session_state.cache)

    if st.session_state.loaded:
        st.success(f"📚 {pages} pages indexed")
    else:
        st.info(f"⚡ Learning PDFs... ({pages} pages so far)")
        st.progress(min(pages / 200, 1.0))

    st.info(f"⚡ {cached} answers cached")
    st.info(f"🔑 Gemini: {len(GEMINI_KEYS)} | OpenAI: {len(OPENAI_KEYS)}")

    if st.button("🔍 Test APIs"):
        with st.spinner("Testing..."):
            r1 = ask_gemini("Say OK")
            r2 = ask_openai("Say OK")
        st.write(f"Gemini: {'✅' if r1 else '❌'}")
        st.write(f"OpenAI: {'✅' if r2 else '❌'}")

    if st.button("🗑️ Clear Cache"):
        st.session_state.cache = {}
        st.success("Cache cleared!")

    if st.button("🗑️ Clear Chat"):
        st.session_state.chat = []
        st.rerun()

    st.divider()
    st.markdown("""
**How it works:**
1. 🧮 Calculator (instant)
2. 📖 Your PDFs (textbook)
3. 📚 Built-in knowledge
4. 🌐 Wikipedia
5. 💡 Gemini / ChatGPT
""")
