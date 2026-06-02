import json
from pathlib import Path

from app.db import create_employee, get_all_employees


ROOT_DIR = Path(__file__).resolve().parents[1]
SUBMISSIONS_DIR = ROOT_DIR / "data" / "submissions"


def split_trip_dates(trip_dates: str):
    """
    Example input:
    '2025-04-14 to 2025-04-16'

    Returns:
    ('2025-04-14', '2025-04-16')
    """
    if not trip_dates:
        return "", ""

    if " to " in trip_dates:
        start_date, end_date = trip_dates.split(" to ", 1)
        return start_date.strip(), end_date.strip()

    return trip_dates.strip(), ""


def seed_employees():
    """
    Loads employee_info.json files from data/submissions/*/employee_info.json.

    This is needed because the assignment expects the 5 provided employees
    to be available in the UI without uploading JSON manually.
    """

    if not SUBMISSIONS_DIR.exists():
        print(f"Seed skipped: {SUBMISSIONS_DIR} does not exist")
        return

    existing_employees = get_all_employees()

    existing_keys = set()
    for employee in existing_employees:
        key = (
            employee["employee_name"],
            employee["trip_purpose"]
        )
        existing_keys.add(key)

    employee_files = list(SUBMISSIONS_DIR.rglob("employee_info.json"))

    if not employee_files:
        print("Seed skipped: no employee_info.json files found")
        return

    added_count = 0

    for employee_file in employee_files:
        with open(employee_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        employee_name = data.get("name") or data.get("employee_name") or ""
        employee_grade = str(data.get("grade") or data.get("employee_grade") or "")
        department = data.get("department") or ""
        manager = data.get("manager") or data.get("manager_id") or ""
        trip_purpose = data.get("trip_purpose") or ""

        trip_start_date = data.get("trip_start_date") or ""
        trip_end_date = data.get("trip_end_date") or ""

        if not trip_start_date and not trip_end_date:
            trip_start_date, trip_end_date = split_trip_dates(
                data.get("trip_dates", "")
            )

        key = (employee_name, trip_purpose)

        if key in existing_keys:
            continue

        create_employee(
            employee_name=employee_name,
            employee_grade=employee_grade,
            department=department,
            manager=manager,
            trip_purpose=trip_purpose,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date
        )

        existing_keys.add(key)
        added_count += 1

    print(f"Seed complete: added {added_count} employee(s)")