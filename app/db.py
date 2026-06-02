
import sqlite3
from pathlib import Path

DB_PATH = Path("expense_app.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Employees
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_name TEXT NOT NULL,
        employee_grade TEXT,
        department TEXT,
        manager TEXT,
        trip_purpose TEXT,
        trip_start_date TEXT,
        trip_end_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Expense submissions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )
    """)

    # Uploaded receipts
    cur.execute("""
    CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER,
        filename TEXT,
        file_path TEXT,
        vendor TEXT,
        amount REAL,
        category TEXT,
        verdict TEXT,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(submission_id) REFERENCES submissions(id)
    )
    """)

    # Reviewer overrides
    cur.execute("""
    CREATE TABLE IF NOT EXISTS overrides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id INTEGER,
        old_verdict TEXT,
        new_verdict TEXT,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(receipt_id) REFERENCES receipts(id)
    )
    """)

    conn.commit()
    conn.close()


# -------------------------
# Employee Helpers
# -------------------------

def create_employee(
    employee_name,
    employee_grade,
    department,
    manager,
    trip_purpose,
    trip_start_date,
    trip_end_date
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO employees (
        employee_name,
        employee_grade,
        department,
        manager,
        trip_purpose,
        trip_start_date,
        trip_end_date
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        employee_name,
        employee_grade,
        department,
        manager,
        trip_purpose,
        trip_start_date,
        trip_end_date
    ))

    conn.commit()
    conn.close()


def get_all_employees():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM employees ORDER BY employee_name"
    ).fetchall()
    conn.close()
    return rows


# -------------------------
# Submission Helpers
# -------------------------

def create_submission(employee_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO submissions(employee_id)
    VALUES(?)
    """, (employee_id,))

    submission_id = cur.lastrowid

    conn.commit()
    conn.close()

    return submission_id


def get_submission(submission_id):
    conn = get_connection()

    submission = conn.execute("""
    SELECT *
    FROM submissions
    WHERE id = ?
    """, (submission_id,)).fetchone()

    receipts = conn.execute("""
    SELECT *
    FROM receipts
    WHERE submission_id = ?
    """, (submission_id,)).fetchall()

    conn.close()

    return submission, receipts


# -------------------------
# Receipt Helpers
# -------------------------

def save_receipt(
    submission_id,
    filename,
    file_path,
    vendor,
    amount,
    category,
    verdict,
    reason
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO receipts (
        submission_id,
        filename,
        file_path,
        vendor,
        amount,
        category,
        verdict,
        reason
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        submission_id,
        filename,
        file_path,
        vendor,
        amount,
        category,
        verdict,
        reason
    ))

    conn.commit()
    conn.close()


def get_receipt(receipt_id):
    conn = get_connection()

    row = conn.execute("""
    SELECT *
    FROM receipts
    WHERE id = ?
    """, (receipt_id,)).fetchone()

    conn.close()

    return row


# -------------------------
# Override Helpers
# -------------------------

def create_override(
    receipt_id,
    old_verdict,
    new_verdict,
    comment
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO overrides(
        receipt_id,
        old_verdict,
        new_verdict,
        comment
    )
    VALUES (?, ?, ?, ?)
    """, (
        receipt_id,
        old_verdict,
        new_verdict,
        comment
    ))

    conn.commit()
    conn.close()

def get_employee(employee_id):
    conn = get_connection()

    row = conn.execute("""
    SELECT *
    FROM employees
    WHERE id = ?
    """, (employee_id,)).fetchone()

    conn.close()

    return row
def get_overrides_for_submission(submission_id):
    conn = get_connection()

    rows = conn.execute("""
    SELECT 
        overrides.id,
        overrides.receipt_id,
        overrides.old_verdict,
        overrides.new_verdict,
        overrides.comment,
        overrides.created_at
    FROM overrides
    JOIN receipts ON receipts.id = overrides.receipt_id
    WHERE receipts.submission_id = ?
    ORDER BY overrides.created_at ASC
    """, (submission_id,)).fetchall()

    conn.close()

    return rows