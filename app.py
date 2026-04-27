import streamlit as st
import itertools, re, wikipedia, feedparser, json, uuid

from google import genai
from openai import OpenAI

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SmartLoop AI",
    page_icon="🧠",
    layout="wide"
)

# =========================
# API SETUP
# =========================
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
# SESSION STATE
# =========================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"
if "last_q" not in st.session_state:
    st.session_state.last_q = ""
if "active_grade" not in st.session_state:
    st.session_state.active_grade = "Grade 6"

# =========================
# CSS
# =========================
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
    -webkit-backdrop-filter: blur(40px) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stForm"],
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.04) !important;
    backdrop-filter: blur(40px) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 24px !important;
    padding: 20px !important;
    margin: 10px 0 !important;
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
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.04);
    border-radius: 14px;
    margin: 8px 0;
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
.beta-badge {
    display: inline-block;
    background: linear-gradient(135deg, #ff4d6d, #7b2ff7);
    color: white;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
    box-shadow: 0 0 12px rgba(255,77,109,0.5);
    vertical-align: middle;
    margin-left: 10px;
}
.section-label {
    color: #00d4ff;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 12px 0 6px;
}
.welcome-card {
    background: linear-gradient(135deg,
        rgba(0,212,255,0.12), rgba(123,47,247,0.08));
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-weight: 600;
    color: #2ecc71;
    font-size: 14px;
}
.tier-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 6px;
}
.tier-calc { background:rgba(155,89,182,0.2); color:#9b59b6; border:1px solid rgba(155,89,182,0.4); }
.tier-wiki { background:rgba(52,152,219,0.15); color:#3498db; border:1px solid rgba(52,152,219,0.3); }
.tier-news { background:rgba(46,204,113,0.15); color:#2ecc71; border:1px solid rgba(46,204,113,0.3); }
.tier-ai   { background:rgba(252,132,4,0.15);  color:#fc8404; border:1px solid rgba(252,132,4,0.3); }
</style>
""", unsafe_allow_html=True)

# =========================
# SAFETY
# =========================
def is_safe(q):
    prompt = f"Return ONLY one word — true if safe, false if unsafe:\n{q}"
    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )
        return "true" in r.text.lower()
    except:
        pass
    try:
        c = get_openai()
        r = c.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=5
        )
        return "true" in r.choices[0].message.content.lower()
    except:
        pass
    return True

# =========================
# MATH SOLVER
# =========================
def extract_math(q):
    matches = re.findall(r"[0-9\+\-\*/\^\(\)\[\]\{\}\.]+", q)
    expr = "".join(matches)
    if not expr:
        return None
    expr = (expr
            .replace("[","(").replace("]",")")
            .replace("{","(").replace("}",")")
            .replace("^","**"))
    return expr

def solve_math_steps(q):
    expr = extract_math(q)
    if not expr:
        return None
    try:
        original = expr.replace("**","^")
        steps = [f"Expression: {original}"]
        working = expr
        if "(" in working:
            inner = re.findall(r"\([^()]+\)", working)
            for part in inner:
                val = eval(part, {"__builtins__":None}, {})
                steps.append(f"Solve {part} → {val}")
                working = working.replace(part, str(val), 1)
        if "**" in working:
            for p in re.findall(r"\d+\*\*\d+", working):
                val = eval(p, {"__builtins__":None}, {})
                steps.append(f"{p.replace('**','^')} = {val}")
                working = working.replace(p, str(val), 1)
        for m in re.findall(r"\d+[\*/]\d+", working):
            val = eval(m, {"__builtins__":None}, {})
            steps.append(f"{m} = {val}")
            working = working.replace(m, str(val), 1)
        result = eval(working, {"__builtins__":None}, {})
        steps.append(f"**Final Answer: {result}**")
        return "🧮 **Step-by-step:**\n\n" + "\n\n".join(steps)
    except:
        return None

# =========================
# NEWS
# =========================
def is_news_query(q):
    return any(w in q.lower() for w in [
        "news","latest","headlines","current events","today"
    ])

def get_global_news():
    feeds = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "http://feeds.reuters.com/reuters/topNews",
        "http://rss.cnn.com/rss/edition.rss",
        "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
    ]
    headlines = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                headlines.append(f"• {entry.title}")
        except:
            continue
    if not headlines:
        return "Could not fetch news right now. Please try again."
    return "📰 **Latest Headlines:**\n\n" + "\n".join(headlines[:10])

# =========================
# WIKIPEDIA
# =========================
def search_wiki(q):
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

# =========================
# MAIN AI ANSWER
# =========================
def ai_answer(q, grade, history):
    if not is_safe(q):
        return "⚠️ I can't help with that.", ""

    if is_news_query(q):
        return get_global_news(), "news"

    math = solve_math_steps(q)
    if math:
        return math, "calc"

    history_text = ""
    if history:
        for msg in history[-6:]:
            role = "Student" if msg["role"] == "user" else "SmartLoop"
            history_text += f"{role}: {msg.get('content','')}\n"

    prompt = f"""
You are SmartLoop AI — a smart, concise tutor.
The student is in {grade}. Adjust your language and complexity accordingly.
Grade 1-3: very simple words, short sentences, fun examples.
Grade 4-6: clear simple explanations, relatable examples.
Grade 7-10: more detailed, academic language appropriate for the level.
Answer clearly and accurately. Use bullet points or short paragraphs.
Never write more than needed.

Previous conversation:
{history_text}

Student's question: {q}
"""

    try:
        c = get_google()
        r = c.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )
        if r.text:
            return r.text, "ai"
    except:
        pass

    try:
        c = get_openai()
        msgs = [{
            "role": "system",
            "content": (
                f"You are SmartLoop AI, a concise tutor. "
                f"The student is in {grade}. "
                f"Adjust complexity for their grade level. "
                f"Answer clearly and simply."
            )
        }]
        if history:
            for msg in history[-6:]:
                msgs.append({
                    "role": msg["role"],
                    "content": msg.get("content","")
                })
        msgs.append({"role":"user","content":q})
        r = c.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=msgs,
            max_tokens=600
        )
        return r.choices[0].message.content, "ai"
    except:
        pass

    wiki = search_wiki(q)
    if wiki:
        return "🌐 " + wiki, "wiki"

    return "⚠️ Could not find an answer. Please rephrase.", ""

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(
        "<div class='welcome-card'>👋 Welcome back, Student!</div>",
        unsafe_allow_html=True
    )

    st.button("👤 My Account", use_container_width=True)
    st.button("🚪 Log out", use_container_width=True)

    st.divider()

    st.markdown(
        "<div class='section-label'>🎯 Active Grade</div>",
        unsafe_allow_html=True
    )
    st.session_state.active_grade = st.selectbox(
        "Grade",
        [f"Grade {i}" for i in range(1, 11)],
        index=5,  # defaults to Grade 6
        label_visibility="collapsed"
    )

    st.divider()

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()

    st.markdown(
        "<div class='section-label'>💬 Chats</div>",
        unsafe_allow_html=True
    )

    for chat_name in list(reversed(list(
        st.session_state.chats.keys()
    ))):
        is_active = (chat_name == st.session_state.current_chat)
        col1, col2 = st.columns([0.82, 0.18],
                                  vertical_alignment="center")
        msgs = st.session_state.chats.get(chat_name, [])
        first_user = next(
            (m["content"] for m in msgs if m["role"] == "user"),
            chat_name
        )
        title = (
            first_user[:22] + "..."
            if len(first_user) > 22
            else first_user
        )
        label = f"{'🟢' if is_active else '💬'} {title}"

        if col1.button(
            label,
            key=f"ch_{chat_name}",
            use_container_width=True
        ):
            st.session_state.current_chat = chat_name
            st.rerun()

        if col2.button(
            "🗑", key=f"dl_{chat_name}",
            use_container_width=True
        ):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[chat_name]
                if st.session_state.current_chat == chat_name:
                    st.session_state.current_chat = list(
                        st.session_state.chats.keys()
                    )[0]
                st.rerun()

    st.divider()

    with st.expander("🏫 Are you a Teacher?"):
        st.markdown(
            "<span style='color:#a0a0ab;font-size:13px;'>"
            "Enter your school code to unlock teacher tools."
            "</span>",
            unsafe_allow_html=True
        )
        teacher_code = st.text_input(
            "Code", type="password",
            placeholder="Enter code...",
            label_visibility="collapsed"
        )
        if st.button("Verify", use_container_width=True):
            if teacher_code == st.secrets.get("TEACHER_CODE",""):
                st.success("✅ Teacher access granted!")
            else:
                st.error("Invalid code.")

# =========================
# MAIN CHAT UI
# =========================
st.markdown("""
<div style='text-align:center; padding: 20px 0 8px;'>
    <span style='font-size:44px; font-weight:800; color:#00d4ff;
        letter-spacing:-2px;
        text-shadow: 0 0 16px rgba(0,212,255,0.45);'>
        🧠 SmartLoop AI
    </span>
    <span class='beta-badge'>BETA</span>
</div>
<div style='text-align:center; color:rgba(255,255,255,0.4);
    font-size:15px; margin-bottom:24px;'>
    Your AI Tutor for Grade 1–10
</div>
""", unsafe_allow_html=True)

messages = st.session_state.chats.get(
    st.session_state.current_chat, []
)

if not messages:
    with st.chat_message("assistant"):
        st.markdown(
            "👋 **Hey there! I'm SmartLoop AI!**\n\n"
            "I'm your smart tutor here to help you learn! 📚\n\n"
            "I can:\n"
            "- ✏️ Answer any subject question\n"
            "- 🧮 Solve maths step-by-step\n"
            "- 📰 Fetch the latest news\n"
            "- 💬 Remember our conversation\n\n"
            f"*Currently set to: "
            f"**{st.session_state.active_grade}** — "
            f"you can change this in the sidebar anytime!*"
        )

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content",""))
        tier = msg.get("tier","")
        if tier:
            badge_map = {
                "calc": ("tier-calc","🧮 Calculator"),
                "wiki": ("tier-wiki","🌐 Wikipedia"),
                "news": ("tier-news","📰 News"),
                "ai":   ("tier-ai",  "💡 AI"),
            }
            cls, label = badge_map.get(tier, ("tier-ai","💡 AI"))
            st.markdown(
                f'<span class="tier-badge {cls}">{label}</span>',
                unsafe_allow_html=True
            )

q = st.chat_input("Ask SmartLoop...")

if q and q != st.session_state.last_q:
    st.session_state.last_q = q
    messages = st.session_state.chats[st.session_state.current_chat]
    messages.append({"role":"user","content":q})

    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.markdown("""
<div class="thinking-container">
    <span class="thinking-text">Thinking</span>
    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)

        ans, tier = ai_answer(
            q,
            st.session_state.active_grade,
            messages[:-1]
        )
        thinking.empty()
        st.markdown(ans)

        if tier:
            badge_map = {
                "calc": ("tier-calc","🧮 Calculator"),
                "wiki": ("tier-wiki","🌐 Wikipedia"),
                "news": ("tier-news","📰 News"),
                "ai":   ("tier-ai",  "💡 AI"),
            }
            cls, label = badge_map.get(tier, ("tier-ai","💡 AI"))
            st.markdown(
                f'<span class="tier-badge {cls}">{label}</span>',
                unsafe_allow_html=True
            )

    messages.append({
        "role":    "assistant",
        "content": ans,
        "tier":    tier
    })
