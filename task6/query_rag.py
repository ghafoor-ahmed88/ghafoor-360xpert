import os
import re
import psycopg2
import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")

print("OPENROUTER KEY FOUND:", bool(OPENROUTER_API_KEY))

DB = {
    "dbname": os.getenv("PGDATABASE", "vectordb"),
    "user": os.getenv("PGUSER", "admin"),
    "password": os.getenv("PGPASSWORD", "admin"),
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5434")),
}

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

HEADINGS = [
    "SUMMARY",
    "WORK EXPERIENCE",
    "EDUCATION",
    "SKILLS",
    "CERTIFICATES",
    "PROJECTS",
]

EXTRA_STOPS = [
    "+92", "@GMAIL", "LINKEDIN", "GITHUB",
    "TECHNICAL CONTENT WRITER", "T E C H N I C A L C O N T E N T W R I T E R",
    "SEO",
]

# Load embedding model
EMB_MODEL = SentenceTransformer(EMBED_MODEL_NAME)


# ---------------- HELPERS ----------------
def to_pgvector_literal(vec):
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


def make_heading_regex(h: str) -> re.Pattern:
    parts = []
    for ch in h:
        if ch == " ":
            parts.append(r"\s+")
        else:
            parts.append(re.escape(ch) + r"\s*")
    return re.compile("".join(parts), re.IGNORECASE)


def detect_section(query: str):
    q = query.lower().strip()
    if "summary" in q:
        return "SUMMARY"
    if "education" in q:
        return "EDUCATION"
    if "skill" in q:
        return "SKILLS"
    if "certificate" in q or "certification" in q:
        return "CERTIFICATES"
    if "project" in q:
        return "PROJECTS"
    if "work" in q or "experience" in q:
        return "WORK EXPERIENCE"
    return None


def fetch_full_text():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT content FROM documents ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return "\n".join((r[0] or "") for r in rows)


def extract_section(full_text: str, section: str) -> str:
    start_re = make_heading_regex(section)
    start_m = start_re.search(full_text)
    if not start_m:
        return ""

    stop_candidates = HEADINGS + EXTRA_STOPS
    end = None

    for s in stop_candidates:
        if s.upper() == section.upper():
            continue
        m = make_heading_regex(s).search(full_text, pos=start_m.end())
        if m:
            end = m.start() if end is None else min(end, m.start())

    block = full_text[start_m.start():end].strip() if end else full_text[start_m.start():].strip()
    block = re.sub(r"\s+", " ", block).strip()
    return block


def rag_semantic_retrieve(query: str, k: int = 4):
    q_emb = EMB_MODEL.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    vec = to_pgvector_literal(q_emb)

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT content
        FROM documents
        ORDER BY embedding <=> (%s::vector)
        LIMIT %s;
        """,
        (vec, k),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows if r and r[0]]


def openrouter_answer(question: str, contexts: list[str]) -> str:
    if not OPENROUTER_API_KEY:
        return "❌ OPENROUTER_API_KEY missing in .env"

    context_text = "\n\n---\n\n".join(contexts[:3])

    prompt = f"""
You are a resume assistant.
Answer ONLY using the provided context.
If the answer is not in the context, say: "I don't have that info in the resume."

Question:
{question}

Context:
{context_text}

Answer (short & clear):
""".strip()

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # ✅ OpenRouter recommends sending these (can be anything valid)
        "HTTP-Referer": os.getenv("OPENROUTER_SITE", "http://localhost"),
        "X-Title": os.getenv("OPENROUTER_APP", "Resume-RAG"),
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Answer ONLY using the given context from the resume."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "stream": False,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        return f"❌ Network error calling OpenRouter: {e}"

    if r.status_code != 200:
        return f"❌ OpenRouter API error {r.status_code}: {r.text}"

    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


# ---------------- MAIN ----------------
def main():
    query = input("Ask: ").strip()
    if not query:
        print("Empty query.")
        return

    # 1) Section mode (exact)
    section = detect_section(query)
    if section:
        full_text = fetch_full_text()
        ans = extract_section(full_text, section)
        print(f"\n✅ {section} ONLY:\n")
        print(ans if ans else "Section not found. (Run: python store_vectors.py)")
        return

    # 2) RAG mode: retrieve -> OpenRouter (DeepSeek)
    contexts = rag_semantic_retrieve(query, k=4)
    if not contexts:
        print("No matches found. (Run: python store_vectors.py)")
        return

    answer = openrouter_answer(query, contexts)
    print("\n✅ RAG Answer:\n")
    print(answer)


if __name__ == "__main__":
    main()
