import re
from pathlib import Path
from functools import lru_cache


ROOT_DIR = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT_DIR / "data" / "policies"


@lru_cache(maxsize=1)
def load_policy_texts():
    """
    Loads all policy PDFs from data/policies.

    Returns a list like:
    [
        {
            "filename": "policy1.pdf",
            "text": "..."
        }
    ]
    """
    policies = []

    if not POLICY_DIR.exists():
        return policies

    for pdf_path in POLICY_DIR.glob("*.pdf"):
        text = extract_pdf_text(pdf_path)

        if text:
            policies.append({
                "filename": pdf_path.name,
                "text": text
            })

    return policies


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        import fitz
    except ImportError:
        return ""

    text_parts = []

    try:
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                text_parts.append(page.get_text())
    except Exception:
        return ""

    return "\n".join(text_parts)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_best_policy_quote(keywords):
    """
    Very simple keyword-based policy search.

    keywords example:
    ["meal", "dinner", "$75"]

    Returns:
    {
        "source": "policy1.pdf",
        "quote": "..."
    }
    """
    policies = load_policy_texts()

    best_result = None
    best_score = 0

    for policy in policies:
        text = clean_text(policy["text"])
        lowered = text.lower()

        for match in re.finditer(r".{0,250}", text):
            pass

        # Split policy into small readable chunks
        chunks = split_into_chunks(text)

        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = 0

            for keyword in keywords:
                if keyword.lower() in chunk_lower:
                    score += 1

            if score > best_score:
                best_score = score
                best_result = {
                    "source": policy["filename"],
                    "quote": chunk
                }

    return best_result


def split_into_chunks(text: str, chunk_size: int = 700):
    """
    Splits long policy text into small chunks.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), 90):
        chunk = " ".join(words[i:i + 90])

        if len(chunk) <= chunk_size:
            chunks.append(chunk)
        else:
            chunks.append(chunk[:chunk_size])

    return chunks


def get_policy_support(category: str, verdict: str):
    """
    Returns a relevant policy quote based on receipt category/verdict.
    """

    if category == "meal":
        return find_best_policy_quote([
            "meal",
            "dinner",
            "$75",
            "caps",
            "not reimbursable"
        ])

    if category == "alcohol":
        return find_best_policy_quote([
            "alcohol",
            "reimbursable",
            "client",
            "solo",
            "not reimbursable"
        ])

    if category == "air_travel":
        return find_best_policy_quote([
            "air travel",
            "economy",
            "business class",
            "first class",
            "not reimbursable"
        ])

    if category == "lodging":
        return find_best_policy_quote([
            "lodging",
            "hotel",
            "rate cap",
            "nightly"
        ])

    if category == "ground_transport":
        return find_best_policy_quote([
            "rideshare",
            "taxi",
            "ground transportation",
            "business-related"
        ])

    if category == "conference":
        return find_best_policy_quote([
            "conference",
            "registration",
            "approval",
            "attendance"
        ])

    return find_best_policy_quote([
        "business purpose",
        "documentation",
        "itemized receipts",
        "reimbursable"
    ])
    