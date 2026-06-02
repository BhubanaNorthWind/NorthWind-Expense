from fastapi import FastAPI
from app.db import init_db
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import init_db, create_employee, get_all_employees

app = FastAPI(title="Northwind Expense Pre-Review")


@app.on_event("startup")
def startup():
    init_db()


templates = Jinja2Templates(directory="templates")


@app.get("/")
def dashboard(request: Request):
    employees = get_all_employees()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "employees": employees
        }
    )

@app.get("/new")
def new_employee(request: Request):
    return templates.TemplateResponse(
        "new.html",
        {"request": request}
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