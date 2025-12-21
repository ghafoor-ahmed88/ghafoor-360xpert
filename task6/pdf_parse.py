import re
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def clean_text(text: str) -> str:
    text = text or ""

    # 1) Normalize whitespace (tabs/newlines -> single space)
    text = re.sub(r"\s+", " ", text).strip()

    # 2) Join spaced ALL-CAPS headings
    text = re.sub(
        r"(?:\b[A-Z]\s){2,}[A-Z]\b",
        lambda m: m.group(0).replace(" ", ""),
        text
    )

    # 3) Join spaced letters in normal words
    def join_word(m):
        s = m.group(0)
        if s.startswith("I "): 
            return s
        return s.replace(" ", "")

    text = re.sub(r"(?:\b[A-Za-z]\s){2,}[A-Za-z]\b", join_word, text)



    # 5) Add missing spaces in common cases
    # lowercase + Uppercase -> space
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

    # digit + letter -> space
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)

    # punctuation + letter -> space
    text = re.sub(r"([.,;:])([A-Za-z])", r"\1 \2", text)

    return text.strip()


# --------- RUN TEST ---------

PDF_PATH = "resume cs (1).pdf"

loader = PyPDFLoader(PDF_PATH)
docs = loader.load()

for d in docs:
    d.page_content = clean_text(d.page_content)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50
)
chunks = splitter.split_documents(docs)

print("Total chunks:", len(chunks))
for i, c in enumerate(chunks, start=1):
    print(f"\n--- CHUNK {i} ---\n{c.page_content}")
