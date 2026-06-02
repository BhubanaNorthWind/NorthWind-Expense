from typing import List
from fastapi import FastAPI
from app.db import init_db
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.seed_data import seed_employees
from app.receipt import save_uploaded_receipt, analyze_receipt

from app.db import (
    init_db,
    create_employee,
    get_all_employees,
    get_employee,
    create_submission,
    get_submission,
    save_receipt,
)

app = FastAPI(title="Northwind Expense Pre-Review")


@app.on_event("startup")
def startup():
    init_db()
    seed_employees()


templates = Jinja2Templates(directory="templates")


@app.get("/")
def dashboard(request: Request):
    employees = get_all_employees()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "employees": employees
        }
    )

@app.get("/new")
def new_employee(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="new.html",
        context={}
    )

@app.post("/new")
def save_employee(
    employee_name: str = Form(...),
    employee_grade: str = Form(...),
    department: str = Form(...),
    manager: str = Form(...),
    trip_purpose: str = Form(...),
    trip_start_date: str = Form(...),
    trip_end_date: str = Form(...)
):

    create_employee(
        employee_name,
        employee_grade,
        department,
        manager,
        trip_purpose,
        trip_start_date,
        trip_end_date
    )

    return RedirectResponse(
        "/",
        status_code=303
    )

@app.get("/employee/{employee_id}/submission")
def start_submission(employee_id: int):
    employee = get_employee(employee_id)

    if employee is None:
        return RedirectResponse(
            "/",
            status_code=303
        )

    submission_id = create_submission(employee_id)

    return RedirectResponse(
        f"/submissions/{submission_id}",
        status_code=303
    )

@app.get("/submissions/{submission_id}")
def submission_detail(request: Request, submission_id: int):
    submission, receipts = get_submission(submission_id)

    if submission is None:
        return RedirectResponse(
            "/",
            status_code=303
        )

    employee = get_employee(submission["employee_id"])

    return templates.TemplateResponse(
        request=request,
        name="submission.html",
        context={
            "submission": submission,
            "employee": employee,
            "receipts": receipts
        }
    )
@app.post("/submissions/{submission_id}/upload")
def upload_receipts(
    submission_id: int,
    files: List[UploadFile] = File(...)
):
    submission, _ = get_submission(submission_id)

    if submission is None:
        return RedirectResponse(
            "/",
            status_code=303
        )

    for uploaded_file in files:
        try:
            file_path = save_uploaded_receipt(
                uploaded_file,
                submission_id
            )

            result = analyze_receipt(file_path)

            save_receipt(
                submission_id=submission_id,
                filename=uploaded_file.filename,
                file_path=str(file_path),
                vendor=result.get("vendor"),
                amount=result.get("amount"),
                category=result.get("category"),
                verdict=result.get("verdict"),
                reason=result.get("reason")
            )

        except Exception as error:
            save_receipt(
                submission_id=submission_id,
                filename=uploaded_file.filename or "unknown_file",
                file_path="",
                vendor="Upload error",
                amount=None,
                category="unknown",
                verdict="needs_human_review",
                reason=f"Upload or receipt analysis failed: {error}"
            )

    return RedirectResponse(
        f"/submissions/{submission_id}",
        status_code=303
    )