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
STOPWORDS = {
    "the", "a", "an", "is", "are", "am", "i", "we", "you", "can", "could",
    "should", "would", "to", "for", "of", "on", "in", "at", "by", "with",
    "and", "or", "it", "this", "that", "be", "as", "from", "what", "who",
    "when", "where", "why", "how", "do", "does", "did", "my", "our"
}


POLICY_SCOPE_WORDS = {
    "policy",
    "expense",
    "expenses",
    "receipt",
    "receipts",
    "reimburse",
    "reimbursed",
    "reimbursable",
    "travel",
    "trip",
    "meal",
    "meals",
    "dinner",
    "lunch",
    "breakfast",
    "alcohol",
    "hotel",
    "lodging",
    "flight",
    "air",
    "airfare",
    "taxi",
    "uber",
    "lyft",
    "rideshare",
    "conference",
    "approval",
    "manager",
    "director",
    "vp",
    "grade",
    "card",
    "corporate",
    "tip",
    "tips",
    "per-diem",
    "perdiem",
    "retention",
    "data",
    "security",
    "confidential",
    "vendor",
    "record",
    "records",
    "tep",
    "sec",
    "rec",
    "coc",
    "hrp",
    "proc",
    "sus",
    "first",
    "class",
    "business",
    "economy"
}


def extract_question_terms(question: str):
    tokens = re.findall(r"[a-zA-Z0-9\-]+", question.lower())

    terms = []

    for token in tokens:
        if token in STOPWORDS:
            continue

        if len(token) < 3:
            continue

        terms.append(token)

    return terms


def is_policy_question(question: str, terms: list[str]) -> bool:
    lower_question = question.lower()

    # Allow direct policy document IDs like TEP-003, REC-001, SEC-201.
    if re.search(r"\b[a-z]{2,5}-\d{3}\b", lower_question):
        return True

    return any(term in POLICY_SCOPE_WORDS for term in terms)


def search_policy_chunks(question: str, limit: int = 3):
    terms = extract_question_terms(question)

    if not is_policy_question(question, terms):
        return []

    policies = load_policy_texts()

    results = []

    for policy in policies:
        text = clean_text(policy["text"])
        chunks = split_into_chunks(text)

        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = 0

            for term in terms:
                if term in chunk_lower:
                    score += 1

            # Boost direct document ID matches.
            doc_ids = re.findall(r"\b[A-Z]{2,5}-\d{3}\b", question.upper())

            for doc_id in doc_ids:
                if doc_id.lower() in chunk_lower:
                    score += 10

            if score > 0:
                results.append({
                    "source": policy["filename"],
                    "quote": chunk,
                    "score": score
                })

    results.sort(key=lambda item: item["score"], reverse=True)

    if not results:
        return []

    # Avoid weak/random matches.
    if results[0]["score"] < 2:
        return []

    return results[:limit]


def answer_policy_question(question: str):
    """
    Simple non-LLM policy Q&A.

    Returns:
    {
        "in_scope": True/False,
        "answer": "...",
        "citations": [
            {
                "source": "policy1.pdf",
                "quote": "..."
            }
        ]
    }
    """

    question = question.strip()

    if not question:
        return {
            "in_scope": False,
            "answer": "Please enter a policy question.",
            "citations": []
        }

    results = search_policy_chunks(question)

    if not results:
        return {
            "in_scope": False,
            "answer": (
                "I could not find enough support in the policy library to answer this. "
                "This may be outside the policy scope, so I am declining to answer."
            ),
            "citations": []
        }

    lower_question = question.lower()

    if "alcohol" in lower_question and "solo" in lower_question:
        answer = (
            "Alcohol on solo travel should be treated as a policy risk. "
            "The relevant policy excerpts are shown below."
        )

    elif "first class" in lower_question:
        answer = (
            "First class air travel is not reimbursable under the relevant policy excerpts."
        )

    elif "dinner" in lower_question or "meal" in lower_question:
        answer = (
            "Meal reimbursement depends on the applicable meal cap, location, and whether it was "
            "individual travel or client entertainment. The relevant policy excerpts are shown below."
        )

    elif "receipt" in lower_question:
        answer = (
            "Expenses must be supported by receipt documentation. "
            "The relevant policy excerpts are shown below."
        )

    elif "retention" in lower_question or "retain" in lower_question:
        answer = (
            "The records policy includes retention rules for employee expense reports and supporting receipts. "
            "The relevant excerpts are shown below."
        )

    else:
        answer = (
            "I found relevant policy excerpts. Use the quoted policy text below to support the review decision."
        )

    citations = []

    for result in results:
        citations.append({
            "source": result["source"],
            "quote": result["quote"]
        })

    return {
        "in_scope": True,
        "answer": answer,
        "citations": citations
    }