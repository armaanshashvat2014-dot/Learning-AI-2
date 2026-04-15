import streamlit as st, os, time, re, uuid, json, concurrent.futures, base64
from pathlib import Path
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types
from google.cloud import firestore
from google.oauth2 import service_account
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# -----------------------------
# 1) GLOBAL CONSTANTS & STYLING
# -----------------------------
st.set_page_config(page_title="helix.ai - Cambridge (CIE) Tutor", page_icon="📚", layout="centered")

quiz_bg_state = st.session_state.get("quiz_bg", "default")
if quiz_bg_state == "correct": bg_style = "radial-gradient(circle at 50% 50%, rgba(46, 204, 113, 0.25) 0%, #0a0a1a 80%)"
elif quiz_bg_state == "wrong": bg_style = "radial-gradient(circle at 50% 50%, rgba(231, 76, 60, 0.25) 0%, #0a0a1a 80%)"
else: bg_style = "radial-gradient(800px circle at 50% 0%, rgba(0, 212, 255, 0.12), rgba(0, 212, 255, 0.00) 60%), #0a0a1a"

st.markdown(f"""<style>
.stApp {{ background: {bg_style} !important; transition: background 0.6s ease-in-out; color: #f5f5f7 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important; }}
[data-testid="stSidebar"] {{ background: rgba(25, 25, 35, 0.4) !important; backdrop-filter: blur(40px) !important; border-right: 1px solid rgba(255, 255, 255, 0.08) !important; }}
[data-testid="stForm"],[data-testid="stVerticalBlockBorderWrapper"] {{ background: rgba(255, 255, 255, 0.04) !important; backdrop-filter: blur(40px) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; border-radius: 28px !important; padding: 24px !important; box-shadow: 0 16px 40px 0 rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important; margin: 20px 0 !important; }}
[data-testid="stChatMessage"] {{ background: rgba(255, 255, 255, 0.05) !important; backdrop-filter: blur(24px) !important; border: 1px solid rgba(255, 255, 255, 0.12) !important; border-radius: 28px !important; padding: 20px !important; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important; color: #fff !important; margin-bottom: 16px; }}
[data-testid="stChatMessage"] * {{ color: #f5f5f7 !important; }}
.stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>textarea, .stNumberInput>div>div>input {{ background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 12px !important; color: #fff !important; }} .stChatInputContainer {{ background: transparent !important; }}
.stButton>button {{ background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.02) 100%) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 20px !important; backdrop-filter: blur(20px) !important; color: #fff !important; font-weight: 600 !important; transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important; }}
@media (hover: hover) and (pointer: fine) {{ .stButton>button:hover {{ background: linear-gradient(180deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.05) 100%) !important; border-color: rgba(255,255,255,0.4) !important; transform: translateY(-2px) !important; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important; }} }}
.stButton>button:active {{ transform: translateY(1px) !important; background: rgba(255,255,255,0.2) !important; }}
.thinking-container {{ display: flex; align-items: center; gap: 8px; padding: 12px 16px; background-color: rgba(255,255,255,0.05); border-radius: 16px; margin: 10px 0; border-left: 3px solid #fc8404; backdrop-filter: blur(10px); }} .thinking-text {{ color: #fc8404; font-size: 14px; font-weight: 600; }} .thinking-dots {{ display: flex; gap: 4px; }} .thinking-dot {{ width: 6px; height: 6px; border-radius: 50%; background-color: #fc8404; animation: thinking-pulse 1.4s infinite; }} .thinking-dot:nth-child(2){{animation-delay: 0.2s;}} .thinking-dot:nth-child(3){{animation-delay: 0.4s;}} @keyframes thinking-pulse {{ 0%, 60%, 100% {{ opacity: 0.3; transform: scale(0.8); }} 30% {{ opacity: 1; transform: scale(1.2); }} }}
.big-title {{ font-family: 'Inter', sans-serif; color: #00d4ff; text-align: center; font-size: 48px; font-weight: 1200; letter-spacing: -3px; margin-bottom: 0px; text-shadow: 0 0 12px rgba(0, 212, 255, 0.4); }} .quiz-title {{ font-size: 32px; font-weight: 800; text-align: center; margin-bottom: 20px; }} .quiz-question-text {{ font-size: 28px; font-weight: 700; text-align: center; margin-bottom: 30px; line-height: 1.4; color: #fff; }} .quiz-counter {{ color: #a0a0ab; font-size: 14px; font-weight: 600; margin-bottom: 15px; }}
.glass-container {{ background: rgba(35, 35, 45, 0.4); backdrop-filter: blur(40px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 28px; padding: 24px; margin-bottom: 20px; }} .account-detail {{ font-size: 1.1rem; margin-bottom: 0.5rem; }} .mastery-title {{ font-size: 14px; color: #a0a0ab; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }} .mastery-value {{ font-size: 48px; color: #00d4ff; font-weight: 800; line-height: 1; }} .weak-spot-item {{ background: rgba(231, 76, 60, 0.1); border: 1px solid rgba(231, 76, 60, 0.2); border-radius: 16px; padding: 12px 16px; color: #f5f5f7; font-weight: 500; margin-bottom: 8px; }} .success-item {{ background: rgba(46, 204, 113, 0.1); border: 1px solid rgba(46, 204, 113, 0.2); border-radius: 16px; padding: 12px 16px; color: #f5f5f7; font-weight: 500; }}
[data-testid="stFileUploaderDropzone"] {{ z-index: -1 !important; }}
</style>""", unsafe_allow_html=True)

if "SCHOOL_CODES" in st.secrets: SCHOOL_CODES = dict(st.secrets["SCHOOL_CODES"])
else: SCHOOL_CODES = {}

# -----------------------------
# AI PROMPTS
# -----------------------------
SYSTEM_INSTRUCTION = f"""
You are Helix, an elite Cambridge (CIE) Tutor and Examiner for Grade 6-8 students.
RULE 1: STRICT SCOPE: Restrict ALL answers/questions ONLY to requested chapters. NEVER introduce outside concepts. "Hard" means multi-step reasoning, not outside topics.
RULE 2: Force multi-step reasoning. NEVER reveal the topic in the heading. Tables MUST be Markdown.
RULE 3: ANTI-PLAGIARISM: STRICTLY FORBIDDEN to copy-paste or slightly rephrase textbook questions. Generate 100% NEW/UNIQUE questions.
RULE 4: Use IMAGE_GEN:[Desc] or PIE_CHART:[L:V]. 
RULE 5: TITLE: # Helix A.I.\n## Practice Paper\n###[SUBJECT] - [GRADE]
RULE 6: If asked to evaluate weak points, silently do so. If detected, output at VERY END: ===ANALYTICS_START===\n{{ "subject": "Math", "grade": "Grade 7", "weak_point": "Fractions" }}\n===ANALYTICS_END===
RULE 7: Grade flexibly. SILENTLY solve first. Focus on SEMANTIC CORRECTNESS.
"""

QUIZ_SYSTEM_INSTRUCTION = f"""
You are an AI Quiz Engine. Output a single, raw JSON array of objects. NEVER output conversational text or markdown.
ANTI-PLAGIARISM & STRICT SYLLABUS BOUNDARIES: STRICTLY FORBIDDEN to copy from textbooks. Generate 100% NEW questions. NEVER introduce outside concepts.
JSON ARRAY Structure:[{{ "question": "?", "type": "MCQ", "options":["A", "B", "C", "D"], "correct_answer": "Exact option text", "explanation": "Why" }}]
"""
PAPER_SYSTEM = SYSTEM_INSTRUCTION + "\nCRITICAL FOR PAPERS: DO NOT output the ===ANALYTICS_START=== block. Append[PDF_READY] at the end."

GRADE_TO_STAGE = {"Grade 6": "Stage 7", "Grade 7": "Stage 8", "Grade 8": "Stage 9"}
STAGE_TO_GRADE = {v: k for k, v in GRADE_TO_STAGE.items()}
NUM_WORDS = {"six":"6","seven":"7","eight":"8","nine":"9","vi":"6","vii":"7","viii":"8","ix":"9"}
def normalize_stage_text(s: str) -> str:
    s = (s or "").lower()
    for w, d in NUM_WORDS.items(): s = re.sub(rf"\b{w}\b", d, s)
    return s

# -----------------------------
# AUTH & FIRESTORE
# -----------------------------
if hasattr(st, "user"): auth_object = st.user
elif hasattr(st, "experimental_user"): auth_object = st.experimental_user
else: st.error("Streamlit version too old for Google Login."); st.stop()
is_authenticated = getattr(auth_object, "is_logged_in", False)

@st.cache_resource
def get_firestore_client():
    if "firebase" in st.secrets: return firestore.Client(credentials=service_account.Credentials.from_service_account_info(dict(st.secrets["firebase"])))
    return None
db = get_firestore_client()

def get_student_class_data(student_email):
    if not db: return None
    for c in db.collection("classes").where(filter=firestore.FieldFilter("students", "array_contains", student_email)).limit(1).stream(): return {"id": c.id, **c.to_dict()}
    return None

def get_user_profile(email):
    if not db: return {"role": "student"}
    doc = db.collection("users").document(email).get()
    if doc.exists:
        p = doc.to_dict(); u = False
        if not p.get("display_name") and is_authenticated: p["display_name"] = getattr(auth_object, "name", email.split("@")[0]); u = True
        if p.get("role") == "undefined": p["role"] = "student"; u = True
        if u: db.collection("users").document(email).update(p)
        return p
    else:
        dp = {"role": "student", "teacher_id": None, "display_name": getattr(auth_object, "name", email.split("@")[0]) if is_authenticated else "Guest", "grade": "Grade 6", "school": None}
        db.collection("users").document(email).set(dp); return dp

def create_global_class(class_id, teacher_email, grade, section, school_name):
    clean_id = class_id.strip().upper()
    if not clean_id or not db: return False, "Database error."
    ref = db.collection("classes").document(clean_id)
    @firestore.transactional
    def check_and_create(transaction, r):
        if r.get(transaction=transaction).exists: return False, f"Class '{clean_id}' already exists!"
        transaction.set(r, {"created_by": teacher_email, "created_at": time.time(), "grade": grade, "section": section, "school": school_name, "students":[], "subjects":[]})
        return True, f"Class '{clean_id}' created successfully!"
    return check_and_create(db.transaction(), ref)

user_role = "guest"; user_profile = {} 
if is_authenticated:
    user_email = auth_object.email
    user_profile = get_user_profile(user_email)
    user_role = user_profile.get("role", "student")

@st.cache_data(ttl=600) 
def evaluate_weak_spots(_email): 
    if not db: return [],[]
    t = time.time() - 604800
    ws_ref = db.collection("users").document(_email).collection("weak_spots")
    act, dis = [],[]
    for d in ws_ref.where(filter=firestore.FieldFilter("identified_at", ">", t)).stream():
        v = d.to_dict(); v['id'] = d.id; (dis if v.get("dismissed") else act).append(v)
    rem =[d.to_dict() for d in db.collection("users").document(_email).collection("analytics").where(filter=firestore.FieldFilter("timestamp", ">", t)).stream() if d.to_dict().get("weak_point") and d.to_dict().get("weak_point").lower() != "none"]
    if len(rem) >= 3:
        p = f"Group semantic remarks: {json.dumps(rem)}. Ignore if in {[s.get('topic') for s in act+dis]}. Return ONLY JSON array of NEW distinct objects:[{{\"subject\": \"Math\", \"topic\": \"Fractions\"}}]"
        try:
            r = client.models.generate_content(model="gemini-2.5-flash", contents=p, config=types.GenerateContentConfig(temperature=0.1))
            if m := re.search(r'\[.*\]', safe_response_text(r), re.DOTALL):
                for s in json.loads(m.group(0)):
                    if s.get("topic") and s.get("subject"):
                        nd = ws_ref.add({"topic": s["topic"], "subject": s["subject"], "identified_at": time.time(), "dismissed": False})
                        act.append({"id": nd[1].id, "topic": s["topic"], "subject": s["subject"], "identified_at": time.time(), "dismissed": False})
        except: pass
    return act, dis

def run_quiz_weakpoint_check(history, email, subject):
    if not db: return
    p = f"Review the last 5 {subject} quiz answers:\n{json.dumps(history, indent=2)}\nSpecific recurring weak spot? Return JSON: {{\"weak_point\": \"desc\"}} or {{\"weak_point\": \"None\"}}"
    try:
        r = client.models.generate_content(model="gemini-2.5-flash-lite", contents=p, config=types.GenerateContentConfig(temperature=0.1))
        if m := re.search(r'\{.*\}', safe_response_text(r), re.DOTALL):
            d = json.loads(m.group(0))
            if d.get("weak_point") and d.get("weak_point").lower() != "none":
                db.collection("users").document(email).collection("analytics").add({"timestamp": time.time(), "subject": subject, "weak_point": d["weak_point"], "source": "quiz"})
    except: pass

def get_threads_collection(): return db.collection("users").document(auth_object.email).collection("threads") if is_authenticated and db else None
def get_all_threads():
    try: return[{"id": d.id, **d.to_dict()} for d in get_threads_collection().order_by("updated_at", direction=firestore.Query.DESCENDING).limit(15).stream()] if get_threads_collection() else[]
    except: return[]
def get_default_greeting(): return[{"role": "assistant", "content": "👋 **Hey there! I'm Helix!**\n\nI'm your CIE tutor here to help you ace your CIE exams! 📖\n\nI can answer your doubts, draw diagrams, and create quizzes!\n**Attach photos, PDFs, or text files directly in the chat box below!** 📸📄\n\nWhat are we learning today?", "is_greeting": True}]
def load_chat_history(thread_id):
    c = get_threads_collection()
    if c and thread_id:
        try:
            msgs =[m.to_dict() for m in c.document(thread_id).collection("messages").order_by("idx").stream()]
            if msgs: return msgs
            doc = c.document(thread_id).get()
            if doc.exists and "messages" in doc.to_dict(): return doc.to_dict().get("messages",[])
        except: pass
    return get_default_greeting()
def compress_image_for_db(b: bytes) -> str:
    try:
        if not b: return None
        i = Image.open(BytesIO(b)).convert('RGB'); i.thumbnail((1024, 1024), Image.Resampling.LANCZOS); b_io = BytesIO(); i.save(b_io, format="JPEG", quality=85, optimize=True)
        return base64.b64encode(b_io.getvalue()).decode('utf-8')
    except: return None

def save_chat_history():
    c = get_threads_collection()
    if not c: return
    sm, ds, dg =[], set(), set()
    for msg in st.session_state.get("messages",[]):
        cs, r = str(msg.get("content", "")), msg.get("role")
        if r == "user":
            q = cs.lower()
            if any(k in q for k in["math", "algebra", "geometry", "calculate", "equation", "number", "fraction"]): ds.add("Math")
            if any(k in q for k in["science", "cell", "biology", "physics", "chemistry", "experiment", "gravity"]): ds.add("Science")
            if any(k in q for k in["english", "poem", "story", "essay", "writing", "grammar", "noun", "verb"]): ds.add("English")
            qn = normalize_stage_text(cs)
            if re.search(r"\b(stage\W*7|grade\W*6|class\W*6|year\W*6)\b", qn): dg.add("Grade 6")
            if re.search(r"\b(stage\W*8|grade\W*7|class\W*7|year\W*7)\b", qn): dg.add("Grade 7")
            if re.search(r"\b(stage\W*9|grade\W*8|class\W*8|year\W*8)\b", qn): dg.add("Grade 8")
        dbi =[compress_image_for_db(img) for img in msg.get("images",[]) if img] if msg.get("images") else msg.get("db_images",[])
        ub, um, un = None, msg.get("user_attachment_mime"), msg.get("user_attachment_name")
        if msg.get("user_attachment_bytes"):
            if "image" in (um or ""): ub = compress_image_for_db(msg["user_attachment_bytes"])
        elif msg.get("user_attachment_b64"): ub = msg.get("user_attachment_b64")
        smg = {"role": str(r), "content": cs, "is_greeting": bool(msg.get("is_greeting")), "is_downloadable": bool(msg.get("is_downloadable")), "db_images":[i for i in dbi if i], "image_models": msg.get("image_models",[])}
        if ub: smg["user_attachment_b64"], smg["user_attachment_mime"], smg["user_attachment_name"] = ub, um, un
        elif un: smg["user_attachment_name"], smg["user_attachment_mime"] = un, um
        sm.append(smg)
    try: 
        tr = c.document(st.session_state.get("current_thread_id")); tr.set({"updated_at": time.time(), "metadata": {"subjects": list(ds), "grades": list(dg)}}, merge=True)
        b = db.batch()
        for idx, s_msg in enumerate(sm):
            s_msg["idx"] = idx; b.set(tr.collection("messages").document(str(idx).zfill(4)), s_msg)
        b.commit()
    except Exception as e: st.toast(f"⚠️ DB Error: {e}")

api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
if not api_key: st.error("🚨 GOOGLE_API_KEY not found."); st.stop()
try: client = genai.Client(api_key=api_key)
except Exception as e: st.error(f"🚨 GenAI Error: {e}"); st.stop()

def generate_with_retry(model_target, contents, config, retries=2):
    fm = ["gemini-2.5-flash", "gemini-3.1-flash-preview", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite-preview"]
    mtt = [model_target] + [m for m in fm if m != model_target]
    for cm in mtt:
        for a in range(retries):
            try: return client.models.generate_content(model=cm, contents=contents, config=config)
            except Exception as e:
                es = str(e).lower()
                if any(x in es for x in ["503", "unavailable", "overloaded", "429", "quota"]):
                    if a < retries - 1: time.sleep(1.5 ** a); continue
                break 
        if cm != mtt[-1]: st.toast(f"⚠️ {cm} overloaded. Switching models...", icon="⚡")
    st.toast("🚨 All Google AI servers are currently overloaded.", icon="🛑")
    return None

def safe_response_text(resp) -> str:
    try: return str(resp.text) if getattr(resp, "text", None) else "\n".join([p.text for c in (getattr(resp, "candidates", []) or[]) for p in (getattr(c.content, "parts",[]) or[]) if getattr(p, "text", None)])
    except: return ""

def process_visual_wrapper(vp):
    el =[]
    try:
        vt, vd = vp
        if vt == "IMAGE_GEN":
            for m in['gemini-3-pro-image-preview', 'gemini-3.1-flash-image-preview', 'imagen-4.0-fast-generate-001', 'gemini-2.5-flash-image']:
                try:
                    if "imagen" in m.lower():
                        r = client.models.generate_images(model=m, prompt=vd, config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="4:3"))
                        if r.generated_images: return (r.generated_images[0].image.image_bytes, m, el)
                    else:
                        r = client.models.generate_content(model=m, contents=[f"{vd}\n\n(Important: Generate a 1k res image with a 4:3 aspect ratio.)"], config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
                        if r.candidates and r.candidates[0].content.parts:
                            for p in r.candidates[0].content.parts:
                                if getattr(p, "inline_data", None) and p.inline_data.data: return (p.inline_data.data, m, el)
                except Exception as e: el.append(f"**{m} Error:** {str(e)}")
            return (None, "All Models Failed", el)
        elif vt == "PIE_CHART":
            try:
                l, s =[],[]
                for i in str(vd).split(","):
                    if ":" in i: k, v = i.split(":", 1); l.append(k.strip()); s.append(float(re.sub(r"[^\d\.]", "", v)))
                if not l or not s or len(l) != len(s): return (None, "matplotlib_failed", el)
                f = Figure(figsize=(5, 5), dpi=200); FigureCanvas(f); ax = f.add_subplot(111)
                ax.pie(s, labels=l, autopct="%1.1f%%", startangle=140, colors=["#00d4ff", "#fc8404", "#2ecc71", "#9b59b6", "#f1c40f", "#e74c3c"][:len(l)], textprops={"color": "black", "fontsize": 9}); ax.axis("equal")
                b = BytesIO(); f.savefig(b, format="png", bbox_inches="tight", transparent=True); return (b.getvalue(), "matplotlib", el)
            except: return (None, "matplotlib_failed", el)
    except Exception as e: return (None, "Crash",[str(e)])

def md_inline_to_rl(text: str) -> str:
    s = (text or "").replace(r'\(', '').replace(r'\)', '').replace(r'\[', '').replace(r'\]', '').replace(r'\times', ' x ').replace(r'\div', ' ÷ ').replace(r'\circ', '°').replace(r'\pm', '±').replace(r'\leq', '≤').replace(r'\geq', '≥').replace(r'\neq', '≠').replace(r'\approx', '≈').replace(r'\pi', 'π').replace(r'\sqrt', '√').replace('\\', '')
    s = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', s).replace('$', '') 
    return re.sub(r"(?<!\*)\*(\S.+?)\*(?!\*)", r"<i>\1</i>", re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")))

def create_pdf(content: str, images=None, filename="Question_Paper.pdf"):
    b = BytesIO(); d = SimpleDocTemplate(b, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
    sty = getSampleStyleSheet()
    ts = ParagraphStyle("CustomTitle", parent=sty["Heading1"], fontSize=18, textColor=colors.HexColor("#00d4ff"), spaceAfter=12, alignment=TA_CENTER, fontName="Helvetica-Bold")
    bs = ParagraphStyle("CustomBody", parent=sty["BodyText"], fontSize=11, spaceAfter=8, alignment=TA_LEFT, fontName="Helvetica")
    story, img_idx, tr =[], 0,[]

    def rnd_tbl():
        nonlocal tr
        if not tr: return
        nc = max(len(r) for r in tr)
        nr = [[Paragraph(md_inline_to_rl(c), bs) for c in list(r) + [""] * (nc - len(r))] for r in tr]
        t = Table(nr, colWidths=[d.width / max(1, nc)] * nc)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00d4ff")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "LEFT"), ("BOTTOMPADDING", (0, 0), (-1, 0), 8), ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        story.extend([t, Spacer(1, 0.18*inch)]); tr.clear()

    ls =[re.sub(r"\s*\(Source:.*?\)", "", l).strip() for l in str(content or "").split("\n") if "[PDF_READY]" not in l.upper() and not l.strip().startswith(("Source(s):", "**Source(s):**"))]
    for s in ls:
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 2:
            cl =[c.strip() for c in s.split("|")[1:-1]]
            if not all(re.fullmatch(r":?-+:?", c) for c in cl if c): tr.append(cl)
            continue
        rnd_tbl()
        if not s: story.append(Spacer(1, 0.14*inch)); continue
        if s.startswith(("IMAGE_GEN:", "PIE_CHART:")):
            if images and img_idx < len(images) and images[img_idx]:
                try:
                    i_s = BytesIO(images[img_idx]); r_r = ImageReader(i_s); iw, ih = r_r.getSize()
                    story.extend([Spacer(1, 0.12*inch), RLImage(i_s, width=4.6*inch, height=4.6*inch*(ih/float(iw))), Spacer(1, 0.12*inch)])
                except: pass
            img_idx += 1; continue
        if s.startswith("# "): story.append(Paragraph(md_inline_to_rl(s[2:].strip()), ts))
        elif s.startswith("## "): story.append(Paragraph(md_inline_to_rl(s[3:].strip()), ParagraphStyle("CustomHeading", parent=sty["Heading2"], fontSize=14, spaceAfter=10, spaceBefore=10, fontName="Helvetica-Bold")))
        elif s.startswith("### "): story.append(Paragraph(f"<b>{md_inline_to_rl(s[4:].strip())}</b>", bs))
        else: story.append(Paragraph(md_inline_to_rl(s), bs))
    rnd_tbl(); story.extend([Spacer(1, 0.28*inch), Paragraph("<i>Generated by helix.ai</i>", bs)])
    d.build(story); b.seek(0); return b

def generate_chat_title(client, messages):
    try:
        um =[m.get("content", "") for m in messages if m.get("role") == "user"]
        if not um: return "New Chat"
        r = generate_with_retry("gemini-2.5-flash", ["Summarize into a short title (max 4 words). Context: " + "\n".join(um[-3:])], types.GenerateContentConfig(temperature=0.3, max_output_tokens=50))
        return safe_response_text(r).strip().replace('"', '').replace("'", "") or "New Chat"
    except: return "New Chat"

def guess_mime(fn: str, fb: str = "application/octet-stream") -> str: return "image/jpeg" if (fn or "").lower().endswith((".jpg", ".jpeg")) else "image/png" if (fn or "").lower().endswith(".png") else "application/pdf" if (fn or "").lower().endswith(".pdf") else fb
def is_image_mime(m: str) -> bool: return (m or "").lower().startswith("image/")

def upload_textbooks():
    af = {"sci":[], "math": [], "eng":[]}
    pm = {p.name.lower(): p for p in Path.cwd().rglob("*.pdf") if "cie" in p.name.lower()}
    cf = "fast_sync_cache.json"
    if os.path.exists(cf):
        try:
            with open(cf, "r") as f: cd = json.load(f)
            if time.time() - cd.get("timestamp", 0) < 86400:
                class CF:
                    def __init__(self, d): self.uri = d["uri"]; self.display_name = d["display_name"]
                for subj, files in cd["files"].items():
                    for i in files: af[subj].append(CF(i))
                return af
        except: pass
    
    try: ex = {f.display_name.lower(): f for f in client.files.list() if f.display_name}
    except: ex = {}
    
    def process_single_book(t):
        if t in ex and ex[t].state.name == "ACTIVE": return t, ex[t]
        if t in pm:
            try:
                up = client.files.upload(file=str(pm[t]), config={"mime_type": "application/pdf", "display_name": pm[t].name})
                timeout = time.time() + 90
                while up.state.name == "PROCESSING" and time.time() < timeout: time.sleep(3); up = client.files.get(name=up.name)
                if up.state.name == "ACTIVE": return t, up
            except Exception as e: print(f"Upload Error {t}: {e}")
        return t, None
        
    with st.chat_message("assistant"): st.markdown(f"""<div class="thinking-container"><span class="thinking-text">📚 Syncing {len(pm)} Books...</span><div class="thinking-dots"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div></div>""", unsafe_allow_html=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor: results = list(executor.map(process_single_book, list(pm.keys())))
        
    cd = {"sci": [], "math": [], "eng":[]}
    for t, fo in results:
        if fo:
            sk = "sci" if "sci" in t else "math" if "math" in t else "eng" if "eng" in t else None
            if sk: af[sk].append(fo); cd[sk].append({"uri": fo.uri, "display_name": fo.display_name})
                
    try:
        with open(cf, "w") as f: json.dump({"timestamp": time.time(), "files": cd}, f)
    except: pass
    return af

def select_relevant_books(q, fd, ug="Grade 6"):
    qn = normalize_stage_text(q)
    s7, s8, s9 = any(k in qn for k in["stage 7", "grade 6", "year 7"]), any(k in qn for k in["stage 8", "grade 7", "year 8"]), any(k in qn for k in["stage 9", "grade 8", "year 9"])
    im, isc, ien = any(k in qn for k in["math", "algebra", "number", "fraction", "geometry", "calculate", "equation"]), any(k in qn for k in["sci", "biology", "physics", "chemistry", "experiment", "cell", "gravity"]), any(k in qn for k in["eng", "poem", "story", "essay", "writing", "grammar"])
    if not (s7 or s8 or s9): s7, s8, s9 = (ug=="Grade 6"), (ug=="Grade 7"), (ug=="Grade 8")
    if not (im or isc or ien): im = isc = ien = True
    sel =[]
    def add(k, act):
        if act: 
            for b in fd.get(k,[]):
                n = b.display_name.lower()
                if "answers" in n and user_role != "teacher": continue
                if (s7 and "cie_7" in n) or (s8 and "cie_8" in n) or (s9 and "cie_9" in n): sel.append(b); return 
    add("math", im); add("sci", isc); add("eng", ien)
    return sel

def generate_full_quiz_ai(p, u_grade):
    pt = f"Create EXACTLY {p['num']} unique questions for a {p['grade']} {p['subj']} student. Topic: {p['chap']}. Difficulty: {p['diff']}."
    bs = select_relevant_books(f"{p['subj']} {p['grade']}", st.session_state.get("textbook_handles", {}), u_grade)
    ps =[]
    for b in bs: ps.extend([types.Part.from_text(text=f"[Source: {b.display_name}]"), types.Part.from_uri(file_uri=b.uri, mime_type="application/pdf")])
    ps.append(pt)
    r = generate_with_retry("gemini-2.5-flash", ps, types.GenerateContentConfig(system_instruction=QUIZ_SYSTEM_INSTRUCTION, temperature=0.7))
    if r:
        m = re.search(r'\[.*\]', safe_response_text(r), re.DOTALL)
        if m:
            try: return json.loads(m.group(0))
            except: pass
    return None

def evaluate_short_answer(q, ua, ref):
    pt = f"Evaluate short answer.\nQ: {q}\nAns: {ua}\nRef: {ref}\nOutput JSON: {{\n\"is_correct\": true/false,\n\"explanation\": \"feedback\"\n}}"
    try:
        r = client.models.generate_content(model="gemini-2.5-flash-lite", contents=pt, config=types.GenerateContentConfig(temperature=0.1))
        m = re.search(r'\{.*\}', safe_response_text(r), re.DOTALL)
        if m: return json.loads(m.group(0))
    except: pass
    return {"is_correct": False, "explanation": "Failed to evaluate answer."}

# -----------------------------
# QUIZ ENGINE & ROUTING LOGIC
# -----------------------------
def render_quiz_engine():
    if not st.session_state.get("quiz_active", False) and not st.session_state.get("quiz_finished", False):
        st.markdown("<div class='quiz-title'>⚙️ Quiz Engine</div>", unsafe_allow_html=True)
        tab_ai, tab_man, tab_join = st.tabs(["🤖 AI Generator", "✍️ Manual Builder", "🔑 Join Quiz"])
        
        with tab_ai:
            with st.form("create_quiz_form", border=False):
                st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
                st.markdown("<h3 style='text-align: center; margin-bottom:20px;'>Generate AI Quiz</h3>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                q_subj = c1.selectbox("Subject",["Math", "Science", "English"]) # Quiz UI subjects
                current_active_grade = st.session_state.get("active_grade", user_profile.get("grade", "Grade 6"))
                q_grade = c2.selectbox("Grade",["Grade 6", "Grade 7", "Grade 8"], index=["Grade 6", "Grade 7", "Grade 8"].index(current_active_grade))
                q_diff = c3.selectbox("Difficulty",["Easy", "Medium", "Hard"])
                
                c4, c5 = st.columns([3, 1])
                q_chap = c4.text_input("Chapter / Topic", placeholder="e.g., Chapter 4, Fractions, Forces...")
                q_num = c5.selectbox("Questions",[5, 10, 15, 20])
                
                col_btn1, col_btn2 = st.columns(2)
                start_quiz_btn = col_btn1.form_submit_button("🚀 Start Interactive Quiz", type="primary", use_container_width=True)
                gen_code_btn = col_btn2.form_submit_button("🔗 Generate ShareCode Only", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                if start_quiz_btn or gen_code_btn:
                    p = {"subj": q_subj, "grade": q_grade, "diff": q_diff, "chap": q_chap, "num": q_num}
                    with st.spinner("Generating your unique quiz... This may take up to 30 seconds."):
                        generated_q = generate_full_quiz_ai(p, current_active_grade)
                    
                    if generated_q:
                        share_code = str(uuid.uuid4())[:6].upper()
                        if db:
                            db.collection("quizzes").document(share_code).set({
                                "params": p, "questions": generated_q, "created_by": user_email, "created_at": time.time()
                            })
                        if start_quiz_btn:
                            st.session_state.quiz_params = p
                            st.session_state.quiz_questions = generated_q
                            st.session_state.quiz_score, st.session_state.quiz_current_q = 0, 1
                            st.session_state.quiz_active, st.session_state.quiz_saved = True, False
                            st.session_state.quiz_bg, st.session_state.quiz_history = "default",[]
                            st.session_state.quiz_share_code = share_code
                            st.rerun()
                        else:
                            st.success(f"Quiz generated! Share this code: **{share_code}**")
                    else: st.error("Failed to generate quiz. Please try again.")

        with tab_man:
            if "manual_questions" not in st.session_state: st.session_state.manual_questions =[]
            for i, mq in enumerate(st.session_state.get("manual_questions",[])):
                st.info(f"**Q{i+1}:** {mq['question']} *({mq['type']})*")
            
            with st.expander("➕ Add New Question", expanded=True):
                q_type = st.radio("Question Type",["MCQ", "Short Answer"])
                q_text = st.text_area("Question Text")
                if q_type == "MCQ":
                    mc1, mc2 = st.columns(2)
                    opt_a = mc1.text_input("Option A")
                    opt_b = mc2.text_input("Option B")
                    opt_c = mc1.text_input("Option C")
                    opt_d = mc2.text_input("Option D")
                    correct_opt = st.selectbox("Correct Option",["Option A", "Option B", "Option C", "Option D"])
                    if st.button("Save MCQ"):
                        opts =[opt_a, opt_b, opt_c, opt_d]
                        c_text = opts[["Option A", "Option B", "Option C", "Option D"].index(correct_opt)]
                        st.session_state.manual_questions.append({
                            "question": q_text, "type": "MCQ", "options": opts, "correct_answer": c_text, "explanation": "Manual Quiz - Correct Answer."
                        })
                        st.rerun()
                else:
                    ref_ans = st.text_area("Reference Answer / Grading Rubric")
                    if st.button("Save Short Answer"):
                        st.session_state.manual_questions.append({
                            "question": q_text, "type": "Short Answer", "options":[], "correct_answer": ref_ans, "explanation": "Manual Quiz Evaluated."
                        })
                        st.rerun()

            if len(st.session_state.get("manual_questions",[])) > 0:
                if st.button("Publish Quiz & Get ShareCode", type="primary", use_container_width=True):
                    code = str(uuid.uuid4())[:6].upper()
                    if db:
                        db.collection("quizzes").document(code).set({
                            "questions": st.session_state.manual_questions,
                            "created_by": user_email,
                            "created_at": time.time(),
                            "params": {"subj": "Manual", "grade": "Mixed", "diff": "Mixed", "chap": "Mixed", "num": len(st.session_state.manual_questions)}
                        })
                    st.success(f"Quiz Published! ShareCode: **{code}**")
                    st.session_state.manual_questions =[]

        with tab_join:
            with st.form("join_quiz_form", border=False):
                with st.container(border=True):
                    st.markdown("<h3 style='text-align: center; margin-bottom:20px;'>Join a Shared Quiz</h3>", unsafe_allow_html=True)
                    share_code_input = st.text_input("Enter ShareCode", placeholder="e.g., A1B2C3").upper()
                    if st.form_submit_button("Join Quiz", use_container_width=True):
                        if db:
                            quiz_ref = db.collection("quizzes").document(share_code_input).get()
                            if quiz_ref.exists:
                                q_dict = quiz_ref.to_dict()
                                st.session_state.quiz_params = q_dict.get("params", {"subj": "General", "num": len(q_dict.get("questions",[]))})
                                st.session_state.quiz_questions = q_dict.get("questions",[])
                                st.session_state.quiz_share_code = share_code_input
                                st.session_state.quiz_score, st.session_state.quiz_current_q = 0, 1
                                st.session_state.quiz_active, st.session_state.quiz_saved = True, False
                                st.session_state.quiz_bg, st.session_state.quiz_history = "default",[]
                                st.rerun()
                            else:
                                st.error("Invalid ShareCode. Please check the code and try again.")
    else:
        q_list = st.session_state.get("quiz_questions",[])
        q_idx = st.session_state.get("quiz_current_q", 1) - 1
        
        if st.session_state.get("quiz_finished"):
            score, total = st.session_state.get("quiz_score"), len(st.session_state.get("quiz_questions",[]))
            if not st.session_state.get("quiz_saved") and is_authenticated and db:
                db.collection("users").document(user_email).collection("quiz_results").add({"timestamp": time.time(), "score": score, "total": total, "subject": st.session_state.get("quiz_params", {}).get('subj', 'Manual')})
                st.session_state.quiz_saved = True
                
            st.balloons()
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f"<h1 style='color:#2ecc71; text-align:center;'>🎉 Quiz Complete! 🎉</h1>", unsafe_allow_html=True)
                st.markdown(f"<h2 style='text-align:center;'>You scored: <span style='color:#00d4ff;'>{score} / {total}</span></h2>", unsafe_allow_html=True)
                
                if st.session_state.get("quiz_share_code"):
                    st.info(f"Challenge friends with ShareCode: **{st.session_state.get('quiz_share_code')}**")
                    
                if st.button("Take Another Quiz", type="primary", use_container_width=True):
                    for key in list(st.session_state.keys()):
                        if key.startswith('quiz_'): del st.session_state[key]
                    st.rerun()
                    
        elif q_idx < len(q_list):
            q_data = q_list[q_idx]
            q_params = st.session_state.get("quiz_params", {})
            
            with st.container(border=True):
                st.markdown(f"<div class='quiz-counter'>Question {q_idx + 1} of {len(q_list)}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='quiz-question-text'>{q_data.get('question', 'Question text missing')}</div>", unsafe_allow_html=True)

                if st.session_state.get("quiz_user_answer") is None:
                    if q_data.get("type", "MCQ") == "MCQ":
                        for o_idx, option in enumerate(q_data.get('options',[])):
                            if st.button(option, use_container_width=True, key=f"q{q_idx}_opt_{o_idx}"):
                                st.session_state.quiz_user_answer = option; st.rerun()
                    else:
                        user_sa = st.text_area("Your Answer:")
                        if st.button("Submit Answer", type="primary"):
                            with st.spinner("Evaluating..."):
                                eval_res = evaluate_short_answer(q_data.get("question"), user_sa, q_data.get("correct_answer"))
                                st.session_state.quiz_sa_eval = eval_res
                            st.session_state.quiz_user_answer = user_sa; st.rerun()
                else:
                    user_ans = st.session_state.get("quiz_user_answer")
                    
                    if q_data.get("type", "MCQ") == "MCQ":
                        is_correct = (user_ans == q_data.get('correct_answer'))
                        explanation = q_data.get('explanation', '')
                    else:
                        eval_res = st.session_state.get("quiz_sa_eval", {})
                        is_correct = eval_res.get("is_correct", False)
                        explanation = eval_res.get("explanation", "Evaluated by AI.")

                    if is_correct:
                        st.success(f"**Correct!** {explanation}")
                        if st.session_state.get("quiz_bg") != "correct":
                            st.session_state.quiz_score += 1
                            st.session_state.quiz_bg = "correct"; st.rerun()
                    else:
                        if q_data.get("type", "MCQ") == "MCQ": st.error(f"**Incorrect.** The correct answer was **{q_data.get('correct_answer')}**. \n\n*Explanation: {explanation}*")
                        else: st.error(f"**Incorrect.** \n\n*Feedback: {explanation}*")
                        if st.session_state.get("quiz_bg") != "wrong":
                            st.session_state.quiz_bg = "wrong"; st.rerun()
                            
                    if len(st.session_state.get("quiz_history",[])) < st.session_state.get("quiz_current_q"):
                        st.session_state.quiz_history.append({"q": q_data.get('question'), "user": user_ans, "correct": q_data.get('correct_answer'), "is_correct": is_correct})
                        if len(st.session_state.quiz_history) % 5 == 0: run_quiz_weakpoint_check(st.session_state.quiz_history[-5:], user_email, q_params.get('subj', 'General'))

                    is_last_q = (st.session_state.get("quiz_current_q") == len(q_list))
                    if st.button("Next Question" if not is_last_q else "Finish Quiz", type="primary", use_container_width=True):
                        if is_last_q: st.session_state.quiz_finished = True
                        else: st.session_state.quiz_current_q += 1
                        st.session_state.quiz_user_answer = None 
                        st.session_state.quiz_bg = "default"; st.rerun()

# ==========================================
# APP ROUTER
# ==========================================
render_chat_interface = False 
view_mode = st.session_state.get("view_mode", "main")
app_mode = st.session_state.get("app_mode", "💬 AI Tutor")

# --- 1) ACCOUNT DASHBOARD (ALL ROLES) ---
if view_mode == "account":
    render_chat_interface = False
    st.markdown("<div class='big-title' style='display: flex; align-items: center; justify-content: center; gap: 15px;'><svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-user'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'></path><circle cx='12' cy='7' r='4'></circle></svg> My Account</div><br>", unsafe_allow_html=True)
    
    student_class_data = get_student_class_data(user_email)
    class_name = student_class_data.get('id') if student_class_data else "Not in a Class"
    school_name = user_profile.get('school') or (student_class_data.get('school') if student_class_data else None) or "Not linked"
    
    st.markdown(f"""<div class="glass-container">
        <div class="account-detail"><b>Name:</b> {user_profile.get('display_name', 'Guest')}</div>
        <div class="account-detail"><b>Email:</b> {user_email}</div>
        <div class="account-detail"><b>Grade:</b> {user_profile.get('grade', 'Grade 6')}</div>
        <div class="account-detail"><b>School:</b> {school_name}</div>
        {f'<div class="account-detail"><b>Class:</b> {class_name}</div>' if user_role == 'student' else ''}
    </div>""", unsafe_allow_html=True)

    if not student_class_data and not user_profile.get('school'):
        with st.form("rename_form", border=False):
            st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
            new_name = st.text_input("Change Display Name", value=user_profile.get('display_name', ''))
            if st.form_submit_button("Save Name", use_container_width=True):
                if db: db.collection("users").document(user_email).update({"display_name": new_name})
                st.success("Name updated!"); time.sleep(1); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
    if user_role == "teacher":
        st.markdown("### Danger Zone")
        with st.container(border=True):
            if st.button("Request Account Deletion", type="primary", use_container_width=True):
                confirm_delete_account_dialog()

    if user_role == "student":
        scores, totals = 0, 0
        if db:
            qr_docs = db.collection("users").document(user_email).collection("quiz_results").stream()
            for qd in qr_docs: d = qd.to_dict(); scores += d.get("score", 0); totals += d.get("total", 0)
        mastery = int((scores/totals)*100) if totals > 0 else 0
        
        st.markdown(f"""<div class="glass-container"><div class="mastery-title">Overall Mastery</div><div class="mastery-value">{mastery}%</div></div>""", unsafe_allow_html=True)
        st.markdown("### ⚠️ Potential Weak Spots (7 Days)")
        with st.spinner("Analyzing recent performance..."):
            active_spots, _ = evaluate_weak_spots(user_email)
        
        if not active_spots: st.markdown("<div class='success-item'>No active weak spots detected! Great job! 🎉</div>", unsafe_allow_html=True)
        else:
            for spot in active_spots:
                col1, col2 = st.columns([0.8, 0.2])
                with col1: st.markdown(f"<div class='weak-spot-item'>[{spot.get('subject', 'General')}] {spot['topic']}</div>", unsafe_allow_html=True)
                with col2:
                    if st.button("Dismiss", key=f"d_a_{spot['id']}", use_container_width=True):
                        if db: db.collection("users").document(user_email).collection("weak_spots").document(spot['id']).update({"dismissed": True})
                        st.rerun()

# --- 2) TEACHER DASHBOARD ---
elif user_role == "teacher":
    st.markdown("<div class='big-title' style='color:#fc8404;'>👨‍🏫 helix.ai / Teacher</div><br>", unsafe_allow_html=True)
    
    roster =[]
    if db:
        if user_profile.get("school"): roster_stream = db.collection("users").where(filter=firestore.FieldFilter("school", "==", user_profile.get("school"))).stream()
        else: roster_stream = db.collection("users").where(filter=firestore.FieldFilter("teacher_id", "==", user_email)).stream()
        roster =[u for u in roster_stream if u.to_dict().get("role") == "student"]

    teacher_menu = st.radio("Menu",["Student Analytics", "Class Management", "Assign Papers", "⚡ Interactive Quiz", "💬 AI Chat"], horizontal=True, label_visibility="collapsed")
    st.divider()

    if teacher_menu == "Student Analytics":
        st.subheader("📊 Student Analytics")
        if not roster: st.info("No students enrolled yet.")
        else:
            selected_student_name = st.selectbox("Select Student",[r.to_dict().get('display_name', r.id) for r in roster])
            student_doc_list =[r for r in roster if r.to_dict().get('display_name', r.id) == selected_student_name]
            if student_doc_list:
                stu_email = student_doc_list[0].id
                stu_class_data = get_student_class_data(stu_email)
                class_subjects = stu_class_data.get("subjects",[]) if stu_class_data else[]
                
                st.markdown("#### Subject-Specific Mastery")
                if not class_subjects: st.info("No subjects assigned to this student's class.")
                else:
                    cols = st.columns(len(class_subjects))
                    for i, subject in enumerate(class_subjects):
                        scores, totals = 0, 0
                        if db:
                            qr_docs = db.collection("users").document(stu_email).collection("quiz_results").where(filter=firestore.FieldFilter("subject", "==", subject)).stream()
                            for qd in qr_docs: d = qd.to_dict(); scores += d.get("score", 0); totals += d.get("total", 0)
                        mastery = int((scores/totals)*100) if totals > 0 else 0
                        cols[i].metric(f"{subject}", f"{mastery}%")
                
                st.markdown("### ⚠️ Potential Weak Spots (7 Days)")
                with st.spinner("Analyzing recent performance..."):
                    active_spots, _ = evaluate_weak_spots(stu_email)
                
                relevant_spots =[s for s in active_spots if s.get('subject') in class_subjects] if class_subjects else active_spots
                
                if not relevant_spots: st.success("No active weak spots detected for your subjects!")
                else:
                    for spot in relevant_spots:
                        col1, col2 = st.columns([0.8, 0.2])
                        col1.warning(f"[{spot.get('subject', 'General')}] {spot['topic']}")
                        if col2.button("Dismiss", key=f"d_t_{spot['id']}"):
                            if db: db.collection("users").document(stu_email).collection("weak_spots").document(spot['id']).update({"dismissed": True})
                            st.rerun()

    elif teacher_menu == "Class Management":
        st.subheader("🏫 Class Management")
        with st.form("create_class_form", border=False):
            st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
            st.markdown("<h5>Create New Class</h5>", unsafe_allow_html=True)
            cc1, cc2, cc3 = st.columns([0.4, 0.3, 0.3])
            grade_choice = cc1.selectbox("Grade",["Grade 6", "Grade 7", "Grade 8"])
            section_choice = cc2.selectbox("Section", ["A", "B", "C", "D"])
            if cc3.form_submit_button("Create", use_container_width=True):
                success, msg = create_global_class(f"{grade_choice.split()[-1]}{section_choice}".upper(), user_email, grade_choice, section_choice, user_profile.get("school"))
                if success: st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)
            st.markdown("</div>", unsafe_allow_html=True)
            
        my_classes = list(db.collection("classes").where(filter=firestore.FieldFilter("created_by", "==", user_email)).stream()) if db else[]
        if my_classes:
            st.markdown("---")
            st.subheader("Edit Existing Class")
            for c_doc in my_classes:
                c_data = c_doc.to_dict()
                col1, col2 = st.columns([0.85, 0.15])
                if col1.button(f"🏫 {c_doc.id}", key=f"sel_cls_{c_doc.id}", use_container_width=True): st.session_state.managing_class = c_doc.id
                if col2.button("⋮", key=f"del_cls_{c_doc.id}"): manage_class_dialog_ui(c_doc.id)
                    
            if st.session_state.get("managing_class"):
                m_class_id = st.session_state.get("managing_class")
                if db:
                    m_class_doc = db.collection("classes").document(m_class_id).get()
                    if m_class_doc.exists:
                        c_data = m_class_doc.to_dict()
                        with st.form(f"edit_subjects_{m_class_id}", border=False):
                            st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
                            subjects = st.multiselect(f"Subjects taught in {m_class_id}",["Math", "English", "Physics", "Chemistry", "Biology"], default=c_data.get("subjects",[]))
                            if st.form_submit_button("Update Subjects", use_container_width=True):
                                db.collection("classes").document(m_class_id).update({"subjects": subjects})
                                st.success("Subjects updated!"); time.sleep(1); st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                        st.markdown("<h6>Student Roster</h6>", unsafe_allow_html=True)
                        for s_email in c_data.get("students",[]):
                            s_prof = get_user_profile(s_email)
                            c1, c2 = st.columns([0.85, 0.15], vertical_alignment="center")
                            c1.markdown(f"<div class='glass-container' style='padding:10px; margin-bottom:5px;'>{s_prof.get('display_name', 'Unknown')} ({s_email})</div>", unsafe_allow_html=True)
                            if c2.button("⋮", key=f"mng_stu_{s_email}"): manage_student_dialog_ui(s_email, m_class_id)
                        
                        with st.form(f"add_student_{m_class_id}", border=False):
                            st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
                            em = st.text_input("Add Student Email")
                            if st.form_submit_button("Add Student", use_container_width=True) and em:
                                db.collection("users").document(em.strip().lower()).set({"role": "student", "teacher_id": user_email, "school": user_profile.get("school")}, merge=True)
                                db.collection("classes").document(m_class_id).update({"students": firestore.ArrayUnion([em.strip().lower()])})
                                st.success("Added!"); time.sleep(1); st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)

    elif teacher_menu == "Assign Papers":
        st.subheader("📝 Assignment Creator")
        with st.form("assign_paper_form", border=False):
            st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            assign_title, assign_subject, assign_grade = c1.text_input("Title", "Chapter Quiz"), c1.selectbox("Subject",["Math", "Science", "Biology", "Chemistry", "Physics", "English"]), c1.selectbox("Grade",["Grade 6", "Grade 7", "Grade 8"])
            assign_difficulty, assign_marks, assign_extra = c2.selectbox("Difficulty",["Easy", "Medium", "Hard"]), c2.number_input("Marks", 10, 100, 30, 5), st.text_area("Extra Instructions")
            if st.form_submit_button("🤖 Generate with Helix AI", type="primary", use_container_width=True):
                with st.spinner("Writing paper..."):
                    books = select_relevant_books(f"{assign_subject} {assign_grade}", st.session_state.get("textbook_handles", {}), assign_grade)
                    parts =[]
                    for b in books: parts.extend([types.Part.from_text(text=f"[Source: {b.display_name}]"), types.Part.from_uri(file_uri=b.uri, mime_type="application/pdf")])
                    parts.append(types.Part.from_text(text=f"Task: Generate a CIE {assign_subject} paper for {assign_grade} students.\nDifficulty: {assign_difficulty}. Marks: {assign_marks}.\nExtra Instructions: {assign_extra}"))
                    try:
                        resp = generate_with_retry("gemini-2.5-flash", parts, types.GenerateContentConfig(system_instruction=PAPER_SYSTEM, temperature=0.1))
                        gen_paper = safe_response_text(resp)
                        draft_imgs, draft_mods = [],[]
                        if v_prompts := re.findall(r"(IMAGE_GEN|PIE_CHART):\s*\[(.*?)\]", gen_paper):
                            with concurrent.futures.ThreadPoolExecutor(5) as exe:
                                for r in exe.map(process_visual_wrapper, v_prompts):
                                    if r and r[0]: draft_imgs.append(r[0]); draft_mods.append(r[1])
                        st.session_state.update({"draft_paper": gen_paper, "draft_images": draft_imgs, "draft_models": draft_mods, "draft_title": assign_title}); st.rerun()
                    except Exception as e: st.error("Failed to generate paper.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        if st.session_state.get("draft_paper"):
            with st.expander("Preview", expanded=True):
                st.markdown(st.session_state.get("draft_paper").replace("[PDF_READY]", ""))
                if st.session_state.get("draft_images"):
                    for i, m in zip(st.session_state.get("draft_images"), st.session_state.get("draft_models")):
                        if i: st.image(i, caption=m)
                try: st.download_button("Download PDF", data=create_pdf(st.session_state.get("draft_paper"), st.session_state.get("draft_images")), file_name=f"{st.session_state.get('draft_title')}.pdf", mime="application/pdf")
                except Exception: st.error("PDF Gen Error.")

    elif teacher_menu == "⚡ Interactive Quiz": render_quiz_engine()
    elif teacher_menu == "💬 AI Chat": render_chat_interface = True 

# --- 3) STUDENT MAIN DASHBOARD (Chat or Quiz) ---
else:
    if app_mode == "⚡ Interactive Quiz": render_quiz_engine()
    else: render_chat_interface = True

# ==========================================
# UNIVERSAL CHAT VIEW (AI Tutor / Teacher Chat)
# ==========================================
if render_chat_interface:
    st.markdown("<div class='big-title'>📚 helix.ai</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; opacity: 0.60; font-size: 18px; margin-bottom: 30px;'>Your AI-powered Cambridge (CIE) Tutor for Grade 6-8.</div>", unsafe_allow_html=True)

    for idx, msg in enumerate(st.session_state.get("messages",[])):
        with st.chat_message(msg["role"]):
            disp = msg.get("content") or ""
            disp = re.sub(r"(?i)(?:Here is the )?(?:Analytics|JSON).*?(?:for student)?s?\s*[:-]?\s*", "", disp)
            disp = re.sub(r"===ANALYTICS_START===.*?===ANALYTICS_END===", "", disp, flags=re.IGNORECASE|re.DOTALL)
            disp = re.sub(r"```json\s*\{[^{]*?\"weak_point\".*?\}\s*```", "", disp, flags=re.IGNORECASE|re.DOTALL)
            disp = re.sub(r"\{[^{]*?\"weak_point\".*?\}", "", disp, flags=re.IGNORECASE|re.DOTALL)
            st.markdown(re.sub(r"\[PDF_READY\]", "", disp, flags=re.IGNORECASE).strip())
            
            for img, mod in zip(msg.get("images") or[], msg.get("image_models", ["Unknown"]*10)):
                if img: st.image(img, use_container_width=True, caption=f"✨ Generated by helix.ai ({mod})")
            for b64, mod in zip(msg.get("db_images") or[], msg.get("image_models", ["Unknown"]*10)):
                if b64:
                    try: st.image(base64.b64decode(b64), use_container_width=True, caption=f"✨ Generated by helix.ai ({mod})")
                    except: pass
            
            if msg.get("user_attachment_bytes"):
                mime, name = msg.get("user_attachment_mime", ""), msg.get("user_attachment_name", "File")
                if "image" in mime: st.image(msg["user_attachment_bytes"], use_container_width=True)
                else: st.caption(f"📎 Attached: {name}")
            elif msg.get("user_attachment_b64"):
                try: st.image(base64.b64decode(msg["user_attachment_b64"]), use_container_width=True)
                except: st.caption(f"📎 Attached: {msg.get('user_attachment_name', 'File')}")
            elif msg.get("user_attachment_name"): st.caption(f"📎 Attached: {msg.get('user_attachment_name', 'File')}")

            if msg["role"] == "assistant" and msg.get("is_downloadable"):
                try: st.download_button("📄 Download PDF", data=create_pdf(msg.get("content") or "", msg.get("images") or[base64.b64decode(b) for b in msg.get("db_images", []) if b]), file_name=f"Paper_{idx}.pdf", mime="application/pdf", key=f"dl_{idx}")
                except Exception: pass

    if chat_input := st.chat_input("Ask Helix...", accept_file=True, file_type=["jpg","png","pdf","txt"]):
        
        if "textbook_handles" not in st.session_state: st.session_state.textbook_handles = upload_textbooks()
        
        f_bytes, f_mime, f_name = (chat_input.files[0].getvalue() if chat_input.files else None), (chat_input.files[0].type if chat_input.files else None), (chat_input.files[0].name if chat_input.files else None)
        
        if "messages" not in st.session_state: st.session_state.messages =[]
        st.session_state.messages.append({"role": "user", "content": (chat_input.text or "").strip(), "user_attachment_bytes": f_bytes, "user_attachment_mime": f_mime, "user_attachment_name": f_name})
        save_chat_history(); st.rerun()

    if st.session_state.get("messages") and st.session_state.get("messages")[-1]["role"] == "user":
        msg_data = st.session_state.messages[-1]
        with st.chat_message("assistant"):
            think = st.empty()
            
            try:
                think.markdown("""<div class="thinking-container"><span class="thinking-text">Thinking</span><div class="thinking-dots"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div></div>""", unsafe_allow_html=True)
                
                valid_history =[]
                exp_role = "model"
                for m in reversed([m for m in st.session_state.get("messages",[])[:-1] if not m.get("is_greeting")]):
                    r = "user" if m.get("role") == "user" else "model"
                    txt = m.get("content") or ""
                    if txt.strip() and r == exp_role:
                        valid_history.insert(0, types.Content(role=r, parts=[types.Part.from_text(text=txt)]))
                        exp_role = "user" if exp_role == "model" else "model"
                if valid_history and valid_history[0].role == "model": valid_history.pop(0)

                curr_parts =[]
                student_grade = st.session_state.get("active_grade", user_profile.get("grade", "Grade 6"))
                books = select_relevant_books(" ".join([m.get("content", "") for m in st.session_state.get("messages", [])[-3:]]), st.session_state.get("textbook_handles", {}), student_grade)
                
                if books:
                    for b in books: 
                        curr_parts.append(types.Part.from_text(text=f"--- START OF SOURCE TEXTBOOK: {b.display_name} ---"))
                        curr_parts.append(types.Part.from_uri(file_uri=b.uri, mime_type="application/pdf"))
                        curr_parts.append(types.Part.from_text(text=f"--- END OF SOURCE TEXTBOOK ---"))
                
                if f_bytes := msg_data.get("user_attachment_bytes"):
                    mime = msg_data.get("user_attachment_mime") or guess_mime(msg_data.get("user_attachment_name"))
                    if is_image_mime(mime): curr_parts.append(types.Part.from_bytes(data=f_bytes, mime_type=mime))
                    elif "pdf" in mime:
                        tmp = f"temp_{time.time()}.pdf"; open(tmp, "wb").write(f_bytes); up = client.files.upload_file(tmp)
                        while up.state.name == "PROCESSING": time.sleep(1); up = client.files.get(name=up.name)
                        curr_parts.append(types.Part.from_uri(file_uri=up.uri, mime_type="application/pdf")); os.remove(tmp)

                curr_parts.append(types.Part.from_text(text=f"Context: Student Grade is {student_grade}.\n\nUser Query: {msg_data.get('content')}"))
                
                user_msg_count = sum(1 for m in st.session_state.get("messages",[]) if m["role"] == "user")
                if user_msg_count > 0 and user_msg_count % 6 == 0:
                    curr_parts.append(types.Part.from_text(text="Please analyze the student's previous inputs. If you detect a clear, specific academic weak point, output the hidden ===ANALYTICS_START=== JSON block. If not, do NOT output it."))

                resp = generate_with_retry("gemini-2.5-flash", valid_history +[types.Content(role="user", parts=curr_parts)], types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.3, tools=[{"google_search": {}}]))
                
                if resp is None: bot_txt = "My apologies, I'm currently experiencing exceptionally high network traffic and can't access my core knowledge base. Could you please try asking your question again in a moment?"
                else: bot_txt = safe_response_text(resp)
                
                match_full = re.search(r"===ANALYTICS_START===(.*?)===ANALYTICS_END===", bot_txt, flags=re.IGNORECASE|re.DOTALL) or re.search(r"(?:(?:Here is the )?Analytics.*?:?\s*|```json\s*)?(\{[\s\S]*?\"weak_point\"[\s\S]*?\})(?:\s*```)?", bot_txt, flags=re.IGNORECASE)
                
                if match_full:
                    try:
                        ad = json.loads(match_full.group(1))
                        start_idx = match_full.start()
                        bot_txt = bot_txt[:start_idx].strip()
                        bot_txt = re.sub(r"(?i)(?:Here is the )?(?:Analytics|JSON).*?(?:for student)?s?\s*[:-]?\s*$", "", bot_txt).strip()
                        if is_authenticated and db and ad.get("weak_point"): db.collection("users").document(user_email).collection("analytics").add({"timestamp": time.time(), "source": "chat", **ad})
                    except Exception: pass

                think.empty()
                
                imgs, mods = [],[]
                if v_prompts := re.findall(r"(IMAGE_GEN|PIE_CHART):\s*\[(.*?)\]", bot_txt):
                    with concurrent.futures.ThreadPoolExecutor(5) as exe:
                        for r in exe.map(process_visual_wrapper, v_prompts):
                            if r and r[0]: imgs.append(r[0]); mods.append(r[1])
                
                dl = bool(re.search(r"\[PDF_READY\]|##\s*Mark Scheme", bot_txt, re.IGNORECASE))
                st.session_state.messages.append({"role": "assistant", "content": bot_txt, "is_downloadable": dl, "images": imgs, "image_models": mods})
                
                if is_authenticated and sum(1 for m in st.session_state.get("messages",[]) if m.get("role") == "user") == 1:
                    t = generate_chat_title(client, st.session_state.get("messages", []))
                    if t and db: get_threads_collection().document(st.session_state.get("current_thread_id")).set({"title": t}, merge=True)
                
                save_chat_history(); st.rerun()
                
            except Exception as e: 
                think.empty()
                print(f"FATAL CHAT ERROR: {e}") 
                fallback_msg = "My apologies, I seem to have encountered an unexpected system glitch. Please try your request again."
                st.session_state.messages.append({"role": "assistant", "content": fallback_msg})
                st.rerun()
