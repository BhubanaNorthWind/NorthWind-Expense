# Northwind Expense Pre-Review System

## Overview

This is a lightweight expense pre-review system built using FastAPI, SQLite, and policy-based retrieval.

Features:

* Employee submission management
* Receipt upload and review
* Policy-backed expense validation
* Reviewer overrides with comments
* Policy Q&A
* Evaluation harness

## Note

I did not use an external LLM API because I currently do not have access to an API key.

The solution uses a deterministic rule-based review engine and policy retrieval approach that runs completely locally.

## How to Run

Clone the repository:

```bash
git clone <your-github-repo-url>
cd northwind-expense-minimal
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Windows

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Run Evaluation

```bash
python eval/run_eval.py
```

Expected result:

```text
Passed 27/27 checks
```
