import re
import shutil
import uuid
from pathlib import Path
from typing import Optional, Dict, Any


ROOT_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT_DIR / "uploads"

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
}


def ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(original_filename: str) -> str:
    """
    Makes uploaded filenames safe for local storage.
    Example:
    'My Receipt #1.pdf' -> 'my_receipt_1.pdf'
    """
    filename = Path(original_filename).name
    filename = filename.strip().lower()
    filename = re.sub(r"[^a-z0-9._-]+", "_", filename)

    if not filename:
        filename = "receipt"

    return filename


def save_uploaded_receipt(upload_file, submission_id: int) -> Path:
    """
    Saves an uploaded receipt file into:

    uploads/submission_<id>/<unique_filename>

    upload_file is FastAPI's UploadFile object.
    """
    ensure_upload_dir()

    original_filename = upload_file.filename or "receipt"
    cleaned_name = safe_filename(original_filename)

    extension = Path(cleaned_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            "Supported types are PDF, TXT, JPG, JPEG, PNG."
        )

    submission_folder = UPLOAD_DIR / f"submission_{submission_id}"
    submission_folder.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{cleaned_name}"
    file_path = submission_folder / unique_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return file_path


def extract_text_from_pdf(file_path: Path) -> str:
    """
    Extracts text from PDF receipts using PyMuPDF.
    This works well for normal text-based PDFs.
    Scanned PDFs may return little/no text.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ""

    text_parts = []

    try:
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text_parts.append(page.get_text())
    except Exception:
        return ""

    return "\n".join(text_parts).strip()


def extract_text_from_txt(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return ""


def extract_receipt_text(file_path: Path) -> str:
    """
    Extract receipt text based on file extension.

    Minimum version:
    - PDF: extract using PyMuPDF
    - TXT: read directly
    - Images: accepted, but OCR not implemented yet
    """
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension == ".txt":
        return extract_text_from_txt(file_path)

    if extension in {".jpg", ".jpeg", ".png"}:
        return ""

    return ""


def money_to_float(value: str) -> Optional[float]:
    try:
        value = value.replace(",", "").replace("$", "").strip()
        return float(value)
    except Exception:
        return None


def extract_amount(text: str) -> Optional[float]:
    """
    Tries to extract the total amount from receipt text.

    Strategy:
    1. Prefer lines containing Total / Amount Paid / Grand Total.
    2. If not found, use the largest currency-looking value.
    """
    if not text:
        return None

    total_patterns = [
        r"\bgrand\s+total\b\s*[:\-]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.\d{2}|[0-9]+\.\d{2})",
        r"\bamount\s+paid\b\s*[:\-]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.\d{2}|[0-9]+\.\d{2})",
        r"\btotal\s+paid\b\s*[:\-]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.\d{2}|[0-9]+\.\d{2})",
        r"\bbalance\s+due\b\s*[:\-]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.\d{2}|[0-9]+\.\d{2})",
        r"\btotal\b\s*[:\-]?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.\d{2}|[0-9]+\.\d{2})",
    ]

    matches = []

    for pattern in total_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            amount = money_to_float(match.group(1))
            if amount is not None:
                matches.append(amount)

    if matches:
        return matches[-1]

    all_money_values = re.findall(
        r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.\d{2}|[0-9]+\.\d{2})",
        text,
    )

    amounts = []
    for value in all_money_values:
        amount = money_to_float(value)
        if amount is not None:
            amounts.append(amount)

    if not amounts:
        return None

    return max(amounts)


def extract_vendor(text: str, file_path: Path) -> str:
    """
    Very simple vendor extraction:
    Use the first meaningful text line.
    If text is missing, fall back to filename.
    """
    if not text:
        return file_path.stem.replace("_", " ").title()

    ignored_prefixes = (
        "receipt",
        "invoice",
        "date",
        "time",
        "total",
        "subtotal",
        "tax",
        "tip",
        "card",
        "visa",
        "mastercard",
        "amex",
        "payment",
    )

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        cleaned = line.strip()

        if len(cleaned) < 2:
            continue

        if len(cleaned) > 80:
            continue

        if cleaned.lower().startswith(ignored_prefixes):
            continue

        if not re.search(r"[A-Za-z]", cleaned):
            continue

        return cleaned

    return file_path.stem.replace("_", " ").title()


def classify_category(text: str, file_path: Path) -> str:
    """
    Rule-based category detection.
    This is intentionally simple for the minimum local version.
    """
    combined = f"{text} {file_path.name}".lower()

    alcohol_keywords = [
        "beer",
        "wine",
        "cocktail",
        "vodka",
        "whiskey",
        "whisky",
        "bourbon",
        "tequila",
        "martini",
        "alcohol",
        "bar tab",
        "lager",
        "ipa",
    ]

    flight_keywords = [
        "flight",
        "airfare",
        "airline",
        "boarding",
        "delta",
        "united airlines",
        "american airlines",
        "southwest",
        "jetblue",
        "alaska airlines",
    ]

    hotel_keywords = [
        "hotel",
        "lodging",
        "inn",
        "suite",
        "room",
        "night",
        "nights",
        "check-in",
        "check out",
        "marriott",
        "hilton",
        "hyatt",
        "sheraton",
    ]

    ground_keywords = [
        "uber",
        "lyft",
        "taxi",
        "cab",
        "rideshare",
        "parking",
        "toll",
        "mileage",
        "rental car",
        "hertz",
        "avis",
        "enterprise",
    ]

    conference_keywords = [
        "conference",
        "registration",
        "summit",
        "expo",
        "eventbrite",
        "badge",
        "workshop",
        "seminar",
    ]

    meal_keywords = [
        "restaurant",
        "cafe",
        "coffee",
        "breakfast",
        "lunch",
        "dinner",
        "meal",
        "bistro",
        "grill",
        "kitchen",
        "sandwich",
        "pizza",
    ]

    if any(keyword in combined for keyword in alcohol_keywords):
        return "alcohol"

    if any(keyword in combined for keyword in flight_keywords):
        return "air_travel"

    if any(keyword in combined for keyword in hotel_keywords):
        return "lodging"

    if any(keyword in combined for keyword in ground_keywords):
        return "ground_transport"

    if any(keyword in combined for keyword in conference_keywords):
        return "conference"

    if any(keyword in combined for keyword in meal_keywords):
        return "meal"

    return "unknown"


def make_verdict(
    category: str,
    amount: Optional[float],
    text: str,
    file_path: Path,
) -> Dict[str, Any]:
    """
    Minimum rule-based verdict.

    Later we will connect this to policy.py for quoted policy clauses.
    """
    extension = file_path.suffix.lower()
    lowered_text = text.lower() if text else ""

    if extension in {".jpg", ".jpeg", ".png"}:
        return {
            "verdict": "needs_human_review",
            "reason": "Image receipt uploaded. OCR is not implemented in the minimum version, so a reviewer should verify it manually.",
            "confidence": 0.25,
        }

    if not text:
        return {
            "verdict": "needs_human_review",
            "reason": "Could not extract readable text from this receipt.",
            "confidence": 0.25,
        }

    if amount is None:
        return {
            "verdict": "needs_human_review",
            "reason": "Could not confidently extract the total amount from the receipt.",
            "confidence": 0.40,
        }

    if "first class" in lowered_text:
        return {
            "verdict": "rejected",
            "reason": "Receipt appears to mention first class air travel, which should be reviewed against the air travel policy.",
            "confidence": 0.80,
        }

    if category == "alcohol":
        return {
            "verdict": "flagged",
            "reason": "Alcohol-related expense detected. Reviewer should verify business context, attendees, and policy eligibility.",
            "confidence": 0.75,
        }

    if category == "meal" and amount > 75:
        return {
            "verdict": "flagged",
            "reason": "Meal expense appears to exceed the standard dinner cap of $75. Reviewer should verify meal type, city tier, and client context.",
            "confidence": 0.70,
        }

    if category == "unknown":
        return {
            "verdict": "needs_human_review",
            "reason": "Could not confidently classify the receipt category.",
            "confidence": 0.45,
        }

    return {
        "verdict": "compliant",
        "reason": "No obvious issue detected by the minimum rule-based review.",
        "confidence": 0.70,
    }


def analyze_receipt(file_path: str | Path) -> Dict[str, Any]:
    """
    Main function used by the app.

    Input:
        file_path

    Output:
        dictionary with extracted vendor, amount, category, verdict, reason
    """
    file_path = Path(file_path)

    text = extract_receipt_text(file_path)
    vendor = extract_vendor(text, file_path)
    amount = extract_amount(text)
    category = classify_category(text, file_path)
    verdict_info = make_verdict(category, amount, text, file_path)

    return {
        "vendor": vendor,
        "amount": amount,
        "category": category,
        "verdict": verdict_info["verdict"],
        "reason": verdict_info["reason"],
        "confidence": verdict_info["confidence"],
        "extracted_text": text,
    }