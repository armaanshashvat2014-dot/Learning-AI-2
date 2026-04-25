import streamlit as st
import re, random
from google import genai

# =========================
# API SETUP
# =========================
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

st.title("🧠 SmartLoop AI (Fixed)")

mode = st.sidebar.selectbox(
    "Mode",
    ["Tutor Mode","Teacher Mode","Quiz Mode","Test Mode"]
)

# =========================
# SUBJECT DETECTION (FIXED)
# =========================
def detect_subject(q):
    q=q.lower()

    math_words=["add","subtract","multiply","divide","fraction","decimal","algebra","indices","equation","+","-","*","/","^"]
    science_words=["force","energy","cell","atom","gravity","biology","physics","chemistry"]
    english_words=["noun","verb","grammar","sentence","adjective"]

    scores={"math":0,"science":0,"english":0}

    for w in math_words:
        if w in q: scores["math"]+=2
    for w in science_words:
        if w in q: scores["science"]+=2
    for w in english_words:
        if w in q: scores["english"]+=2

    best=max(scores,key=scores.get)
    return best if scores[best]>0 else "math"

# =========================
# MATH ENGINE (LOCAL)
# =========================
def parse_math(q):
    q=q.lower()
    q=q.replace("plus","+").replace("minus","-")
    q=q.replace("times","*").replace("multiply","*")
    q=q.replace("divide","/")
    q=q.replace("^","**")
    return q

def solve_math(q):
    try:
        return str(eval(parse_math(q),{"__builtins__":None},{}))
    except:
        return None

def is_math(q):
    return bool(re.search(r"[0-9\+\-\*/\^]", q))

# =========================
# AI ANSWER (GEMINI)
# =========================
def ai_answer(q):

    prompt=f"""
    Answer clearly like a teacher.

    Question: {q}

    Rules:
    - Be simple
    - No nonsense
    - No unrelated topics
    """

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return resp.text
    except:
        return "AI error."

# =========================
# QUESTION GENERATORS
# =========================
def gen_math(mode):
    qs=[]
    n={"Teacher Mode":3,"Quiz Mode":5,"Test Mode":6}.get(mode,4)

    for _ in range(n):
        t=random.choice(["basic","power","mix"])

        if t=="basic":
            a,b=random.randint(1,20),random.randint(1,20)
            qs.append(f"{a} + {b}")

        elif t=="power":
            a=random.randint(2,10)
            b=random.randint(2,4)
            qs.append(f"{a}^{b}")

        else:
            a=random.randint(5,20)
            b=random.randint(2,5)
            c=random.randint(2,3)
            qs.append(f"{a} - {b}^{c}")

    return qs

def gen_science(topic):
    return [
        f"What is {topic}?",
        f"Why is {topic} important?",
        f"How does {topic} work?",
        f"Who discovered {topic}?"
    ]

def gen_english(topic):
    return [
        f"What is {topic}?",
        f"Define {topic}",
        f"Use {topic} in a sentence"
    ]

def generate_questions(q,mode):
    sub=detect_subject(q)

    if sub=="math":
        return gen_math(mode)
    if sub=="science":
        return gen_science(q)
    if sub=="english":
        return gen_english(q)

# =========================
# ANSWER CHECKING
# =========================
def check(user,correct):

    if not user:
        return False,"No answer"

    user=user.strip()

    if correct:
        if user==correct:
            return True,"Correct"
        return False,f"Wrong. Answer: {correct}"

    if len(user)>5:
        return True,"Acceptable"

    return False,"Too short"

# =========================
# UI
# =========================
q=st.text_input("Ask or Enter Topic")

if q:

    # Tutor Mode
    if mode=="Tutor Mode":

        if is_math(q):
            st.write("🧮 Answer:",solve_math(q))
        else:
            st.write(ai_answer(q))

    # Teacher Mode
    elif mode=="Teacher Mode":

        st.write(ai_answer(q))

        st.subheader("Practice")
        for x in generate_questions(q,mode):
            st.write("-",x)

    # Quiz Mode
    elif mode=="Quiz Mode":

        st.subheader("Quiz")
        for x in generate_questions(q,mode):
            st.write("•",x)

    # Test Mode
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

                st.subheader("Feedback")

                for i,ques in enumerate(st.session_state.qs):

                    correct = solve_math(ques) if is_math(ques) else None
                    ok,msg=check(st.session_state.ans[i],correct)

                    if ok: score+=1

                    st.write(f"Q{i+1}: {ques}")
                    st.write("Your:",st.session_state.ans[i])
                    st.write(msg)
                    st.write("---")

                st.write(f"🎯 Score: {score}/{len(st.session_state.qs)}")

                st.session_state.start=False
