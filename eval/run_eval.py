import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


from app.policy import answer_policy_question
from app.receipt import analyze_receipt


VALID_VERDICTS = {
    "compliant",
    "flagged",
    "rejected",
    "needs_human_review",
}

VALID_CATEGORIES = {
    "meal",
    "alcohol",
    "air_travel",
    "lodging",
    "ground_transport",
    "conference",
    "unknown",
}


SUPPORTED_RECEIPT_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
}


def load_expected(expected_path: Path):
    if not expected_path.exists():
        raise FileNotFoundError(f"Expected file not found: {expected_path}")

    with open(expected_path, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(value):
    if value is None:
        return ""

    return str(value).lower()


def check_terms(text, expected_terms):
    missing = []

    text = normalize_text(text)

    for term in expected_terms:
        if normalize_text(term) not in text:
            missing.append(term)

    return missing


def evaluate_policy_qa(expected):
    print("\n=== Policy Q&A Evaluation ===")

    tests = expected.get("policy_qa", [])

    total = 0
    passed = 0

    for test in tests:
        total += 1

        question = test["question"]
        expected_in_scope = test.get("expected_in_scope", True)
        expected_terms = test.get("expected_terms", [])
        min_citations = test.get("min_citations", 0)

        result = answer_policy_question(question)

        citations = result.get("citations", [])

        combined_text = result.get("answer", "")

        for citation in citations:
            combined_text += " "
            combined_text += citation.get("source", "")
            combined_text += " "
            combined_text += citation.get("quote", "")

        missing_terms = check_terms(combined_text, expected_terms)

        is_pass = True
        reasons = []

        if result.get("in_scope") != expected_in_scope:
            is_pass = False
            reasons.append(
                f"expected in_scope={expected_in_scope}, got {result.get('in_scope')}"
            )

        if len(citations) < min_citations:
            is_pass = False
            reasons.append(
                f"expected at least {min_citations} citation(s), got {len(citations)}"
            )

        if missing_terms:
            is_pass = False
            reasons.append(
                "missing expected term(s): " + ", ".join(missing_terms)
            )

        if is_pass:
            passed += 1
            print(f"[PASS] {question}")
        else:
            print(f"[FAIL] {question}")
            for reason in reasons:
                print(f"       - {reason}")

    return passed, total


def evaluate_seed_files(input_dir: Path):
    print("\n=== Seed Data Evaluation ===")

    employee_files = list(input_dir.rglob("employee_info.json"))

    if len(employee_files) >= 5:
        print(f"[PASS] Found {len(employee_files)} employee_info.json file(s)")
        return 1, 1

    print(f"[FAIL] Expected at least 5 employee_info.json files, found {len(employee_files)}")
    return 0, 1


def evaluate_policy_files():
    print("\n=== Policy File Evaluation ===")

    policy_dir = ROOT_DIR / "data" / "policies"

    policy_files = list(policy_dir.glob("*.pdf"))

    if len(policy_files) >= 1:
        print(f"[PASS] Found {len(policy_files)} policy PDF file(s)")
        return 1, 1

    print("[FAIL] No policy PDF files found in data/policies")
    return 0, 1


def evaluate_receipt_smoke(input_dir: Path, limit: int):
    print("\n=== Receipt Smoke Evaluation ===")

    receipt_files = []

    for path in input_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_RECEIPT_EXTENSIONS:
            receipt_files.append(path)

    if not receipt_files:
        print("[WARN] No receipt files found. Skipping receipt smoke test.")
        return 0, 0

    receipt_files = receipt_files[:limit]

    total = 0
    passed = 0

    for receipt_path in receipt_files:
        total += 1

        try:
            result = analyze_receipt(receipt_path)

            verdict = result.get("verdict")
            category = result.get("category")

            if verdict in VALID_VERDICTS and category in VALID_CATEGORIES:
                passed += 1
                print(
                    f"[PASS] {receipt_path.name} | "
                    f"category={category} | verdict={verdict}"
                )
            else:
                print(
                    f"[FAIL] {receipt_path.name} | "
                    f"invalid category/verdict: category={category}, verdict={verdict}"
                )

        except Exception as error:
            print(f"[FAIL] {receipt_path.name} | error={error}")

    return passed, total


def main():
    parser = argparse.ArgumentParser(
        description="Minimal evaluation harness for Northwind Expense Review"
    )

    parser.add_argument(
        "--input-dir",
        default=str(ROOT_DIR / "data" / "submissions"),
        help="Path to submissions directory"
    )

    parser.add_argument(
        "--expected",
        default=str(ROOT_DIR / "eval" / "example_expected.json"),
        help="Path to expected outcomes JSON"
    )

    parser.add_argument(
        "--receipt-limit",
        type=int,
        default=20,
        help="Maximum number of receipts to smoke test"
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    expected_path = Path(args.expected)

    expected = load_expected(expected_path)

    total_passed = 0
    total_tests = 0

    passed, tests = evaluate_policy_files()
    total_passed += passed
    total_tests += tests

    passed, tests = evaluate_seed_files(input_dir)
    total_passed += passed
    total_tests += tests

    passed, tests = evaluate_policy_qa(expected)
    total_passed += passed
    total_tests += tests

    passed, tests = evaluate_receipt_smoke(input_dir, args.receipt_limit)
    total_passed += passed
    total_tests += tests

    print("\n=== Final Result ===")
    print(f"Passed {total_passed}/{total_tests} checks")

    if total_tests == 0:
        print("No tests were run.")
        sys.exit(1)

    if total_passed != total_tests:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()