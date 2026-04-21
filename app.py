import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import os
import re
import time
import pickle
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(
    page_title="MentorLoop Smart Study AI",
    page_icon="📚",
    layout="wide"
)

GEMINI_MODEL = "gemini-2.0-flash"
OPENAI_MODEL = "gpt-3.5-turbo"
PDF_FOLDER = "."

# ======================================
# BUILT-IN KNOWLEDGE BASE
# ======================================
QUICK_KNOWLEDGE = {
    "photosynthesis": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of glucose. The formula is: 6CO2 + 6H2O + light → C6H12O6 + 6O2. It occurs in the chloroplasts of plant cells.",
    "cell": "A cell is the basic unit of life. Animal cells have a nucleus, mitochondria, cell membrane, cytoplasm, and ribosomes. Plant cells also have a cell wall, chloroplasts, and a large vacuole.",
    "mitosis": "Mitosis is cell division that produces two identical daughter cells. Stages: Prophase, Metaphase, Anaphase, Telophase, Cytokinesis (PMATC).",
    "atom": "An atom is the smallest unit of an element. It has a nucleus containing protons and neutrons, with electrons orbiting around it. Protons are positive, neutrons are neutral, electrons are negative.",
    "decimals": "Decimals are numbers that have a whole number part and a fractional part separated by a decimal point. Example: 3.14 means 3 whole and 14 hundredths. You can add, subtract, multiply and divide decimals.",
    "fractions": "A fraction represents part of a whole. It has a numerator (top number) and denominator (bottom number). Example: 3/4 means 3 parts out of 4. To add fractions, make the denominators the same first.",
    "percentage": "A percentage is a number out of 100. To convert a fraction to a percentage, divide and multiply by 100. Example: 3/4 = 0.75 = 75%. To find 20% of 50: 50 × 20/100 = 10.",
    "algebra": "Algebra uses letters (variables) to represent unknown numbers. To solve an equation, do the same operation on both sides. Example: x + 5 = 10, so x = 10 - 5 = 5.",
    "pythagoras": "Pythagoras theorem: In a right-angled triangle, a² + b² = c², where c is the hypotenuse (longest side). Example: if a=3, b=4, then c = √(9+16) = √25 = 5.",
    "gravity": "Gravity is a force that pulls objects toward each other. On Earth, gravity pulls things downward at 9.8 m/s². The formula is F = mg, where m is mass and g is gravitational acceleration.",
    "newton": "Newton's 3 Laws of Motion: 1) An object stays at rest or in motion unless acted on by a force. 2) Force = Mass × Acceleration (F=ma). 3) Every action has an equal and opposite reaction.",
    "speed": "Speed = Distance ÷ Time. Velocity is speed in a specific direction. Acceleration = Change in Speed ÷ Time. Units: speed in m/s or km/h.",
    "energy": "Energy is the ability to do work. Types: Kinetic (moving), Potential (stored), Thermal (heat), Chemical, Electrical. Energy cannot be created or destroyed, only converted (Law of Conservation of Energy).",
    "periodic table": "The periodic table arranges all chemical elements by atomic number. Elements in the same column (group) have similar properties. Rows are called periods. Metals are on the left, non-metals on the right.",
    "acid": "Acids have a pH below 7 and taste sour. Bases have a pH above 7. pH 7 is neutral (pure water). Acids and bases neutralise each other to form salt and water.",
    "water cycle": "The water cycle: Evaporation (water turns to vapour) → Condensation (vapour forms clouds) → Precipitation (rain/snow falls) → Collection (water gathers in rivers/oceans) → repeat.",
    "solar system": "The solar system has 8 planets orbiting the Sun: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune. The Sun is a star. Earth is the only known planet with life.",
    "ecosystem": "An ecosystem is all living and non-living things in an area. Food chains show who eats who: Producer → Primary Consumer → Secondary Consumer → Tertiary Consumer.",
    "sound": "Sound is a form of energy that travels as waves through a medium (solid, liquid, or gas). It is caused by vibrations. Sound travels fastest in solids and slowest in gases. The speed of sound in air is about 343 m/s. Frequency is measured in Hertz (Hz) and determines pitch. Amplitude determines loudness.",
    "light": "Light is a form of electromagnetic radiation that travels at 300,000 km/s in a vacuum. It can be reflected, refracted, and absorbed. White light is made up of all colours of the spectrum (ROYGBIV). Light travels in straight lines.",
    "magnetism": "Magnets have a north and south pole. Like poles repel, opposite poles attract. The Earth acts like a giant magnet. Magnetic fields are shown by field lines going from north to south.",
    "electricity": "Electric current is the flow of electrons. Voltage (V) is the push, Current (I) is the flow, Resistance (R) is opposition. Ohm's Law: V = IR. Series circuits have one path; parallel circuits have multiple paths.",
    "world war 2": "World War 2 lasted from 1939 to 1945. It was fought between the Allies (UK, USA, USSR, France) and the Axis powers (Germany, Italy, Japan). It ended with Germany's surrender in May 1945 and Japan's in September 1945.",
    "democracy": "Democracy is a system of government where citizens vote to elect their leaders. Types include direct democracy (citizens vote on every issue) and representative democracy (citizens elect representatives).",
    "continent": "There are 7 continents: Africa, Antarctica, Asia, Australia/Oceania, Europe, North America, South America. Asia is the largest. Australia is the smallest.",
    "adjective": "An adjective describes a noun. Examples: big, small, happy, blue. Comparative adjectives compare two things (bigger, smaller). Superlative adjectives compare three or more (biggest, smallest).",
    "verb": "A verb is an action or state word. Examples: run, jump, is, was. Tenses: past (ran), present (run/runs), future (will run).",
    "shakespeare": "William Shakespeare (1564–1616) was an English playwright and poet. Famous works: Romeo and Juliet, Hamlet, Macbeth, A Midsummer Night's Dream. He wrote 37 plays and 154 sonnets.",
    "osmosis": "Osmosis is the movement of water molecules from a high concentration to a low concentration through a semi-permeable membrane. It is a type of passive transport requiring no energy.",
    "diffusion": "Diffusion is the movement of particles from an area of high concentration to low concentration. It requires no energy (passive process). Examples: oxygen entering blood, smell spreading in a room.",
    "respiration": "Cellular respiration releases energy from glucose. Aerobic: C6H12O6 + 6O2 → 6CO2 + 6H2O + energy (ATP). Anaerobic (no oxygen): glucose → lactic acid + energy (in animals) or ethanol + CO2 (in yeast).",
    "dna": "DNA (Deoxyribonucleic Acid) carries genetic information. It is a double helix made of nucleotides. Base pairs: Adenine-Thymine, Cytosine-Guanine. DNA is found in the nucleus of cells.",
    "evolution": "Evolution is the change in species over time through natural selection. Organisms with favorable traits survive and reproduce more. Charles Darwin proposed the theory of evolution.",
    "plate tectonics": "The Earth's crust is made of plates that move slowly. When plates collide, mountains form. When they separate, rift valleys form. Earthquakes and volcanoes occur at plate boundaries.",
    "climate change": "Climate change refers to long-term shifts in temperatures and weather patterns. Human activities like burning fossil fuels release CO2, which traps heat in the atmosphere (greenhouse effect), causing global warming.",
    "area": "Area formulas: Rectangle = length × width. Triangle = ½ × base × height. Circle = π × r². Parallelogram = base × height. Units are squared (cm², m²).",
    "volume": "Volume formulas: Cuboid = length × width × height. Cylinder = π × r² × h. Sphere = 4/3 × π × r³. Units are cubed (cm³, m³).",
    "ratio": "A ratio compares two quantities. Example: 3:2 means for every 3 of one thing there are 2 of another. To simplify, divide both by the highest common factor.",
    "probability": "Probability = number of favourable outcomes ÷ total outcomes. It ranges from 0 (impossible) to 1 (certain). Example: probability of rolling a 3 on a die = 1/6.",
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
def get_gemini_keys():
    keys = []
    i = 1
    while True:
        key = st.secrets.get(f"GEMINI_API_KEY_{i}")
        if not key:
            break
        keys.append(key)
        i += 1
    single = st.secrets.get("GEMINI_API_KEY")
    if single and single not in keys:
        keys.append(single)
    return keys

def get_openai_keys():
    keys = []
    i = 1
    while True:
        key = st.secrets.get(f"OPENAI_API_KEY_{i}")
        if not key:
            break
        keys.append(key)
        i += 1
    single = st.secrets.get("OPENAI_API_KEY")
    if single and single not in keys:
        keys.append(single)
    return keys

GEMINI_KEYS = get_gemini_keys()
OPENAI_KEYS = get_openai_keys()
ALL_PROVIDERS = []

for k in GEMINI_KEYS:
    ALL_PROVIDERS.append({"provider": "gemini", "key": k})
for k in OPENAI_KEYS:
    ALL_PROVIDERS.append({"provider": "openai", "key": k})

if not ALL_PROVIDERS:
    st.error("No API keys found. Add Gemini or OpenAI keys to Streamlit Secrets.")
    st.stop()

def get_next_provider():
    if "provider_index" not in st.session_state:
        st.session_state.provider_index = 0
    p = ALL_PROVIDERS[st.session_state.provider_index % len(ALL_PROVIDERS)]
    st.session_state.provider_index += 1
    return p

# ======================================
# PDF INDEXING WITH CACHE
# ======================================
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    return text

def get_pdf_hash():
    h = hashlib.md5()
    for f in sorted(os.listdir(PDF_FOLDER)):
        if f.lower().endswith(".pdf"):
            h.update(f.encode())
            h.update(str(os.path.getmtime(
                os.path.join(PDF_FOLDER, f))).encode())
    return h.hexdigest()

def load_single_pdf(file):
    pages = []
    try:
        path = os.path.join(PDF_FOLDER, file)
        reader = PdfReader(path)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 20:
                pages.append({
                    "file": file,
                    "page": page_num + 1,
                    "text": text,
                    "clean": clean_text(text)
                })
    except Exception as e:
        print(f"Error loading {file}: {e}")
    return pages

@st.cache_resource
def load_and_index_books():
    if not os.path.exists(PDF_FOLDER):
        return []

    cache_file = "book_index.pkl"
    hash_file = "book_hash.txt"
    current_hash = get_pdf_hash()

    # Load from disk cache if PDFs haven't changed
    if os.path.exists(cache_file) and os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            saved_hash = f.read()
        if saved_hash == current_hash:
            with open(cache_file, "rb") as f:
                return pickle.load(f)

    # Re-index in parallel
    pdf_files = [f for f in os.listdir(PDF_FOLDER)
                 if f.lower().endswith(".pdf")]
    all_pages = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(load_single_pdf, f): f
                   for f in pdf_files}
        for future in as_completed(futures):
            all_pages.extend(future.result())

    # Save to disk
    with open(cache_file, "wb") as f:
        pickle.dump(all_pages, f)
    with open(hash_file, "w") as f:
        f.write(current_hash)

    return all_pages

with st.spinner("Initializing library... Please wait"):
    books = load_and_index_books()

# ======================================
# SEARCH
# ======================================
def search_library_chunk(question, chunk):
    words = clean_text(question).split()
    stopwords = {
        "what","is","are","how","why","when","who","the","a","an",
        "of","in","to","and","does","do","explain","define","tell",
        "me","about","give","can","you","please","describe","mean",
        "means","meaning","example","examples","write"
    }
    words = [w for w in words if w not in stopwords]
    if not words:
        return None, 0
    best_page = None
    best_score = 0
    for page in chunk:
        score = sum(page["clean"].count(word) for word in words)
        if score > best_score:
            best_score = score
            best_page = page
    return best_page, best_score

# ======================================
# ASK SINGLE PROVIDER
# ======================================
def ask_single_provider(prompt, provider):
    try:
        if provider["provider"] == "gemini":
            genai.configure(api_key=provider["key"])
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            return response.text
        else:
            client = openai.OpenAI(api_key=provider["key"])
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content
    except Exception as e:
        err = str(e)
        if "429" in err or "rate" in err.lower() or "quota" in err.lower():
            return None
        return f"AI Error: {err}"

# ======================================
# PARALLEL AI — all providers at once
# ======================================
def ask_ai_parallel(question, fallback_context=""):
    if not ALL_PROVIDERS:
        return "No API keys available."

    if len(ALL_PROVIDERS) == 1:
        provider = ALL_PROVIDERS[0]
        best_page, score = search_library_chunk(question, books)
        ctx = best_page["text"][:3000] if best_page and score >= 2 \
            else fallback_context
        prompt = f"""
You are MentorLoop Smart Study AI, a helpful tutor for students.
Answer the question clearly and simply.
Use the content below if relevant, otherwise use general knowledge.

CONTENT:
{ctx}

QUESTION:
{question}
"""
        result = ask_single_provider(prompt, provider)
        return result or "Provider busy. Please try again."

    # Split library into chunks — one per provider
    num_workers = len(ALL_PROVIDERS)
    chunk_size = max(1, len(books) // num_workers)
    chunks = [books[i:i + chunk_size]
              for i in range(0, len(books), chunk_size)]

    # Pad chunks list if fewer chunks than providers
    while len(chunks) < num_workers:
        chunks.append([])

    def worker(provider, chunk):
        best_page, score = search_library_chunk(question, chunk)
        if best_page and score >= 2:
            ctx = best_page["text"][:2000]
            source = f"{best_page['file']} Page {best_page['page']}"
        else:
            ctx = fallback_context[:2000]
            source = "general knowledge"

        prompt = f"""
You are MentorLoop Smart Study AI.
Answer this student question clearly and simply using the content below.
Give a clear, concise answer in 3-5 sentences.

CONTENT:
{ctx}

QUESTION:
{question}
"""
        answer = ask_single_provider(prompt, provider)
        return {
            "answer": answer,
            "source": source,
            "score": score,
            "provider": provider["provider"]
        }

    # Run all workers simultaneously
    results = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(worker, ALL_PROVIDERS[i], chunks[i])
            for i in range(num_workers)
        ]
        for future in as_completed(futures):
            result = future.result()
            if result["answer"] and not result["answer"].startswith("AI Error"):
                results.append(result)

    if not results:
        # All failed — wait and try once more with first provider
        time.sleep(15)
        provider = ALL_PROVIDERS[0]
        best_page, score = search_library_chunk(question, books)
        ctx = best_page["text"][:3000] if best_page and score >= 2 \
            else fallback_context
        prompt = f"""
You are MentorLoop Smart Study AI.
Answer this student question clearly and simply.

CONTENT:
{ctx}

QUESTION:
{question}
"""
        result = ask_single_provider(prompt, provider)
        return result or "All providers busy. Please try again in a minute."

    # Only one result — return directly
    if len(results) == 1:
        return results[0]["answer"]

    # Multiple results — master combines them
    combined = "\n\n".join([
        f"Source {i+1} ({r['source']}):\n{r['answer']}"
        for i, r in enumerate(results)
    ])

    master_prompt = f"""
You are MentorLoop Smart Study AI.
Multiple sources answered a student's question.
Combine them into ONE clear, accurate, simple answer.
Remove repetition. Keep it easy to understand for a student.
Do not mention "sources" or "source 1/2/3" in your answer.
Just give the final clean answer directly.

STUDENT QUESTION:
{question}

ANSWERS TO COMBINE:
{combined}

Final combined answer:
"""

    # Try each provider as master until one works
    for provider in ALL_PROVIDERS:
        final = ask_single_provider(master_prompt, provider)
        if final and not final.startswith("AI Error"):
            return final

    # Master failed — return best individual answer
    best = max(results, key=lambda r: r["score"])
    return best["answer"]

# ======================================
# UI
# ======================================
st.title("📚 MentorLoop Smart Study AI")
st.markdown(
    f"**Library Status:** {len(books)} pages indexed from pre-loaded textbooks."
)

query = st.text_input(
    "What would you like to learn today?",
    placeholder="e.g., What is sound?"
)

if st.button("Search Library"):
    if not query.strip():
        st.warning("Please enter a question.")
    else:
        # Step 1: Built-in knowledge — instant, no API
        quick = get_quick_answer(query)
        if quick:
            st.subheader("Answer")
            st.write(quick)
            st.caption("Answered from built-in knowledge base")
        else:
            # Step 2: All AIs search in parallel
            with st.spinner("All AIs scanning textbooks simultaneously..."):
                answer = ask_ai_parallel(query)
            st.subheader("Answer")
            st.write(answer)
