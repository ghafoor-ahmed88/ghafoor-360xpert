# store_vectors.py (FINAL - clean PDF text + better chunks + store in pgvector)

import re
import psycopg2
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

PDF_PATH = "resume cs (1).pdf"

DB = {
    "dbname": "vectordb",
    "user": "admin",
    "password": "admin",
    "host": "localhost",
    "port": "5434",
}

MODEL_NAME = "all-MiniLM-L6-v2"  # dim = 384


def clean_text(text: str) -> str:
    text = text or ""

    # 1) Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 2) Join spaced ALL-CAPS headings: S U M M A R Y -> SUMMARY
    text = re.sub(
        r"(?:\b[A-Z]\s){2,}[A-Z]\b",
        lambda m: m.group(0).replace(" ", ""),
        text,
    )

    # 3) Join spaced letters in normal words: P y t h o n -> Python
    #    BUT keep "I am" as-is
    def join_word(m):
        s = m.group(0)
        if s.startswith("I "):
            return s
        return s.replace(" ", "")

    text = re.sub(r"(?:\b[A-Za-z]\s){2,}[A-Za-z]\b", join_word, text)

    # 4) Fix merged headings explicitly
    fixes = {
        "SUMMARY": "SUMMARY ",
        "EDUCATION": "EDUCATION ",
        "SKILLS": "SKILLS ",
        "CERTIFICATES": "CERTIFICATES ",
        "PROJECTS": "PROJECTS ",
        "WORKEXPERIENCE": "WORK EXPERIENCE ",
        "TECHNICALCONTENTWRITER": "TECHNICAL CONTENT WRITER ",
    }
    for k, v in fixes.items():
        text = text.replace(k, v)

    # 5) Add missing spaces (common boundary cases)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)          # aB -> a B
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)          # 2025Built -> 2025 Built
    text = re.sub(r"([.,;:])([A-Za-z])", r"\1 \2", text)      # .Net -> . Net (where needed)

    return text.strip()


def main():
    # 1) Load PDF
    docs = PyPDFLoader(PDF_PATH).load()

    # ✅ Clean every page
    for d in docs:
        d.page_content = clean_text(d.page_content)

    # 2) Chunk (resume = 1 page, so bigger chunks are better)
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    texts = [c.page_content for c in chunks]
    print("Total chunks:", len(texts))

    # 3) Embeddings
    model = SentenceTransformer(MODEL_NAME)
    embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    dim = int(embs.shape[1])
    print("Embedding dim:", dim)

    # 4) DB connect + table create
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR({dim})
        );
    """)

    # Fresh insert every run (OK for demo)
    cur.execute("TRUNCATE TABLE documents;")

    # 5) Insert
    for t, e in zip(texts, embs):
        cur.execute(
            "INSERT INTO documents (content, embedding) VALUES (%s, %s::vector)",
            (t, e.tolist()),
        )

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Stored cleaned chunks + embeddings in pgvector (table: documents)")


if __name__ == "__main__":
    main()
