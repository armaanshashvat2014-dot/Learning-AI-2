import streamlit as st
import random, re, itertools

# =========================
# API SETUP
# =========================
from google import genai
from openai import OpenAI

GOOGLE_KEYS = [
    st.secrets["GOOGLE_API_KEY_1"],
    st.secrets["GOOGLE_API_KEY_2"]
]

OPENAI_KEYS = [
    st.secrets["OPENAI_API_KEY_1"],
    st.secrets["OPENAI_API_KEY_2"]
]

google_cycle = itertools.cycle(GOOGLE_KEYS)
openai_cycle = itertools.cycle(OPENAI_KEYS)

def get_google():
    return genai.Client(api_key=next(google_cycle))

def get_openai():
    return OpenAI(api_key=next(openai_cycle))

# =========================
# AI ANSWER
# =========================
def ai_answer(q):
    prompt = f"""
    Explain like a teacher:
    Topic: {q}

    Include:
    - Definition
    - Explanation
    - Example
    """

    # Google first
    for _ in range(2):
        try:
            c = get_google()
            r = c.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if r.text:
                return r.text
        except:
            pass

    # OpenAI fallback
    for _ in range(2):
        try:
            c = get_openai()
            r = c.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
        except:
            pass

    return "AI busy."

# =========================
# SUBJECT DETECTION
# =========================
def detect_subject(q):
    q=q.lower()

    if any(x in q for x in ["force","energy","cell","atom","gravity","physics","chemistry","biology"]):
        return "science"

    if any(x in q for x in ["noun","verb","grammar","sentence","adjective"]):
        return "english"

    return "math"

# =========================
# MATH ENGINE
# =========================
def solve_math(q):
    try:
        return str(eval(q.replace("^","**"),{"__builtins__":None},{}))
    except:
        return None

def is_math(q):
    return bool(re.search(r"[0-9\+\-\*/\^()]", q))

# =========================
# MATH GENERATOR (TOPIC BASED)
# =========================
def gen_math(topic, mode):

    topic = topic.lower()
    qs = []
    n = {"Quiz Mode":5,"Test Mode":6}.get(mode,4)

    for _ in range(n):

        # 🔥 INDICES
        if "indice" in topic or "power" in topic:
            a = random.randint(2,10)
            b = random.randint(2,4)
            qs.append(f"{a}^{b}")

        # 🔥 BODMAS
        elif "bodmas" in topic or "order" in topic:
            a,b,c = random.randint(1,10), random.randint(1,10), random.randint(1,10)
            qs.append(f"({a} + {b}) * {c}")

        # 🔥 FRACTIONS
        elif "fraction" in topic:
            a,b = random.randint(1,9), random.randint(1,9)
            c,d = random.randint(1,9), random.randint(1,9)
            qs.append(f"{a}/{b} + {c}/{d}")

        # 🔥 ALGEBRA
        elif "algebra" in topic:
            x = random.randint(1,10)
            qs.append(f"Solve: x + {x} = {x+5}")

        # 🔥 DEFAULT → MIX
        else:
            a = random.randint(1,10)
            b = random.randint(2,5)
            c = random.randint(2,3)
            qs.append(f"{a} + {b}^{c}")

    return qs

# =========================
# SCIENCE GENERATOR
# =========================
def gen_science(topic):
    return [
        f"What is {topic}?",
        f"Why is {topic} important?",
        f"How does {topic} work?",
        f"Who discovered {topic}?",
        f"When is {topic} used?"
    ]

# =========================
# ENGLISH GENERATOR (FIXED)
# =========================
def gen_english(topic):
    return [
        f"What is {topic}?",
        f"How do you use {topic} in a sentence?",
        f"Why is {topic} important in language?"
    ]

# =========================
# GENERATE QUESTIONS
# =========================
def generate_questions(q, mode):

    sub = detect_subject(q)

    if sub == "science":
        return gen_science(q)

    if sub == "english":
        return gen_english(q)

    return gen_math(q, mode)

# =========================
# CHECK ANSWERS
# =========================
def check(user, correct):

    if not user:
        return False, "No answer"

    if correct:
        if user.strip() == correct:
            return True, "Correct"
        return False, f"Wrong. Answer: {correct}"

    if len(user) > 5:
        return True, "Good answer"

    return False, "Too short"

# =========================
# UI
# =========================
st.title("🧠 SmartLoop AI")

mode = st.sidebar.selectbox(
    "Mode",
    ["Tutor Mode","Teacher Mode","Quiz Mode","Test Mode"]
)

q = st.text_input("Enter topic")

if q:

    # Tutor
    if mode=="Tutor Mode":
        if is_math(q):
            st.write("🧮 Answer:", solve_math(q))
        else:
            st.write(ai_answer(q))

    # Teacher
    elif mode=="Teacher Mode":
        st.write(ai_answer(q))

    # Quiz
    elif mode=="Quiz Mode":
        st.subheader("📝 Quiz")
        for ques in generate_questions(q,mode):
            st.write("•", ques)

    # Test
    elif mode=="Test Mode":

        if "start" not in st.session_state:
            st.session_state.start=False

        if not st.session_state.start:
            if st.button("Start Test"):
                st.session_state.start=True
                st.session_state.qs=generate_questions(q,mode)
                st.session_state.ans=[""]*len(st.session_state.qs)

        if st.session_state.start:

            for i,ques in enumerate(st.session_state.qs):
                st.session_state.ans[i]=st.text_input(f"Q{i+1}. {ques}",key=i)

            if st.button("Submit"):

                score=0
                st.subheader("📊 Feedback")

                for i,ques in enumerate(st.session_state.qs):

                    correct = solve_math(ques) if is_math(ques) else None
                    ok,msg = check(st.session_state.ans[i],correct)

                    if ok:
                        score+=1

                    st.write(f"Q{i+1}: {ques}")
                    st.write("Your:", st.session_state.ans[i])
                    st.write(msg)
                    st.write("---")

                st.write(f"🎯 Score: {score}/{len(st.session_state.qs)}")
                st.session_state.start=False
