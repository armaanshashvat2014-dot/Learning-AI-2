import streamlit as st
import time
import re
import json
from google import genai

# ----------------------------- #
# CONFIG
# ----------------------------- #
st.set_page_config(page_title="helix.ai Tutor", page_icon="📚")

API_KEY = "AIzaSyBbNzWNCgD3RXZ25dKVdnDMxpjGjqbQ4rs"

client = genai.Client(api_key=API_KEY)

# ----------------------------- #
# SESSION STATE
# ----------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 I'm Helix! Ask me anything."}
    ]

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False

if "answered" not in st.session_state:
    st.session_state.answered = False

# ----------------------------- #
# AI FUNCTION (NEW SDK)
# ----------------------------- #
def get_ai_response(prompt):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text if response.text else "No response."

    except Exception as e:
        return f"⚠️ Error: {e}"

# ----------------------------- #
# LOGIN
# ----------------------------- #
if st.session_state.user_data is None:
    st.title("🚀 helix.ai")

    name = st.text_input("Name")
    email = st.text_input("Email")
    grade = st.selectbox("Grade", ["Grade 6","Grade 7","Grade 8"])

    if st.button("Start Learning"):
        if name and email:
            st.session_state.user_data = {
                "name": name,
                "email": email,
                "grade": grade
            }
            st.rerun()
        else:
            st.warning("Enter all fields")

    st.stop()

# ----------------------------- #
# SIDEBAR
# ----------------------------- #
with st.sidebar:
    st.write(f"👤 {st.session_state.user_data['name']}")
    mode = st.radio("Mode", ["Tutor","Quiz"])

    if st.button("Logout"):
        st.session_state.user_data = None
        st.rerun()

# ----------------------------- #
# TUTOR MODE
# ----------------------------- #
if mode == "Tutor":

    st.title("📚 AI Tutor")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask something"):
        st.session_state.messages.append({"role":"user","content":prompt})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_ai_response(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role":"assistant","content":response})

# ----------------------------- #
# QUIZ MODE
# ----------------------------- #
else:

    st.title("⚡ Quiz Mode")

    if not st.session_state.quiz_active:

        subject = st.selectbox("Subject",["Math","Science","English"])
        num = st.slider("Questions",3,10,5)
        topic = st.text_input("Topic")

        if st.button("Generate Quiz"):
            with st.spinner("Generating..."):

                prompt = f"""
Create {num} {subject} questions on {topic}.

Return ONLY JSON:
[
{{
"question":"",
"options":["A","B","C","D"],
"correct_answer":"A"
}}
]
"""

                raw = get_ai_response(prompt)
                clean = re.sub(r'```json|```', '', raw).strip()

                try:
                    data = json.loads(clean)

                    st.session_state.quiz_questions = data
                    st.session_state.quiz_score = 0
                    st.session_state.current_q_idx = 0
                    st.session_state.quiz_active = True
                    st.session_state.answered = False
                    st.rerun()

                except:
                    st.error("Quiz failed. Try again.")

    else:

        q = st.session_state.quiz_questions
        i = st.session_state.current_q_idx

        if i < len(q):

            st.subheader(f"Q{i+1}")
            st.write(q[i]["question"])

            for opt in q[i]["options"]:
                if st.button(opt) and not st.session_state.answered:

                    st.session_state.answered = True

                    if opt == q[i]["correct_answer"]:
                        st.success("Correct!")
                        st.session_state.quiz_score += 1
                    else:
                        st.error(f"Wrong. Correct: {q[i]['correct_answer']}")

                    time.sleep(1)
                    st.session_state.current_q_idx += 1
                    st.session_state.answered = False
                    st.rerun()

        else:
            st.success(f"Score: {st.session_state.quiz_score}/{len(q)}")

            if st.button("New Quiz"):
                st.session_state.quiz_active = False
                st.rerun()
