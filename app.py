import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
import openai
import wikipedia
import os
import time, random
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="SmartLoop AI", layout="wide")

# ===============================
# 🎨 UI
# ===============================
st.markdown("""
<style>
.stApp {
    background: radial-gradient(800px circle at 50% 0%, rgba(0,212,255,0.10), rgba(0,212,255,0.00) 60%), #0a0a1a !important;
    color: #f5f5f7 !important;
}
.card {
    background: rgba(255,255,255,0.05);
    border-radius: 20px;
    padding: 20px;
}
</style>
""", unsafe_allow_html=True)

st.title("🧠 SmartLoop AI")
st.caption("Use Subject: Question for best results")

# ===============================
# 🔑 KEYS
# ===============================
def get_keys(prefix):
    keys=[]
    i=1
    while True:
        k=st.secrets.get(f"{prefix}_{i}")
        if not k: break
        keys.append(k)
        i+=1
    single=st.secrets.get(prefix)
    if single: keys.append(single)
    return keys

GEMINI_KEYS = get_keys("GEMINI_API_KEY")
OPENAI_KEYS = get_keys("OPENAI_API_KEY")

# ===============================
# ⚡ CACHE
# ===============================
if "cache" not in st.session_state:
    st.session_state.cache = {}

def cache_get(k):
    return st.session_state.cache.get(k)

def cache_set(k,v):
    st.session_state.cache[k]=v

# ===============================
# ⏱ RATE LIMIT TRACKER
# ===============================
if "rl" not in st.session_state:
    st.session_state.rl={}

def allow_request(key,limit=30):
    now=time.time()
    arr=st.session_state.rl.setdefault(key,[])
    arr=[t for t in arr if now-t<60]
    st.session_state.rl[key]=arr
    if len(arr)>=limit:
        return False
    arr.append(now)
    return True

def pick(keys):
    return random.choice(keys) if keys else None

# ===============================
# 🔁 RETRY
# ===============================
def retry(fn):
    delay=1
    for _ in range(3):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e):
                time.sleep(delay+random.random())
                delay*=2
            else:
                break
    return None

# ===============================
# 🤖 AI CALLS
# ===============================
def ask_gemini(q):
    if not GEMINI_KEYS: return None
    def call():
        k=pick(GEMINI_KEYS)
        if not allow_request(k): raise Exception("429")
        genai.configure(api_key=k)
        m=genai.GenerativeModel("gemini-1.5-flash")
        return m.generate_content(q).text
    return retry(call)

def ask_openai(q):
    if not OPENAI_KEYS: return None
    def call():
        k=pick(OPENAI_KEYS)
        if not allow_request(k): raise Exception("429")
        client=openai.OpenAI(api_key=k)
        r=client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":q}],
            max_tokens=400
        )
        return r.choices[0].message.content
    return retry(call)

# ===============================
# 🌐 WIKI
# ===============================
def wiki(q):
    try:
        return wikipedia.summary(q[:60], sentences=2)
    except:
        return None

# ===============================
# 📚 PDF MEMORY
# ===============================
@st.cache_resource
def load_pdfs():
    data=[]
    for f in os.listdir("."):
        if f.endswith(".pdf"):
            try:
                r=PdfReader(f)
                for p in r.pages:
                    t=p.extract_text()
                    if t:
                        data.append({"text":t[:1500],"file":f})
            except:
                pass
    return data

books=load_pdfs()

def search_pdf(q):
    if not books: return None
    words=set(q.lower().split())
    best=None
    score=0
    for b in books:
        s=sum(1 for w in words if w in b["text"].lower())
        if s>score:
            score=s
            best=b
    return best if score>1 else None

# ===============================
# 🧠 CORE AI
# ===============================
def ask_ai(q):
    # cache
    if q in st.session_state.cache:
        return st.session_state.cache[q]

    # try Gemini
    res=ask_gemini(q)
    if res:
        cache_set(q,res)
        return res

    # try OpenAI
    res=ask_openai(q)
    if res:
        cache_set(q,res)
        return res

    # wiki fallback
    res=wiki(q)
    if res:
        cache_set(q,res)
        return res

    return "⚡ Thinking... refining answer..."

# ===============================
# 🧠 ANSWER ENGINE
# ===============================
def get_answer(q):

    if ":" in q:
        _,q=q.split(":",1)

    # PDF FIRST
    pdf=search_pdf(q)
    if pdf:
        prompt=f"Use this:\n{pdf['text']}\n\nQ:{q}"
        ans=ask_ai(prompt)
        return ans, f"📖 {pdf['file']}"

    # AI
    ans=ask_ai(q)
    return ans, "💡 AI"

# ===============================
# 💬 UI
# ===============================
if "msgs" not in st.session_state:
    st.session_state.msgs=[]

for m in st.session_state.msgs:
    with st.chat_message(m["role"]):
        st.write(m["content"])

q=st.chat_input("Ask anything...")

if q:
    st.session_state.msgs.append({"role":"user","content":q})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            ans,src=get_answer(q)
        st.write(ans)
        st.caption(src)

    st.session_state.msgs.append({"role":"assistant","content":ans})
