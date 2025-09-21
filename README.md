# MDT App

A secure, browser-based MDT (Multidisciplinary Team) workflow app implemented with **FastAPI**, **Jinja2**, and **SQLModel**.

## Features (per spec)
- Patient Registration with unique Hospital Number and validation
- MDT Case Entry & Scheduling (unlocked after registration)
- MDT Meeting Consensus capture
- Search by MDT Date range and by Hospital Number
- Read-only MDT details page and PDF preview/download (A4, configurable margins)
- Admin configuration for report/treatment types and PDF margins
- Role-based access (user/admin), basic session auth
- Full audit timestamps

> Target Python: **3.13**

## Quickstart

```bash
# (optional) create venv
python3.13 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -U pip
pip install -e .

# run dev server
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Admin bootstrap
First run will create a default admin if none exists:
- user: `admin@example.com`
- password: `adminadmin`  (change in Admin > Users)

## Notes
- PDF rendering uses WeasyPrint. On some systems you may need system packages (e.g., `libpango`, `gdk-pixbuf`, `libffi`) installed.
- This is a reference implementation meant to be extended.
