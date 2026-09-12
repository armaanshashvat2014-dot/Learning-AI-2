import streamlit as st
import re, os, time, itertools, json, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings, logging
import wikipedia
import fitz
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from google import genai
from streamlit_js_eval import streamlit_js_eval

warnings.filterwarnings("ignore")
logging.getLogger("pymupdf").setLevel(logging.ERROR)

st.set_page_config(
    page_title="SmartLoop AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}          # removes the hamburger ⋮ menu items
)

# One simple colour controls the entire interface.
if "accent_color" not in st.session_state:
    st.session_state.accent_color = "#fbbc04"

st.markdown("""<!-- LEGACY DARK THEME DISABLED
<style>
/* ── Force dark mode regardless of OS/browser preference ── */
:root {
    color-scheme: dark !important;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    color-scheme: dark !important;
}

/* ── Hide GitHub icon, deploy button, toolbar share/fork buttons ── */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
.stDeployButton,
button[title="View source on GitHub"],
button[title="Fork this app"],
button[aria-label="View source on GitHub"],
button[aria-label="Fork this app"],
a[href*="github.com"],
footer { display: none !important; visibility: hidden !important; }

/* ── Remove the top-right header action buttons (share/star/fork) ── */
[data-testid="stHeader"] {
    background: transparent !important;
}
[data-testid="stHeader"] button { display: none !important; }

/* ── App background ── */
.stApp {
    background: radial-gradient(800px circle at 50% 0%,
        rgba(0,212,255,0.10), rgba(0,212,255,0.00) 60%), #0a0a1a !important;
    color: #f5f5f7 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(12,12,22,0.97) !important;
    backdrop-filter: blur(40px) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}

/* ── Chat messages ── */
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
[data-testid="stChatMessage"] pre, [data-testid="stChatMessage"] code {
    white-space: pre-wrap !important; word-break: break-word !important;
}

/* ── Chat input ── */
.stChatInputContainer, [data-testid="stChatInputContainer"] {
    background: rgba(20,20,35,0.90) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 20px !important;
}

/* ── Form inputs ── */
.stTextInput>div>div>input,
.stTextArea>div>textarea,
.stSelectbox>div>div>div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #f5f5f7 !important;
}

/* ── Selectbox dropdown ── */
[data-baseweb="select"] *, [data-baseweb="menu"] * {
    background-color: #12122a !important;
    color: #f5f5f7 !important;
}

/* ── Buttons ── */
.stButton>button {
    background: linear-gradient(180deg,
        rgba(255,255,255,0.10) 0%,
        rgba(255,255,255,0.02) 100%) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 18px !important;
    backdrop-filter: blur(20px) !important;
    color: #f5f5f7 !important;
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

/* ── Spinner / status ── */
[data-testid="stSpinner"] * { color: #00d4ff !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary { color: #f5f5f7 !important; }

/* ── st.success / st.info ── */
[data-testid="stAlert"] {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 10px !important;
    color: #f5f5f7 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }

/* ── Custom components ── */
.thinking-container {
    display: flex; align-items: center; gap: 8px; padding: 12px 16px;
    background: rgba(255,255,255,0.04); border-radius: 14px; margin: 8px 0;
    border-left: 3px solid #00d4ff;
}
.thinking-text { color: #00d4ff; font-size: 14px; font-weight: 600; }
.thinking-dots { display: flex; gap: 4px; }
.thinking-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #00d4ff; animation: tp 1.4s infinite;
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
    color: white; padding: 4px 12px; border-radius: 999px;
    font-size: 13px; font-weight: 700;
    box-shadow: 0 0 12px rgba(255,77,109,0.5);
    vertical-align: middle; margin-left: 10px;
}
.section-label {
    color: #00d4ff; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px; margin: 12px 0 6px;
}
.welcome-card {
    background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(123,47,247,0.08));
    border: 1px solid rgba(0,212,255,0.2); border-radius: 16px;
    padding: 12px 16px; margin-bottom: 8px; font-weight: 600;
    color: #2ecc71; font-size: 14px;
}
.source-badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; margin-top: 6px;
}
.src-pdf  { background:rgba(0,212,255,0.15); color:#00d4ff; border:1px solid rgba(0,212,255,0.3); }
.src-ai   { background:rgba(252,132,4,0.15); color:#fc8404; border:1px solid rgba(252,132,4,0.3); }
.src-ddg  { background:rgba(255,69,0,0.15);  color:#ff6b35; border:1px solid rgba(255,69,0,0.3); }
.src-wiki { background:rgba(52,152,219,0.15); color:#3498db; border:1px solid rgba(52,152,219,0.3); }
.src-calc { background:rgba(155,89,182,0.2);  color:#9b59b6; border:1px solid rgba(155,89,182,0.4); }
</style>
LEGACY DARK THEME DISABLED -->
""", unsafe_allow_html=True)

# =============================================================================
# GOOGLE KEEP-INSPIRED LIGHT THEME
# =============================================================================
ACCENT = st.session_state.accent_color
st.markdown(f"""
<style>
:root {{
    color-scheme: light !important;
    --accent: {ACCENT};
    --ink: #202124;
    --muted: #5f6368;
    --line: #e0e0e0;
    --surface: #ffffff;
    --canvas: #f6f7fb;
    --soft: color-mix(in srgb, var(--accent) 16%, white);
    --accent-strong: color-mix(in srgb, var(--accent) 78%, #5f4300);
    --shadow-1: 0 1px 2px rgba(60,64,67,.12), 0 1px 3px 1px rgba(60,64,67,.06);
    --shadow-2: 0 6px 18px rgba(60,64,67,.14);
}}
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    color-scheme: light !important;
    background: var(--canvas) !important;
    color: var(--ink) !important;
}}
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
.stDeployButton,
button[title="View source on GitHub"],
button[title="Fork this app"],
a[href*="github.com"],
footer {{ display: none !important; visibility: hidden !important; }}
/* Keep Streamlit's sidebar reopen control available after collapse. */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}}
.stApp {{
    background:
        radial-gradient(700px circle at 58% -10%, rgba(120,86,255,.10), transparent 58%),
        radial-gradient(600px circle at 90% 8%, rgba(0,183,255,.08), transparent 54%),
        var(--canvas) !important;
    color: var(--ink) !important;
    font-family: Inter, Roboto, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}}
[data-testid="stHeader"] {{
    background: rgba(255,255,255,.94) !important;
    border-bottom: 1px solid var(--line) !important;
    backdrop-filter: blur(14px) saturate(1.25) !important;
}}
[data-testid="stSidebar"] {{
    background: rgba(248,249,252,.97) !important;
    border-right: 1px solid #e7e8ee !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] * {{ color: var(--ink) !important; }}

/* Force every native and BaseWeb field back to a readable light surface. */
input, textarea, [contenteditable="true"],
[data-baseweb="input"], [data-baseweb="textarea"],
[data-baseweb="select"] > div,
[data-baseweb="base-input"] {{
    background: #ffffff !important;
    background-color: #ffffff !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--ink) !important;
}}
input::placeholder, textarea::placeholder {{
    color: #80868b !important;
    -webkit-text-fill-color: #80868b !important;
    opacity: 1 !important;
}}
[data-baseweb="popover"], [data-baseweb="menu"],
[role="listbox"], [role="option"] {{
    background: #ffffff !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
}}

/* Notes-like message cards */
[data-testid="stChatMessage"] {{
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    box-shadow: 0 1px 2px rgba(60,64,67,.10) !important;
    padding: 18px !important;
    margin-bottom: 14px !important;
}}
[data-testid="stChatMessage"]:hover {{
    box-shadow: 0 2px 8px rgba(60,64,67,.18) !important;
}}
[data-testid="stChatMessage"] * {{ color: var(--ink) !important; }}

/* Keep-style input tray */
.stChatInputContainer, [data-testid="stChatInputContainer"] {{
    background: #fff !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    box-shadow: 0 3px 10px rgba(60,64,67,.18) !important;
}}
[data-testid="stChatInputContainer"] > div,
[data-testid="stChatInputContainer"] form,
[data-testid="stChatInputContainer"] div[data-baseweb="textarea"] {{
    background: #ffffff !important;
}}
[data-testid="stChatInputContainer"] textarea {{ color: var(--ink) !important; }}

.stTextInput>div>div>input,
.stTextArea>div>textarea,
.stSelectbox>div>div>div {{
    background: #fff !important;
    border: 1px solid var(--line) !important;
    border-radius: 10px !important;
    color: var(--ink) !important;
}}
[data-baseweb="select"] *, [data-baseweb="menu"] * {{
    background-color: #fff !important;
    color: var(--ink) !important;
}}
.stButton>button {{
    background: #fff !important;
    border: 1px solid transparent !important;
    border-radius: 999px !important;
    color: var(--ink) !important;
    box-shadow: none !important;
    min-height: 42px !important;
    font-weight: 650 !important;
    transition: background-color .16s ease, border-color .16s ease, box-shadow .16s ease, transform .16s ease !important;
}}
.stButton>button:hover {{
    background: var(--soft) !important;
    border-color: transparent !important;
    color: var(--ink) !important;
    transform: none !important;
    box-shadow: none !important;
}}
.stButton>button[kind="primary"], button[kind="primary"] {{
    background: var(--accent) !important;
    color: #202124 !important;
    font-weight: 700 !important;
}}
.stButton>button:focus-visible,
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
[role="combobox"]:focus-visible {{
    outline: 3px solid color-mix(in srgb, var(--accent) 34%, transparent) !important;
    outline-offset: 2px !important;
}}
[data-testid="stSpinner"] * {{ color: var(--accent) !important; }}
[data-testid="stExpander"] {{
    background: #fff !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stAlert"] * {{ color: var(--ink) !important; }}
[data-testid="stAlert"] {{
    background: var(--soft) !important;
    border: 0 !important;
    border-radius: 10px !important;
}}
.thinking-container {{
    background: var(--soft) !important;
    border: 0 !important;
    border-left: 4px solid var(--accent) !important;
}}
.thinking-text {{ color: var(--ink) !important; }}
.thinking-dot {{ background: var(--accent) !important; }}
.beta-badge {{
    background: var(--accent) !important;
    color: #202124 !important;
    box-shadow: none !important;
}}
.section-label {{ color: var(--muted) !important; }}
.welcome-card {{
    background: var(--soft) !important;
    border: 1px solid color-mix(in srgb, var(--accent) 45%, white) !important;
    color: var(--ink) !important;
}}
.source-badge {{
    background: var(--soft) !important;
    color: var(--ink) !important;
    border: 1px solid color-mix(in srgb, var(--accent) 45%, white) !important;
}}
.stApp [style*="color:#00d4ff"] {{ color: var(--ink) !important; }}
.stApp [style*="color:rgba(255,255,255"] {{ color: var(--muted) !important; }}
.stApp [style*="background:rgba(255,255,255,0.05)"] {{
    background: #fff !important;
    border-color: var(--line) !important;
    box-shadow: 0 3px 10px rgba(60,64,67,.16) !important;
}}
hr {{ border-color: var(--line) !important; }}
::-webkit-scrollbar-thumb {{ background: #dadce0 !important; }}
@media (max-width: 700px) {{
    [data-testid="stChatMessage"] {{ padding: 14px !important; }}
}}

/* ── 2.0 visual polish ─────────────────────────────────────────────── */
[data-testid="stAppViewBlockContainer"] {{
    max-width: 980px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 7rem !important;
}}
[data-testid="stSidebarContent"] {{ padding: 1.1rem .75rem 2rem !important; }}
[data-testid="stSidebar"] {{
    min-width: 278px !important;
    box-shadow: 10px 0 35px rgba(32,33,36,.035) !important;
}}
[data-testid="stSidebar"] hr {{ margin: .75rem 0 !important; }}
[data-testid="stSidebar"] .stButton > button {{
    min-height: 43px !important;
    justify-content: flex-start !important;
    padding: .55rem .8rem !important;
    font-size: .91rem !important;
    transition: background .18s ease, transform .18s ease !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    transform: translateX(3px) !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    justify-content: center !important;
    min-height: 46px !important;
    box-shadow: 0 5px 16px color-mix(in srgb, var(--accent) 25%, transparent) !important;
}}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] input {{
    min-height: 44px !important;
    border-radius: 12px !important;
}}
.section-label {{
    font-size: .68rem !important;
    letter-spacing: .12em !important;
    margin: 1.15rem .55rem .45rem !important;
}}
.welcome-card {{
    border-radius: 18px !important;
    padding: 15px 16px !important;
    line-height: 1.55 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.7) !important;
}}
.smartloop-hero {{
    position: relative;
    overflow: hidden;
    text-align: left;
    padding: 12px 4px 18px;
    margin: 0 0 12px;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
}}
.smartloop-hero::after {{
    display: none;
}}
.hero-kicker {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,.7);
    border: 1px solid #e4e6ec;
    color: var(--muted);
    font-size: .72rem;
    font-weight: 750;
    letter-spacing: .06em;
    text-transform: uppercase;
}}
.hero-title {{
    margin: 14px 0 5px;
    color: var(--ink);
    font-size: clamp(1.9rem, 4vw, 2.65rem);
    line-height: 1.08;
    letter-spacing: -.045em;
    font-weight: 780;
}}
.hero-title span {{
    background: linear-gradient(90deg, #6d4aff, #0078d4 58%, #0097a7);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}}
.hero-copy {{ margin: 0; color: var(--muted); font-size: 1rem; }}
.quick-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: -6px 0 22px;
}}
.quick-card {{
    min-height: 96px;
    padding: 16px;
    border: 1px solid #e3e5e7;
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 2px 7px rgba(60,64,67,.055);
    transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}}
.quick-card:hover {{
    transform: translateY(-3px);
    border-color: color-mix(in srgb, var(--accent) 55%, #ddd);
    box-shadow: 0 9px 22px rgba(60,64,67,.11);
}}
.quick-card b {{ display:block; margin: 7px 0 2px; font-size: .91rem; color: var(--ink); }}
.quick-card span {{ color: var(--muted); font-size: .77rem; line-height: 1.35; }}
.quick-icon {{ font-size: 1.25rem; }}
/* Real interactive quick-prompt buttons */
.st-key-quick_actions {{ margin: -7px 0 22px !important; }}
.st-key-quick_actions [data-testid="stHorizontalBlock"] {{ gap: 12px !important; }}
.st-key-quick_actions .stButton > button {{
    position: relative !important;
    min-height: 118px !important;
    width: 100% !important;
    justify-content: flex-start !important;
    align-items: flex-start !important;
    padding: 18px 17px !important;
    white-space: pre-line !important;
    text-align: left !important;
    line-height: 1.48 !important;
    border: 1px solid #e4e6e8 !important;
    border-radius: 20px !important;
    background:
        radial-gradient(circle at 92% 12%, color-mix(in srgb, var(--accent) 19%, white) 0 11%, transparent 12%),
        linear-gradient(145deg, #fff 35%, color-mix(in srgb, var(--accent) 6%, white)) !important;
    box-shadow: 0 3px 10px rgba(60,64,67,.07), inset 0 1px 0 rgba(255,255,255,.9) !important;
    font-size: .84rem !important;
    font-weight: 650 !important;
    color: var(--ink) !important;
    overflow: hidden !important;
    transition: transform .2s cubic-bezier(.2,.8,.2,1), box-shadow .2s ease, border-color .2s ease !important;
}}
.st-key-quick_actions .stButton > button::after {{
    content: "Try it  →";
    position: absolute;
    left: 17px;
    bottom: 13px;
    color: color-mix(in srgb, var(--accent) 72%, #403000);
    font-size: .69rem;
    font-weight: 800;
    letter-spacing: .04em;
    opacity: .78;
}}
.st-key-quick_actions .stButton > button:hover {{
    transform: translateY(-5px) scale(1.012) !important;
    border-color: color-mix(in srgb, var(--accent) 62%, #ddd) !important;
    background:
        radial-gradient(circle at 92% 12%, color-mix(in srgb, var(--accent) 30%, white) 0 13%, transparent 14%),
        linear-gradient(145deg, #fff 20%, color-mix(in srgb, var(--accent) 11%, white)) !important;
    box-shadow: 0 15px 32px rgba(60,64,67,.13), 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent) !important;
}}
.st-key-quick_actions .stButton > button:active {{
    transform: translateY(-1px) scale(.985) !important;
    box-shadow: 0 5px 14px rgba(60,64,67,.12) !important;
}}
[data-testid="stChatMessage"] {{
    border-radius: 22px !important;
    padding: 20px 22px !important;
    animation: cardIn .25s ease both;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
    background: #eef0f5 !important;
    border-color: transparent !important;
    margin-left: clamp(1rem, 10vw, 7rem) !important;
    box-shadow: none !important;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
    background: rgba(255,255,255,.94) !important;
    border-color: #e7e8ee !important;
}}
[data-testid="stChatMessage"]:hover {{
    border-color: color-mix(in srgb, var(--accent) 32%, var(--line)) !important;
    box-shadow: var(--shadow-2) !important;
}}
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3 {{
    letter-spacing: -.02em !important;
    line-height: 1.25 !important;
}}
[data-testid="stChatMessage"] p {{ line-height: 1.68 !important; }}
[data-testid="stChatMessage"] ul,
[data-testid="stChatMessage"] ol {{ padding-left: 1.3rem !important; }}
[data-testid="stChatMessage"] pre {{
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    background: #f6f8fa !important;
    overflow-x: auto !important;
}}
[data-testid="stChatMessage"] code {{
    border-radius: 6px !important;
    font-size: .9em !important;
}}
[data-testid="stChatInput"] {{ max-width: 1000px !important; margin: 0 auto 10px !important; }}
[data-testid="stChatInputContainer"] {{
    min-height: 62px !important;
    border-radius: 24px !important;
    border-color: #dfe1e8 !important;
    box-shadow: 0 12px 36px rgba(48,52,64,.14), 0 0 0 1px rgba(255,255,255,.8) inset !important;
    transition: border-color .2s ease, box-shadow .2s ease !important;
}}
[data-testid="stChatInputContainer"]:focus-within {{
    border-color: var(--accent) !important;
    box-shadow: 0 12px 38px rgba(60,64,67,.16), 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent) !important;
}}
[data-testid="stChatInputContainer"] textarea {{ font-size: .98rem !important; }}
[data-testid="stExpander"] {{ border-radius: 16px !important; overflow: hidden !important; }}
[data-testid="stExpander"] summary {{ min-height: 46px !important; }}
.beta-badge {{
    vertical-align: 6px !important;
    padding: 5px 9px !important;
    font-size: .63rem !important;
    letter-spacing: .08em !important;
}}
.source-badge {{ border-radius: 999px !important; padding: 4px 10px !important; }}
.smartloop-hero {{ animation: heroIn .45s cubic-bezier(.2,.8,.2,1) both; }}
.smartloop-hero::before {{
    display: none;
}}
@keyframes heroIn {{
    from {{ opacity: 0; transform: translateY(-9px) scale(.99); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
@keyframes cardIn {{
    from {{ opacity: 0; transform: translateY(7px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@media (max-width: 700px) {{
    [data-testid="stAppViewBlockContainer"] {{ padding: .8rem .7rem 6rem !important; }}
    .smartloop-hero {{ padding: 8px 2px 14px; margin-bottom: 8px; }}
    .hero-title {{ font-size: clamp(1.8rem, 10vw, 2.45rem); letter-spacing: -.045em; }}
    .hero-copy {{ font-size: .92rem; line-height: 1.5; }}
    .smartloop-hero::after {{ display:none; }}
    .quick-grid {{ grid-template-columns: 1fr; }}
    .quick-card {{ min-height: auto; }}
    .st-key-quick_actions [data-testid="stHorizontalBlock"] {{ flex-direction: column !important; }}
    .st-key-quick_actions [data-testid="column"] {{ width: 100% !important; }}
    .st-key-quick_actions .stButton > button {{ min-height: 105px !important; }}
    [data-testid="stChatMessage"] {{ padding: 16px !important; border-radius: 16px !important; }}
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{ margin-left: 1rem !important; }}
    [data-testid="stChatInputContainer"] {{ min-height: 56px !important; border-radius: 18px !important; }}
}}
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        scroll-behavior: auto !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
    }}
}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# API KEYS
# =============================================================================
def _collect_keys(prefix):
    keys = []
    for i in range(1, 6):
        k = st.secrets.get(f"{prefix}_{i}")
        if k:
            keys.append(k)
    return keys

ALL_OPENAI_KEYS = _collect_keys("OPENAI_API_KEY")
ALL_GOOGLE_KEYS = _collect_keys("GOOGLE_API_KEY")
MY_API_KEY      = st.secrets.get("MY_API_KEY")

if not ALL_OPENAI_KEYS and not ALL_GOOGLE_KEYS and not MY_API_KEY:
    st.error("No API keys found.")
    st.stop()

_openai_cycle = itertools.cycle(ALL_OPENAI_KEYS) if ALL_OPENAI_KEYS else None
_google_cycle = itertools.cycle(ALL_GOOGLE_KEYS) if ALL_GOOGLE_KEYS else None

# =============================================================================
# REFUSAL DETECTOR
# =============================================================================
REFUSAL_PHRASES = [
    "i cannot","i can't","i am unable","i'm unable",
    "i don't have","i do not have","not able to",
    "cannot provide","unable to provide","cannot answer",
    "no information","not found in","not covered",
    "beyond my","outside my","i'm sorry, but",
    "i am sorry","as an ai","as a language model",
    "i lack","i cannot find",
]

def is_refusal(text):
    low = text.lower()
    return any(p in low for p in REFUSAL_PHRASES)

# =============================================================================
# LOVABLE / CUSTOM API
# =============================================================================
def call_my_api(messages):
    if not MY_API_KEY:
        return None
    try:
        headers  = {
            "Authorization": f"Bearer {MY_API_KEY}",
            "Content-Type":  "application/json"
        }
        response = requests.post(
            "https://raujzsawwpmixwlcgcgs.supabase.co/functions/v1/public-ai-api",
            headers=headers, json={"messages": messages}, timeout=45
        )
        data = response.json()
        text = ""
        if isinstance(data, dict):
            text = (
                data.get("response") or data.get("content") or
                data.get("message") or data.get("reply") or ""
            )
            if not text and "choices" in data:
                text = data["choices"][0]["message"]["content"]
        elif isinstance(data, str):
            text = data
        text = str(text).strip()
        if len(text) > 10 and not is_refusal(text):
            return text
    except Exception as e:
        print(f"My API error: {e}")
    return None

# =============================================================================
# MAIN LLM CALLER
# =============================================================================
def call_llm(messages, max_tokens=900, temperature=0.3, stream_ph=None):

    # Gemini
    if _google_cycle:
        for _ in range(len(ALL_GOOGLE_KEYS)):
            try:
                client = genai.Client(api_key=next(_google_cycle))
                prompt = "\n\n".join(
                    f"[{m['role'].upper()}]: {m['content']}" for m in messages
                )
                r   = client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt
                )
                txt = (r.text or "").strip()
                if len(txt) > 15 and not is_refusal(txt):
                    if stream_ph:
                        stream_ph.markdown(txt)
                    return txt
            except Exception as e:
                print(f"Gemini error: {e}")
                time.sleep(0.3)

    # OpenAI
    if _openai_cycle:
        for _ in range(len(ALL_OPENAI_KEYS)):
            try:
                client = OpenAI(api_key=next(_openai_cycle))
                if stream_ph:
                    stream  = client.chat.completions.create(
                        model="gpt-3.5-turbo", messages=messages,
                        max_tokens=max_tokens, temperature=temperature, stream=True,
                    )
                    ans = ""
                    for chunk in stream:
                        piece = chunk.choices[0].delta.content or ""
                        ans  += piece
                        stream_ph.markdown(ans + "▌")
                    stream_ph.markdown(ans)
                    if len(ans) > 15 and not is_refusal(ans):
                        return ans
                    stream_ph.empty()
                else:
                    r   = client.chat.completions.create(
                        model="gpt-3.5-turbo", messages=messages,
                        max_tokens=max_tokens, temperature=temperature,
                    )
                    ans = r.choices[0].message.content.strip()
                    if len(ans) > 15 and not is_refusal(ans):
                        return ans
            except Exception as e:
                print(f"OpenAI error: {e}")
                time.sleep(0.3)

    # Custom API fallback
    try:
        ans = call_my_api(messages)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans
    except Exception as e:
        print(f"My API failed: {e}")

    # Hard "never refuse" retry
    fallback_msgs = [
        {"role":"system","content":"You are a helpful tutor. Always answer completely."}
    ] + [m for m in messages if m["role"] != "system"]

    if _openai_cycle:
        for _ in range(len(ALL_OPENAI_KEYS)):
            try:
                client = OpenAI(api_key=next(_openai_cycle))
                r   = client.chat.completions.create(
                    model="gpt-3.5-turbo", messages=fallback_msgs,
                    max_tokens=max_tokens, temperature=0.5,
                )
                ans = r.choices[0].message.content.strip()
                if len(ans) > 15:
                    if stream_ph:
                        stream_ph.markdown(ans)
                    return ans
            except Exception as e:
                print(f"Fallback error: {e}")
                time.sleep(0.3)
    return None

def call_llm_short(prompt, max_tokens=60):
    return call_llm(
        [{"role":"user","content":prompt}],
        max_tokens=max_tokens, temperature=0
    )

# =============================================================================
# GRADE SELECTION
# =============================================================================
if "grade" not in st.session_state:
    st.session_state.grade = None
if "grade_loading" not in st.session_state:
    st.session_state.grade_loading = False

if st.session_state.grade is None:

    # ── Locked loading screen — shown after button click, blocks all interaction ──
    if st.session_state.grade_loading:
        st.markdown(f"""
<div style='max-width:400px;margin:100px auto;background:rgba(255,255,255,0.05);
border:1px solid rgba(255,255,255,0.15);border-radius:28px;padding:40px;
text-align:center;backdrop-filter:blur(40px);'>
<div style='font-size:40px;margin-bottom:16px;'>🧠</div>
<div style='font-size:24px;font-weight:800;color:#00d4ff;margin-bottom:20px;'>
SmartLoop AI</div>
<div class='thinking-container' style='justify-content:center;'>
    <span class='thinking-text'>Setting up your Grade {st.session_state._pending_grade} experience</span>
    <div class='thinking-dots'>
        <div class='thinking-dot'></div>
        <div class='thinking-dot'></div>
        <div class='thinking-dot'></div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)
        # Commit the grade and rerun into the main app
        st.session_state.grade = st.session_state._pending_grade
        st.session_state.grade_loading = False
        time.sleep(0.3)
        st.rerun()
        st.stop()

    # ── Normal selection screen ──
    st.markdown("""
<div style='max-width:400px;margin:100px auto;background:rgba(255,255,255,0.05);
border:1px solid rgba(255,255,255,0.15);border-radius:28px;padding:40px;
text-align:center;backdrop-filter:blur(40px);'>
<div style='font-size:40px;margin-bottom:12px;'>🧠</div>
<div style='font-size:28px;font-weight:800;color:#00d4ff;margin-bottom:6px;'>SmartLoop AI</div>
<div style='color:rgba(255,255,255,0.5);margin-bottom:28px;font-size:15px;'>
Select your grade to get started</div></div>
""", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        grade = st.selectbox(
            "Grade", [f"Grade {i}" for i in range(1, 11)],
            index=5, label_visibility="collapsed"
        )
        if st.button("Get Started →", use_container_width=True, type="primary"):
            # Store pending grade and flip to loading screen — no selectbox shown
            st.session_state._pending_grade = int(grade.split()[1])
            st.session_state.grade_loading  = True
            st.rerun()
    st.stop()

# =============================================================================
# PDF LOADING
# =============================================================================
def get_allowed_grades(grade):
    return [grade, grade + 1] if grade < 10 else [grade]

def grade_matches_file(fname, allowed_grades):
    name = fname.lower().replace(".pdf", "")
    for g in allowed_grades:
        if any(p in name for p in [
            str(g), f"grade{g}", f"grade_{g}", f"class{g}",
            f"std{g}", f"g{g}", f"{g}th", f"{g}st", f"{g}nd", f"{g}rd"
        ]):
            return True
    return False

def extract_pdf(fname):
    chunks = []
    try:
        doc = fitz.open(fname)
        for page_num, page in enumerate(doc):
            try:
                blocks = page.get_text("dict")["blocks"]
                lines  = []
                for block in blocks:
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            words   = []
                            prev_x1 = None
                            for span in line.get("spans", []):
                                span_text = span.get("text","").strip()
                                if not span_text:
                                    continue
                                if prev_x1 is not None:
                                    gap = span["origin"][0] - prev_x1
                                    if gap > 2:
                                        words.append(" ")
                                words.append(span_text)
                                prev_x1 = span["bbox"][2]
                            line_text = "".join(words).strip()
                            if line_text:
                                lines.append(line_text)
                text = "\n".join(lines).strip()
            except Exception:
                text = page.get_text().strip()

            if len(text) > 60:
                text  = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
                text  = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)
                words = set(re.sub(r'[^a-z0-9 ]',' ',text.lower()).split())
                chunks.append({
                    "text":  text[:1500],
                    "words": words,
                    "file":  fname,
                    "page":  page_num + 1
                })
        doc.close()
    except Exception as e:
        print(f"PDF error {fname}: {e}")
    return chunks

@st.cache_resource(show_spinner=False)
def load_all_pdfs(grade):
    allowed     = get_allowed_grades(grade)
    pdf_files   = [f for f in os.listdir(".") if f.endswith(".pdf")]
    grade_files = [f for f in pdf_files if grade_matches_file(f, allowed)]
    if not grade_files:
        grade_files = pdf_files
    all_chunks = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(extract_pdf, f): f for f in grade_files}
        for future in as_completed(futures):
            all_chunks.extend(future.result())
    return all_chunks

with st.spinner(""):
    thinking_load = st.empty()
    thinking_load.markdown("""
<div class="thinking-container" style="max-width:500px;margin:0 auto;">
    <span class="thinking-text">📚 Loading your textbooks</span>
    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)
    PDF_CHUNKS = load_all_pdfs(st.session_state.grade)
    thinking_load.empty()

# =============================================================================
# SESSION STATE
# =============================================================================
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# Restore and continuously save chats in this browser. This survives Streamlit
# restarts and page refreshes without requiring an account.
if "browser_chats_loaded" not in st.session_state:
    st.session_state.browser_chats_loaded = False

stored_chat_data = streamlit_js_eval(
    js_expressions="""
    (() => {
        try {
            const raw = localStorage.getItem('smartloop_chats_v1');
            return raw ? JSON.parse(raw) : {chats: {'Chat 1': []}, current_chat: 'Chat 1'};
        } catch (error) {
            return {chats: {'Chat 1': []}, current_chat: 'Chat 1'};
        }
    })()
    """,
    key="load_smartloop_chats"
)

if not st.session_state.browser_chats_loaded and isinstance(stored_chat_data, dict):
    saved_chats = stored_chat_data.get("chats")
    saved_current = stored_chat_data.get("current_chat")
    if isinstance(saved_chats, dict) and saved_chats:
        st.session_state.chats = saved_chats
        st.session_state.current_chat = (
            saved_current if saved_current in saved_chats else next(iter(saved_chats))
        )
    st.session_state.browser_chats_loaded = True

def save_chats_to_browser(key_prefix="save"):
    """Queue the current chat collection for durable browser-local storage."""
    browser_payload = json.dumps({
        "chats": st.session_state.chats,
        "current_chat": st.session_state.current_chat,
    }, ensure_ascii=False)
    payload_key = hashlib.sha256(browser_payload.encode("utf-8")).hexdigest()[:16]
    streamlit_js_eval(
        js_expressions=(
            "(() => { localStorage.setItem('smartloop_chats_v1', "
            + json.dumps(browser_payload)
            + "); return true; })()"
        ),
        key=f"{key_prefix}_smartloop_chats_{payload_key}"
    )

if st.session_state.browser_chats_loaded:
    save_chats_to_browser()

# =============================================================================
# MATH SOLVER
# =============================================================================
def is_pure_calc(q):
    return bool(re.fullmatch(r"[\d\.\+\-\*\/\(\)\s\^%]+", q.strip()))

def solve_math(q):
    try:
        result = eval(
            q.strip().replace("^","**").replace(" ",""),
            {"__builtins__": None}, {}
        )
        return f"**= {round(result, 8)}**", "calc"
    except:
        return None, None

# =============================================================================
# STOPWORDS + KEYWORD SEARCH
# =============================================================================
STOPWORDS = {
    "what","is","are","how","why","when","who","the","a","an",
    "of","in","to","and","does","do","explain","define","me",
    "about","give","please","describe","tell","example","examples",
    "find","solve","calculate","show","write","give","some","for",
    "questions","question","on","from","chapter","topic","subject",
    "create","make","generate","write","list","provide"
}

def keyword_search(q):
    if not PDF_CHUNKS:
        return []
    q_words = set(re.sub(r'[^a-z0-9 ]',' ',q.lower()).split()) - STOPWORDS
    if not q_words:
        return []
    scored = []
    for chunk in PDF_CHUNKS:
        score = len(q_words & chunk["words"])
        if score >= 1:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:8]

# =============================================================================
# QUESTION REQUEST DETECTOR
# =============================================================================
QUESTION_REQUEST_WORDS = [
    "give me questions","give questions","make questions",
    "create questions","generate questions","write questions",
    "some questions","practice questions","exam questions",
    "test questions","quiz","questions on","questions about",
    "questions from","give me some","create a test",
    "make a test","make a quiz","create a quiz",
]

def is_question_request(q):
    ql = q.lower()
    return any(phrase in ql for phrase in QUESTION_REQUEST_WORDS)

def requested_grade(q):
    """Respect an explicit grade in the prompt without changing app settings."""
    match = re.search(r"\bgrade\s*(10|[1-9])\b|\b(10|[1-9])(?:st|nd|rd|th)[- ]grade\b", q, re.I)
    if not match:
        return None
    return int(match.group(1) or match.group(2))

def wants_original_content(q):
    """Detect when the student explicitly asks us not to use a textbook."""
    ql = q.lower()
    original_phrases = (
        "create your own", "make your own", "write your own",
        "original text", "original passage", "new passage",
        "don't use the textbook", "do not use the textbook",
        "dont use the textbook", "not from the textbook",
        "without the textbook", "not from my book",
    )
    return any(phrase in ql for phrase in original_phrases)

# =============================================================================
# AI JUDGE
# =============================================================================
def judge_single(args):
    chunk, question, key = args
    prompt = (
        f"Question: {question}\n\nExcerpt:\n{chunk['text'][:500]}\n\n"
        f"Does this excerpt contain teaching content (definitions, explanations) "
        f"relevant to the question? Reply ONLY: YES or NO"
    )
    try:
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=3, temperature=0
        )
        return "YES" in r.choices[0].message.content.upper(), chunk
    except:
        # A failed relevance check must not silently approve an unrelated book.
        return False, chunk

def parallel_judge(candidates, question):
    if not candidates:
        return []
    if not ALL_OPENAI_KEYS:
        return [c for _, c in candidates[:4]]
    key_list = list(itertools.islice(
        itertools.cycle(ALL_OPENAI_KEYS), len(candidates)
    ))
    tasks = [
        (chunk, question, key_list[i])
        for i, (_, chunk) in enumerate(candidates)
    ]
    good = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = [ex.submit(judge_single, t) for t in tasks]
        for f in as_completed(futures):
            try:
                ok, chunk = f.result()
                if ok:
                    good.append(chunk)
            except:
                pass
    return good

# =============================================================================
# ZERO-API TEXT EXTRACTION
# =============================================================================
def extract_answer_from_text(question, chunks, grade):
    q_words = set(
        w for w in re.sub(r'[^a-z0-9 ]',' ',question.lower()).split()
        if w not in STOPWORDS and len(w) > 1
    )
    sentence_scores = []
    for chunk in chunks[:6]:
        for sent in re.split(r'(?<=[.!?])\s+', chunk["text"]):
            if len(sent.split()) < 6:
                continue
            sent_words = set(re.sub(r'[^a-z0-9 ]',' ',sent.lower()).split())
            overlap    = len(q_words & sent_words)
            if overlap > 0:
                sentence_scores.append((overlap, sent.strip()))
    sentence_scores.sort(key=lambda x: x[0], reverse=True)
    seen, top = set(), []
    for _, sent in sentence_scores:
        key = sent[:40]
        if key not in seen:
            seen.add(key)
            top.append(sent)
        if len(top) >= 6:
            break
    if not top and chunks:
        top = [chunks[0]["text"][:600]]
    if not top:
        return None
    src    = chunks[0]["file"]
    joined = " ".join(top)
    prefix = (
        "Here's what your textbook says:\n\n" if grade <= 4 else
        "Your textbook explains:\n\n"          if grade <= 7 else
        "According to your textbook:\n\n"
    )
    return f"{prefix}{joined}\n\n*📖 Source: {src}*"

# =============================================================================
# GRADE STYLE
# =============================================================================
def grade_style(g):
    if g <= 3:
        return "Use very simple words, short sentences, fun examples. Like explaining to a young child."
    elif g <= 6:
        return "Use clear simple language with relatable everyday examples."
    elif g <= 8:
        return "Use clear academic language with key terms and worked examples."
    else:
        return "Use detailed academic language suitable for high school."

# =============================================================================
# THINKING ANIMATION
# =============================================================================
def update_phase(ph, text):
    ph.markdown(f"""
<div class="thinking-container">
    <span class="thinking-text">{text}</span>
    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>""", unsafe_allow_html=True)

# =============================================================================
# UNDERSTAND INTENT
# =============================================================================
def understand_intent(question, history):
    hist = "".join([
        f"{'Student' if m['role']=='user' else 'AI'}: {m.get('content','')[:150]}\n"
        for m in history[-4:]
    ])
    prompt = (
        f"A student asked: \"{question}\"\n"
        f"Recent conversation:\n{hist}\n\n"
        "In ONE short sentence, what does the student want to learn? "
        "Be specific. Example: 'Understand what decimals are and how they work.'\nIntent:"
    )
    result = call_llm_short(prompt, max_tokens=40)
    return result.strip() if result else question

# =============================================================================
# SAFETY CHECK
# =============================================================================
BAD_INTENT_PATTERNS = [
    r"\b(?:build|make|create)\s+(?:a\s+)?(?:bomb|weapon|explosive)",
    r"\bhow\s+to\s+(?:hack|steal|attack|hurt|poison)\b",
    r"\b(?:adult content|pornograph\w*|sexual content)\b",
    r"\b(?:suicide|self[- ]harm)\b",
]

def is_bad_intent(question, intent):
    combined = (question + " " + (intent or "")).lower()
    return any(re.search(pattern, combined, re.I) for pattern in BAD_INTENT_PATTERNS)

def bad_intent_response(grade):
    if grade <= 4:
        return "I can only help with school subjects! Ask me about maths, science, or anything from your textbooks. 😊"
    elif grade <= 7:
        return "I'm an educational tutor and can only help with school topics. Please ask me about your subjects!"
    else:
        return "I can only assist with academic and educational content. Please keep questions related to your studies."

# =============================================================================
# CONTEXT RELEVANCE CHECK
# =============================================================================
def context_is_relevant(intent, chunks):
    if not chunks:
        return False
    if not ALL_OPENAI_KEYS and not ALL_GOOGLE_KEYS:
        intent_words = set(
            w for w in re.sub(r'[^a-z0-9 ]',' ',intent.lower()).split()
            if w not in STOPWORDS and len(w) > 2
        )
        combined = " ".join(c["text"][:300] for c in chunks[:3]).lower()
        return sum(1 for w in intent_words if w in combined) >= 2
    sample = "\n---\n".join(c["text"][:400] for c in chunks[:3])
    prompt = (
        f"Student intent: {intent}\n\n"
        f"Textbook excerpts:\n{sample}\n\n"
        "Do these excerpts contain actual teaching content — definitions, "
        "explanations, or worked examples — that directly teaches this topic?\n"
        "Answer ONLY: YES or NO"
    )
    result = call_llm_short(prompt, max_tokens=3)
    return bool(result and "YES" in result.upper())

# =============================================================================
# GENERATE QUESTIONS
# =============================================================================
def generate_questions(question, chunks, grade, history, stream_ph=None):
    style      = grade_style(grade)
    topic_prompt = (
        f"The student asked: \"{question}\"\n"
        "What subject and topic/chapter are they asking questions about? "
        "Reply in format: Subject: X | Topic: Y\n"
        "If unclear, make a reasonable guess."
    )
    topic_info = call_llm_short(topic_prompt, max_tokens=30) or "General"

    if chunks:
        context = "\n\n---\n\n".join(c["text"] for c in chunks[:4])
        context_instruction = (
            f"Use the following textbook content as the basis for your questions:\n\n"
            f"{context}\n\nGenerate questions that test understanding of this content."
        )
        src = chunks[0]["file"]
    else:
        context_instruction = (
            f"No specific textbook content is available. "
            f"Generate realistic, curriculum-appropriate questions based on your knowledge of: {topic_info}"
        )
        src = None

    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert tutor for Grade {grade}. {style}\n\n"
                "Generate practice questions when asked.\n"
                "RULES:\n"
                "- Follow every stated topic, format, source, and difficulty requirement\n"
                "- If the student requests an original text or passage, invent one and never use textbook material\n"
                "- Include only the question types and writing tasks the student requested\n"
                "- Number each question clearly\n"
                "- Add answers at the end unless the student asks for a test without answers\n"
                f"- Make questions appropriate for Grade {grade}\n"
                "- NEVER refuse"
            )
        },
        {
            "role": "user",
            "content": (
                f"Topic info: {topic_info}\n\n"
                f"{context_instruction}\n\n"
                f"Student request: {question}\n\nGenerate the questions now:"
            )
        }
    ]
    ans = call_llm(messages, max_tokens=1000, temperature=0.5, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "pdf" if src else "ai", src
    return None, None, None

# =============================================================================
# TIER 1 — PDF ANSWER
# =============================================================================
def answer_from_pdf(question, intent, chunks, grade, history, stream_ph=None):
    src     = chunks[0]["file"]
    style   = grade_style(grade)
    hist    = "".join([
        f"{'Student' if m['role']=='user' else 'SmartLoop'}: {m.get('content','')}\n"
        for m in history[-4:]
    ])
    context = "\n\n---\n\n".join(c["text"] for c in chunks[:4])
    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert tutor for Grade {grade}. {style}\n\n"
                f"The student wants to: {intent}\n\n"
                "RULES:\n"
                "- Use the textbook content as your knowledge source.\n"
                "- Write a clear, friendly EXPLANATION in your own words.\n"
                "- Structure: definition → real-world example → how it works.\n"
                "- Do NOT copy raw text, exercise lists, page numbers, or file names.\n"
                "- Do NOT output answer keys or table of contents.\n"
                "- NEVER refuse or say you cannot answer."
            )
        },
        {
            "role": "user",
            "content": (
                f"TEXTBOOK CONTENT:\n{context}\n\n"
                f"CONVERSATION:\n{hist}\n\n"
                f"QUESTION: {question}\nAnswer:"
            )
        }
    ]
    ans = call_llm(messages, max_tokens=800, temperature=0.3, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "pdf", src
    # Zero-API fallback
    fallback = extract_answer_from_text(question, chunks, grade)
    if fallback:
        if stream_ph:
            stream_ph.markdown(fallback)
        return fallback, "pdf", src
    return None, None, None

# =============================================================================
# TIER 2 — AI ANSWER
# =============================================================================
def answer_from_ai(question, intent, grade, history, stream_ph=None):
    style    = grade_style(grade)
    messages = [
        {
            "role": "system",
            "content": (
                f"You are SmartLoop AI, expert academic tutor for Grade {grade}. {style}\n\n"
                f"The student wants to: {intent}\n\n"
                "Give a clear, complete, friendly explanation.\n"
                "Structure: definition → real-world example → how it works.\n"
                "NEVER refuse or say you cannot answer."
            )
        }
    ]
    for m in history[-4:]:
        messages.append({"role": m["role"], "content": m.get("content","")})
    messages.append({"role":"user","content":question})
    ans = call_llm(messages, max_tokens=800, temperature=0.4, stream_ph=stream_ph)
    if ans and len(ans) > 20:
        return ans, "ai", None
    return None, None, None

# =============================================================================
# TIER 3 — DUCKDUCKGO
# =============================================================================
BAD_CONTENT = [
    "comic","marvel","dc comics","film","movie","tv series",
    "television","album","song","band","actor","actress",
    "footballer","celebrity"
]

def answer_from_duckduckgo(question):
    try:
        headers  = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
        search_q = re.sub(
            r"(what is|what are|explain|define|how does|tell me about|describe)",
            "", question.lower()
        ).strip()
        data = requests.get(
            f"https://api.duckduckgo.com/?q={requests.utils.quote(search_q + ' school definition')}&format=json&no_html=1&skip_disambig=1",
            headers=headers, timeout=8
        ).json()
        result_text = data.get("AbstractText") or data.get("Answer") or data.get("Definition") or ""
        if not result_text and data.get("RelatedTopics"):
            result_text = " ".join(
                t["Text"] for t in data["RelatedTopics"][:3]
                if isinstance(t, dict) and t.get("Text")
            )
        if len(result_text) > 40 and not any(b in result_text.lower() for b in BAD_CONTENT):
            return result_text, "ddg", None
        soup = BeautifulSoup(
            requests.get(
                f"https://html.duckduckgo.com/html/?q={requests.utils.quote(search_q + ' academic definition school')}",
                headers=headers, timeout=8
            ).text, "html.parser"
        )
        snippets = [
            r.get_text(strip=True) for r in soup.select(".result__snippet")[:5]
            if len(r.get_text(strip=True)) > 40
            and not any(b in r.get_text(strip=True).lower() for b in BAD_CONTENT)
        ]
        if snippets:
            combined = " ".join(snippets[:2])
            if len(combined) > 50:
                return combined, "ddg", None
    except Exception as e:
        print(f"DDG error: {e}")
    return None, None, None

# =============================================================================
# TIER 4 — WIKIPEDIA
# =============================================================================
def answer_from_wiki(question):
    try:
        search_q = re.sub(
            r"(what is|what are|explain|define|how does|tell me about|describe)",
            "", question.lower()
        ).strip()
        results = wikipedia.search(search_q + " mathematics science", results=5)
        academic_kw = [
            "physics","chemistry","biology","mathematics","science",
            "history","geography","economics","force","energy","cell",
            "atom","equation","decimal","fraction","geometry","algebra"
        ]
        best = next(
            (r for r in results if any(k in r.lower() for k in academic_kw)),
            results[0] if results else None
        )
        if not best:
            return None, None, None
        summary = wikipedia.summary(best, sentences=3)
        if any(b in summary.lower() for b in BAD_CONTENT + [
            "may refer to","disambiguation","is a list"
        ]):
            return None, None, None
        return summary, "wiki", None
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            bad  = ["film","comic","song","album","band","tv"]
            best = next(
                (o for o in e.options if not any(b in o.lower() for b in bad)),
                e.options[0] if e.options else None
            )
            if not best:
                return None, None, None
            summary = wikipedia.summary(best, sentences=3)
            if any(b in summary.lower() for b in ["comic","marvel","film"]):
                return None, None, None
            return summary, "wiki", None
        except:
            return None, None, None
    except:
        return None, None, None

# =============================================================================
# MAIN PIPELINE
# =============================================================================
def smartloop(question, grade, history, thinking_ph, stream_ph=None):

    # A grade written in the request takes priority for that answer only.
    target_grade = requested_grade(question) or grade

    if is_pure_calc(question):
        update_phase(thinking_ph, "Calculating")
        ans, tier = solve_math(question)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans, tier, None

    update_phase(thinking_ph, "Understanding question")
    intent = understand_intent(question, history)

    update_phase(thinking_ph, "Checking safety")
    if is_bad_intent(question, intent):
        msg = bad_intent_response(target_grade)
        if stream_ph:
            stream_ph.markdown(msg)
        return msg, "", None

    if is_question_request(question):
        update_phase(thinking_ph, "Finding relevant content")
        candidates  = [] if wants_original_content(question) else keyword_search(question)
        good_chunks = parallel_judge(candidates, question) if candidates else []
        update_phase(thinking_ph, "Generating questions")
        ans, tier, src = generate_questions(question, good_chunks, target_grade, history, stream_ph)
        if ans:
            return ans, tier, src

    update_phase(thinking_ph, "Searching textbooks")
    candidates  = keyword_search(question)
    good_chunks = parallel_judge(candidates, question) if candidates else []

    update_phase(thinking_ph, "Checking relevance")
    pdf_relevant = context_is_relevant(intent, good_chunks)

    update_phase(thinking_ph, "Answering")

    if pdf_relevant and good_chunks:
        ans, tier, src = answer_from_pdf(question, intent, good_chunks, target_grade, history, stream_ph)
        if ans:
            return ans, tier, src

    ans, tier, src = answer_from_ai(question, intent, target_grade, history, stream_ph)
    if ans:
        return ans, tier, src

    update_phase(thinking_ph, "Searching web")
    for fn in [answer_from_duckduckgo, answer_from_wiki]:
        ans, tier, src = fn(question)
        if ans:
            if stream_ph:
                stream_ph.markdown(ans)
            return ans, tier, src

    msg = "I couldn't find a good answer right now. Try rephrasing your question!"
    if stream_ph:
        stream_ph.markdown(msg)
    return msg, "", None

# =============================================================================
# BADGE
# =============================================================================
def show_badge(tier, source):
    badges = {
        "pdf":  ("src-pdf",  f"📖 {source}"),
        "ai":   ("src-ai",   "💡 AI knowledge"),
        "ddg":  ("src-ddg",  "🦆 DuckDuckGo"),
        "wiki": ("src-wiki", "🌐 Wikipedia"),
        "calc": ("src-calc", "🧮 Calculator"),
    }
    if tier in badges:
        cls, label = badges[tier]
        if tier == "pdf" and not source:
            return
        st.markdown(
            f'<span class="source-badge {cls}">{label}</span>',
            unsafe_allow_html=True
        )

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("<div class='section-label'>🎨 App colour</div>", unsafe_allow_html=True)
    picked_accent = st.color_picker(
        "App colour",
        value=st.session_state.accent_color,
        label_visibility="collapsed",
        help="Choose one colour for buttons, highlights and cards."
    )
    if picked_accent != st.session_state.accent_color:
        st.session_state.accent_color = picked_accent
        st.rerun()

    allowed = get_allowed_grades(st.session_state.grade)
    st.markdown(
        f"<div class='welcome-card'>"
        f"👋 Welcome! Grade {st.session_state.grade}"
        f"<br><span style='font-size:11px;opacity:0.8;'>"
        f"📚 Using Grade {allowed[0]}"
        f"{' & ' + str(allowed[1]) if len(allowed) > 1 else ''} books"
        f"</span></div>",
        unsafe_allow_html=True
    )
    st.divider()

    st.markdown("<div class='section-label'>🎯 Active Grade</div>", unsafe_allow_html=True)
    new_grade = st.selectbox(
        "Grade", [f"Grade {i}" for i in range(1, 11)],
        index=st.session_state.grade - 1, label_visibility="collapsed"
    )
    if int(new_grade.split()[1]) != st.session_state.grade:
        st.session_state.grade = int(new_grade.split()[1])
        st.cache_resource.clear()
        st.rerun()

    st.divider()

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[name] = []
        st.session_state.current_chat = name
        st.rerun()

    st.markdown("<div class='section-label'>💬 Chats</div>", unsafe_allow_html=True)
    for chat_name in list(reversed(list(st.session_state.chats.keys()))):
        is_active  = (chat_name == st.session_state.current_chat)
        col1, col2 = st.columns([0.82, 0.18], vertical_alignment="center")
        msgs       = st.session_state.chats.get(chat_name, [])
        first_user = next(
            (m["content"] for m in msgs if m["role"] == "user"), chat_name
        )
        title = first_user[:22] + "..." if len(first_user) > 22 else first_user
        if col1.button(
            f"{'🟢' if is_active else '💬'} {title}",
            key=f"ch_{chat_name}", use_container_width=True
        ):
            st.session_state.current_chat = chat_name
            st.rerun()
        if col2.button("🗑", key=f"dl_{chat_name}", use_container_width=True):
            if len(st.session_state.chats) > 1:
                del st.session_state.chats[chat_name]
                if st.session_state.current_chat == chat_name:
                    st.session_state.current_chat = list(
                        st.session_state.chats.keys()
                    )[0]
                st.rerun()

    st.divider()
    st.success(f"📚 {len(PDF_CHUNKS)} pages loaded")
    st.info(f"🔑 OpenAI: {len(ALL_OPENAI_KEYS)} | Google: {len(ALL_GOOGLE_KEYS)}")

    if st.button("🔄 Change Grade", use_container_width=True):
        st.session_state.grade = None
        st.cache_resource.clear()
        st.rerun()

    with st.expander("🏫 Are you a Teacher?"):
        code = st.text_input(
            "Code", type="password",
            placeholder="Enter school code...",
            label_visibility="collapsed"
        )
        if st.button("Verify", use_container_width=True):
            if code == st.secrets.get("TEACHER_CODE",""):
                st.success("✅ Teacher access granted!")
            else:
                st.error("Invalid code.")

# =============================================================================
# MAIN CHAT UI
# =============================================================================
st.markdown(f"""
<section class="smartloop-hero">
    <div class="hero-kicker">✦ Grade {st.session_state.grade} learning space</div>
    <h1 class="hero-title">Learn smarter with <span>SmartLoop</span><span class="beta-badge">BETA</span></h1>
    <p class="hero-copy">Your textbooks, clear explanations and practice—all in one focused workspace.</p>
</section>
""", unsafe_allow_html=True)

messages = st.session_state.chats.get(st.session_state.current_chat, [])
suggested_q = None

if not messages:
    with st.container(key="quick_actions"):
        qa1, qa2, qa3 = st.columns(3)
        if qa1.button(
            "📖  EXPLAIN A TOPIC\nTeach me a difficult topic clearly with examples",
            use_container_width=True,
            key="quick_explain"
        ):
            suggested_q = (
                f"Explain a challenging Grade {st.session_state.grade} topic from my textbooks. "
                "Use proper academic detail, key terms, a real-world example, and a short recap."
            )
        if qa2.button(
            "✍️  PRACTICE MODE\nCreate a challenging mixed question set",
            use_container_width=True,
            key="quick_practice"
        ):
            suggested_q = (
                f"Create a challenging Grade {st.session_state.grade} practice set from a suitable topic. "
                "Include mixed question types and put the answer key at the end."
            )
        if qa3.button(
            "🧮  SOLVE WITH ME\nShow a worked problem step by step",
            use_container_width=True,
            key="quick_solve"
        ):
            suggested_q = (
                f"Give me a challenging Grade {st.session_state.grade} maths problem and solve it "
                "carefully step by step, explaining the reason for every step."
            )
    with st.chat_message("assistant"):
        st.markdown(
            f"### Ready when you are 👋\n\n"
            f"Ask me to explain a Grade {st.session_state.grade} topic, turn a chapter into proper notes, "
            f"make a challenging worksheet, or solve a maths problem step by step.\n\n"
            f"**What are we learning today?**"
        )

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content",""))
        show_badge(msg.get("tier",""), msg.get("source",""))

# =============================================================================
# CHAT INPUT
# =============================================================================
typed_q = st.chat_input("Ask SmartLoop anything…")
q = suggested_q or typed_q

if q:
    messages = st.session_state.chats[st.session_state.current_chat]
    messages.append({"role":"user","content":q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        thinking_ph = st.empty()
        stream_ph   = st.empty()
        ans, tier, source = smartloop(
            q, st.session_state.grade, messages[:-1],
            thinking_ph, stream_ph
        )
        thinking_ph.empty()
        if not ans:
            ans = "Sorry, something went wrong. Please try again."
        stream_ph.markdown(ans)
        show_badge(tier, source)
    messages.append({
        "role":"assistant","content":ans,"tier":tier,"source":source
    })
    save_chats_to_browser("save_after_reply")
