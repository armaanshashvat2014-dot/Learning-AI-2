# =========================
# SMARTLOOP AI ENGINE
# FULL REPLACEMENT
# UI UNCHANGED
# =========================

import re
import time
import itertools
import requests
import wikipedia

from bs4 import BeautifulSoup
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

from openai import OpenAI
from google import genai


# =========================
# API KEY SYSTEM
# =========================

ALL_OPENAI_KEYS = [
    st.secrets.get(f"OPENAI_API_KEY_{i}")
    for i in range(1, 5)
]

ALL_OPENAI_KEYS = [
    k for k in ALL_OPENAI_KEYS if k
]

ALL_GOOGLE_KEYS = [
    st.secrets.get(f"GOOGLE_API_KEY_{i}")
    for i in range(1, 5)
]

ALL_GOOGLE_KEYS = [
    k for k in ALL_GOOGLE_KEYS if k
]

PDF_JUDGE_KEYS = ALL_OPENAI_KEYS.copy()

PRIMARY_ANS_KEYS = [
    k for i, k in enumerate(ALL_OPENAI_KEYS)
    if i in [1, 2]
]

EXTRA_ANS_KEYS = [
    k for i, k in enumerate(ALL_OPENAI_KEYS)
    if i == 3
]

pdf_judge_cycle = (
    itertools.cycle(PDF_JUDGE_KEYS)
    if PDF_JUDGE_KEYS else None
)

primary_ans_cycle = (
    itertools.cycle(PRIMARY_ANS_KEYS)
    if PRIMARY_ANS_KEYS else None
)

extra_ans_cycle = (
    itertools.cycle(EXTRA_ANS_KEYS)
    if EXTRA_ANS_KEYS else None
)

google_cycle = (
    itertools.cycle(ALL_GOOGLE_KEYS)
    if ALL_GOOGLE_KEYS else None
)


def get_primary():
    if primary_ans_cycle:
        return OpenAI(
            api_key=next(primary_ans_cycle)
        )

    if pdf_judge_cycle:
        return OpenAI(
            api_key=next(pdf_judge_cycle)
        )

    return None


def get_extra():

    if extra_ans_cycle:
        return OpenAI(
            api_key=next(extra_ans_cycle)
        )

    return None


def get_google():

    if google_cycle:
        return genai.Client(
            api_key=next(google_cycle)
        )

    return None


# =========================
# GRADE STYLES
# =========================

def grade_style(g):

    if g <= 2:
        return (
            "Use extremely simple words, "
            "short sentences, emojis, and "
            "fun real-life examples."
        )

    elif g <= 5:
        return (
            "Use easy explanations, examples, "
            "and engaging teaching style."
        )

    elif g <= 8:
        return (
            "Use clear academic language with "
            "step-by-step explanations."
        )

    return (
        "Use detailed academic language "
        "suitable for advanced students."
    )


# =========================
# PURE CALCULATOR
# =========================

def is_pure_calc(q):

    return bool(
        re.fullmatch(
            r"[\d\.\+\-\*\/\(\)\s\^%]+",
            q.strip()
        )
    )


def solve_math(q):

    try:

        expr = (
            q.strip()
            .replace("^", "**")
            .replace(" ", "")
        )

        result = eval(
            expr,
            {"__builtins__": None},
            {}
        )

        return (
            f"## 🧮 Answer\n\n"
            f"**{q} = {round(result, 8)}**",
            "calc"
        )

    except:
        return None, None


# =========================
# PDF SEARCH
# =========================

STOPWORDS = {
    "what","is","are","how","why","when",
    "who","the","a","an","of","in","to",
    "and","does","do","explain","define",
    "me","about","give","please","describe",
    "tell","example","examples","find",
    "solve","calculate","show","write"
}


def keyword_search(q):

    if not PDF_CHUNKS:
        return []

    q_words = set(
        re.sub(
            r"[^a-z0-9 ]",
            " ",
            q.lower()
        ).split()
    ) - STOPWORDS

    if not q_words:
        return []

    scored = []

    for chunk in PDF_CHUNKS:

        score = len(
            q_words & chunk["words"]
        )

        if score >= 2:
            scored.append((score, chunk))

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return scored[:8]


# =========================
# PARALLEL PDF JUDGE
# =========================

def judge_single(args):

    chunk, question, key = args

    prompt = f"""
Question:
{question}

Excerpt:
{chunk['text'][:600]}

Does this excerpt directly help answer
the student's academic question?

Reply ONLY:
YES or NO
"""

    try:

        client = OpenAI(api_key=key)

        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=3,
            temperature=0
        )

        ok = (
            "YES" in
            r.choices[0]
            .message.content.upper()
        )

        return ok, chunk

    except:

        return False, chunk


def parallel_judge(candidates, question):

    if not candidates:
        return []

    if not PDF_JUDGE_KEYS:
        return []

    key_list = list(
        itertools.islice(
            itertools.cycle(PDF_JUDGE_KEYS),
            len(candidates)
        )
    )

    tasks = [
        (
            chunk,
            question,
            key_list[i]
        )
        for i, (_, chunk)
        in enumerate(candidates)
    ]

    good = []

    with ThreadPoolExecutor(
        max_workers=len(tasks)
    ) as ex:

        futures = [
            ex.submit(
                judge_single,
                t
            )
            for t in tasks
        ]

        for f in as_completed(futures):

            try:

                ok, chunk = f.result()

                if ok:
                    good.append(chunk)

            except:
                pass

    return good


# =========================
# PDF ANSWER ENGINE
# =========================

def answer_from_pdf(
    question,
    chunks,
    grade,
    history
):

    context = "\n\n---\n\n".join([
        f"[{c['file']} page {c['page']}]\n"
        f"{c['text']}"
        for c in chunks[:4]
    ])

    style = grade_style(grade)

    hist = "\n".join([
        f"{m['role']}: {m.get('content','')}"
        for m in history[-4:]
    ])

    prompt = f"""
You are SmartLoop AI.

You are an expert teacher for Grade {grade}.

STYLE:
{style}

RULES:
- Teach clearly
- Use examples
- Be accurate
- Use markdown formatting
- Use headings and bullets
- Never say "I cannot"
- Never refuse
- If math, solve step-by-step

TEXTBOOK CONTENT:
{context}

CHAT HISTORY:
{hist}

QUESTION:
{question}

ANSWER:
"""

    models = [
        "gpt-4o-mini",
        "gpt-3.5-turbo"
    ]

    for model in models:

        for _ in range(
            max(1, len(PRIMARY_ANS_KEYS))
        ):

            try:

                c = get_primary()

                if not c:
                    continue

                r = c.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=1200,
                    temperature=0.4
                )

                ans = (
                    r.choices[0]
                    .message.content.strip()
                )

                if len(ans) > 30:
                    return (
                        ans,
                        "pdf",
                        chunks[0]["file"]
                    )

            except:
                time.sleep(1)

    return None, None, None


# =========================
# MAIN AI ENGINE
# =========================

def answer_from_ai(
    question,
    grade,
    history
):

    style = grade_style(grade)

    hist = "\n".join([
        f"{m['role']}: {m.get('content','')}"
        for m in history[-4:]
    ])

    prompt = f"""
You are SmartLoop AI.

You are an elite AI tutor for Grade {grade}.

STYLE:
{style}

RULES:
- Be educational
- Be accurate
- Use markdown
- Use headings
- Use examples
- Use bullets
- Explain difficult concepts simply
- Never refuse
- Never say you cannot answer
- Avoid hallucinations
- If math, solve step-by-step

CHAT HISTORY:
{hist}

QUESTION:
{question}

ANSWER:
"""

    # ======================
    # GOOGLE GEMINI
    # ======================

    for _ in range(
        min(
            2,
            max(1, len(ALL_GOOGLE_KEYS))
        )
    ):

        try:

            c = get_google()

            if c:

                r = c.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )

                if (
                    r.text and
                    len(r.text.strip()) > 30
                ):

                    return (
                        r.text.strip(),
                        "ai",
                        None
                    )

        except:
            time.sleep(1)

    # ======================
    # OPENAI
    # ======================

    models = [
        "gpt-4o-mini",
        "gpt-3.5-turbo"
    ]

    for model in models:

        for _ in range(
            max(1, len(PRIMARY_ANS_KEYS))
        ):

            try:

                c = get_primary()

                if not c:
                    continue

                msgs = [
                    {
                        "role": "system",
                        "content": (
                            f"You are SmartLoop AI. "
                            f"You are an expert "
                            f"Grade {grade} tutor. "
                            f"{style}"
                        )
                    }
                ]

                for m in history[-4:]:

                    msgs.append({
                        "role": m["role"],
                        "content": m["content"]
                    })

                msgs.append({
                    "role": "user",
                    "content": question
                })

                r = c.chat.completions.create(
                    model=model,
                    messages=msgs,
                    max_tokens=1200,
                    temperature=0.5
                )

                ans = (
                    r.choices[0]
                    .message.content.strip()
                )

                if len(ans) > 30:

                    return (
                        ans,
                        "ai",
                        None
                    )

            except:
                time.sleep(1)

    return None, None, None


# =========================
# DUCKDUCKGO
# =========================

BAD_CONTENT = [
    "comic","marvel","movie","film",
    "anime","fictional","song",
    "album","actor","actress"
]

ACADEMIC_HINTS = [
    "math","science","decimal",
    "fraction","education",
    "school","formula",
    "equation","history"
]


def clean_query(q):

    q = q.lower()

    remove = [
        "what is",
        "what are",
        "explain",
        "define",
        "tell me about",
        "learn about"
    ]

    for p in remove:
        q = q.replace(p, "")

    q = re.sub(
        r"[^a-z0-9 ]",
        " ",
        q
    )

    q = re.sub(
        r"\s+",
        " ",
        q
    ).strip()

    return q


def looks_academic(text):

    text = text.lower()

    if any(
        b in text
        for b in BAD_CONTENT
    ):
        return False

    score = sum([
        1 for k in ACADEMIC_HINTS
        if k in text
    ])

    return score >= 1


def answer_from_duckduckgo(question):

    try:

        headers = {
            "User-Agent": (
                "Mozilla/5.0"
            )
        }

        search_q = clean_query(question)

        final_query = (
            f"{search_q} school definition"
        )

        api_url = (
            "https://api.duckduckgo.com/"
            f"?q={requests.utils.quote(final_query)}"
            "&format=json"
            "&no_html=1"
            "&skip_disambig=1"
        )

        resp = requests.get(
            api_url,
            headers=headers,
            timeout=8
        )

        data = resp.json()

        answers = [
            data.get("AbstractText", ""),
            data.get("Definition", ""),
            data.get("Answer", "")
        ]

        for ans in answers:

            if (
                ans and
                len(ans) > 40 and
                looks_academic(ans)
            ):

                return ans, "ddg", None

    except:
        pass

    return None, None, None


# =========================
# WIKIPEDIA
# =========================

def answer_from_wiki(question):

    try:

        q = clean_query(question)

        results = wikipedia.search(
            q,
            results=5
        )

        if not results:
            return None, None, None

        best = results[0]

        summary = wikipedia.summary(
            best,
            sentences=4
        )

        if any(
            b in summary.lower()
            for b in BAD_CONTENT
        ):
            return None, None, None

        return summary, "wiki", None

    except:
        return None, None, None


# =========================
# THINKING PHASES
# =========================

def update_phase(ph, text):

    ph.markdown(f"""
<div class="thinking-container">
    <span class="thinking-text">
        {text}
    </span>

    <div class="thinking-dots">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
</div>
""", unsafe_allow_html=True)


# =========================
# MAIN PIPELINE
# =========================

def smartloop(
    question,
    grade,
    history,
    thinking_ph
):

    # ======================
    # CALCULATOR
    # ======================

    if is_pure_calc(question):

        update_phase(
            thinking_ph,
            "Calculating"
        )

        ans, tier = solve_math(question)

        if ans:
            return ans, tier, None

    # ======================
    # PDF SEARCH
    # ======================

    update_phase(
        thinking_ph,
        "Searching textbooks"
    )

    candidates = keyword_search(question)

    good_chunks = []

    if candidates:

        update_phase(
            thinking_ph,
            "Reading textbook pages"
        )

        good_chunks = parallel_judge(
            candidates,
            question
        )

    if good_chunks:

        update_phase(
            thinking_ph,
            "Building textbook answer"
        )

        ans, tier, src = answer_from_pdf(
            question,
            good_chunks,
            grade,
            history
        )

        if ans:
            return ans, tier, src

    # ======================
    # AI
    # ======================

    update_phase(
        thinking_ph,
        "Thinking deeply"
    )

    ans, tier, src = answer_from_ai(
        question,
        grade,
        history
    )

    if ans:
        return ans, tier, src

    # ======================
    # DDG
    # ======================

    update_phase(
        thinking_ph,
        "Searching the web"
    )

    ans, tier, src = answer_from_duckduckgo(
        question
    )

    if ans:
        return ans, tier, src

    # ======================
    # WIKIPEDIA
    # ======================

    update_phase(
        thinking_ph,
        "Checking Wikipedia"
    )

    ans, tier, src = answer_from_wiki(
        question
    )

    if ans:
        return ans, tier, src

    return (
        "# ⚠️ Error\n\n"
        "All AI systems are currently unavailable.",
        "",
        None
    )
