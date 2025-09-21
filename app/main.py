from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from .db import init_db, async_session
from .models import *
from .config import settings
from .security import get_session, set_session, clear_session
from .utils import calculate_age_display
import json

app = FastAPI(title=settings.app_name)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup():
    await init_db()
    # bootstrap admin if missing
    async with async_session() as sess:
        res = await sess.exec(select(User).where(User.email == "admin@example.com"))
        admin = res.first()
        if not admin:
            sess.add(User(email="admin@example.com", password_hash="$2b$12$wF45M9xTShmJgG5H7ZrUeO3zLtzqK0mA9yXWg3k7h3QWm3b4b9zWe", role="admin"))  # bcrypt('adminadmin')
            await sess.commit()

def require_auth(request: Request):
    sess = get_session(request)
    if not sess:
        raise HTTPException(status_code=302, detail="Login required")
    return sess

@app.get("/", response_class=HTMLResponse)
async def opening_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Auth ---
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    from passlib.hash import bcrypt
    async with async_session() as sess:
        res = await sess.exec(select(User).where(User.email == email, User.active == True))
        user = res.first()
        if not user or not bcrypt.verify(password, user.password_hash):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"}, status_code=400)
        resp = RedirectResponse(url="/", status_code=302)
        set_session(resp, {"user_id": user.id, "email": user.email, "role": user.role})
        return resp

@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=302)
    clear_session(resp)
    return resp

# --- Patient Registration ---
@app.get("/patients/register", response_class=HTMLResponse)
async def patient_form(request: Request):
    return templates.TemplateResponse("patient_register.html", {"request": request})

@app.post("/patients/register", response_class=HTMLResponse)
async def patient_register(
    request: Request,
    name: str = Form(...),
    hospital_number: str = Form(...),
    dob: str = Form(...),
    phone_primary: str = Form(...),
    address: str = Form(...),
    pin_code: str | None = Form(None),
    digi_pin: str | None = Form(None),
    additional_phones: str | None = Form(None),
):
    from datetime import datetime
    try:
        dob_dt = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        return templates.TemplateResponse("patient_register.html", {"request": request, "error": "Invalid DOB"}, status_code=400)

    async with async_session() as sess:
        p = Patient(
            name=name.strip(),
            hospital_number=hospital_number.strip(),
            dob=dob_dt,
            phone_primary=phone_primary.strip(),
            address=address.strip(),
            pin_code=pin_code.strip() if pin_code else None,
            digi_pin=digi_pin.strip() if digi_pin else None,
            additional_phones_json=additional_phones or "[]",
        )
        sess.add(p)
        try:
            await sess.commit()
        except IntegrityError:
            await sess.rollback();
            return templates.TemplateResponse("patient_register.html", {"request": request, "error": "Duplicate Hospital Number"}, status_code=400)

    return RedirectResponse(url=f"/cases/new?hn={hospital_number}", status_code=302)

# --- MDT Case Entry & Scheduling ---
@app.get("/cases/new", response_class=HTMLResponse)
async def mdt_case_form(request: Request, hn: str):
    async with async_session() as sess:
        pres = await sess.exec(select(Patient).where(Patient.hospital_number == hn))
        patient = pres.first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        age = calculate_age_display(patient.dob)
    return templates.TemplateResponse("case_entry.html", {"request": request, "patient": patient, "age": age})

@app.post("/cases/new")
async def mdt_case_create(
    request: Request,
    hospital_number: str = Form(...),
    clinical_history: str | None = Form(None),
    provisional_diagnosis: str | None = Form(None),
    discussion_for: str | None = Form(None),
    scheduled_reason: str | None = Form(None),
    scheduled_date: str | None = Form(None),
):
    from datetime import datetime
    async with async_session() as sess:
        pres = await sess.exec(select(Patient).where(Patient.hospital_number == hospital_number))
        patient = pres.first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        dt = None
        if scheduled_date:
            try:
                dt = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        case = MDTCase(
            patient_id=patient.id,
            clinical_history=clinical_history,
            provisional_diagnosis=provisional_diagnosis,
            discussion_for=discussion_for,
            scheduled_reason=scheduled_reason,
            scheduled_date=dt,
        )
        sess.add(case)
        await sess.commit()
        await sess.refresh(case)

        # Prompt if missing date
        if not dt:
            request.session = {}
            return RedirectResponse(url=f"/cases/{case.id}/edit?prompt_no_date=1", status_code=302)

    return RedirectResponse(url=f"/cases/{case.id}/edit", status_code=302)

@app.get("/cases/{case_id}/edit", response_class=HTMLResponse)
async def mdt_case_edit(request: Request, case_id: int, prompt_no_date: int | None = None):
    async with async_session() as sess:
        q = select(MDTCase).where(MDTCase.id == case_id).options(
            selectinload(MDTCase.patient),
            selectinload(MDTCase.pathology_reports),
            selectinload(MDTCase.imaging_reports),
            selectinload(MDTCase.treatments),
            selectinload(MDTCase.consensus),
        )
        case = (await sess.exec(q)).first()
        if not case:
            raise HTTPException(404, "Case not found")
        age = calculate_age_display(case.patient.dob)
    return templates.TemplateResponse("case_entry_edit.html", {"request": request, "case": case, "age": age, "prompt_no_date": prompt_no_date})

# Simplified add endpoints for dynamic sections (pathology/imaging/treatment) omitted for brevity.

# --- Search by MDT Date ---
@app.get("/search/date", response_class=HTMLResponse)
async def search_by_date(request: Request, start: str | None = None, end: str | None = None):
    from datetime import datetime
    items = []
    if start and end:
        try:
            sd = datetime.strptime(start, "%Y-%m-%d").date()
            ed = datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            sd = ed = None
        if sd and ed:
            async with async_session() as sess:
                q = select(MDTCase).where(MDTCase.scheduled_date >= sd, MDTCase.scheduled_date <= ed).options(selectinload(MDTCase.patient))
                items = list((await sess.exec(q)).all())
    return templates.TemplateResponse("search_date.html", {"request": request, "items": items})

# --- Search by Hospital Number ---
@app.get("/search/hn", response_class=HTMLResponse)
async def search_by_hn(request: Request, hn: str | None = None):
    results = []
    if hn:
        async with async_session() as sess:
            q = select(MDTCase).join(Patient).where(Patient.hospital_number == hn).options(selectinload(MDTCase.patient))
            results = list((await sess.exec(q)).all())
    return templates.TemplateResponse("search_hn.html", {"request": request, "results": results, "hn": hn or ""})

@app.get("/cases/{case_id}/details", response_class=HTMLResponse)
async def case_details(request: Request, case_id: int):
    async with async_session() as sess:
        q = select(MDTCase).where(MDTCase.id == case_id).options(
            selectinload(MDTCase.patient),
            selectinload(MDTCase.pathology_reports),
            selectinload(MDTCase.imaging_reports),
            selectinload(MDTCase.treatments),
            selectinload(MDTCase.consensus),
        )
        case = (await sess.exec(q)).first()
        if not case:
            raise HTTPException(404, "Case not found")
        age = calculate_age_display(case.patient.dob)
    return templates.TemplateResponse("mdt_details.html", {"request": request, "case": case, "age": age})

# --- Consensus ---
@app.get("/cases/{case_id}/consensus", response_class=HTMLResponse)
async def consensus_form(request: Request, case_id: int):
    async with async_session() as sess:
        q = select(MDTCase).where(MDTCase.id == case_id).options(selectinload(MDTCase.patient))
        case = (await sess.exec(q)).first()
        if not case:
            raise HTTPException(404, "Case not found")
        age = calculate_age_display(case.patient.dob)
    return templates.TemplateResponse("consensus.html", {"request": request, "case": case, "age": age})

@app.post("/cases/{case_id}/consensus")
async def consensus_save(case_id: int, consensus_text: str = Form(...), followups: str = Form("")):
    async with async_session() as sess:
        q = select(MDTCase).where(MDTCase.id == case_id)
        case = (await sess.exec(q)).first()
        if not case:
            raise HTTPException(404, "Case not found")
        # mark Done
        case.status = "Done"
        res = await sess.exec(select(Consensus).where(Consensus.mdt_case_id == case_id))
        existing = res.first()
        if existing:
            existing.consensus_text = consensus_text
            existing.followups_json = followups or "[]"
        else:
            sess.add(Consensus(mdt_case_id=case_id, consensus_text=consensus_text, followups_json=followups or "[]"))
        await sess.commit()
    return RedirectResponse(url=f"/cases/{case_id}/details", status_code=302)

# --- PDF Preview ---
@app.get("/cases/{case_id}/preview.pdf")
async def preview_pdf(case_id: int):
    from weasyprint import HTML, CSS
    from fastapi.responses import StreamingResponse
    async with async_session() as sess:
        q = select(MDTCase).where(MDTCase.id == case_id).options(
            selectinload(MDTCase.patient),
            selectinload(MDTCase.pathology_reports),
            selectinload(MDTCase.imaging_reports),
            selectinload(MDTCase.treatments),
            selectinload(MDTCase.consensus),
        )
        case = (await sess.exec(q)).first()
        if not case:
            raise HTTPException(404, "Case not found")

    html = f"""
    <html>
    <head>
        <meta charset='utf-8'/>
        <style>
            body {{ font-family: sans-serif; }}
            h1 {{ margin-bottom: 0; }}
            .muted {{ color: #666; }}
            .section {{ margin-top: 12px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            td, th {{ border: 1px solid #ddd; padding: 6px; vertical-align: top; }}
            .badge {{ padding: 2px 6px; border-radius: 4px; background: #eee; }}
        </style>
    </head>
    <body>
      <h1>MDT Case #{case.id}</h1>
      <div class='muted'>Patient: {case.patient.name} — HN {case.patient.hospital_number}</div>
      <div class='muted'>DOB {case.patient.dob} — Status <span class='badge'>{case.status}</span></div>

      <div class='section'><strong>Clinical History</strong><br/>{case.clinical_history or "-"}</div>
      <div class='section'><strong>Provisional Diagnosis</strong><br/>{case.provisional_diagnosis or "-"}</div>
      <div class='section'><strong>Discussion For</strong><br/>{case.discussion_for or "-"}</div>
      <div class='section'><strong>Scheduled</strong><br/>{case.scheduled_reason or "-"} ({case.scheduled_date or "—"})</div>

      <div class='section'><strong>Pathology Reports</strong>
        <table>
          <tr><th>Date</th><th>Type</th><th>Investigation Details</th></tr>
          {''.join(f"<tr><td>{r.date_of_report}</td><td>{r.report_type}</td><td>{r.investigation_details or '-'}</td></tr>" for r in case.pathology_reports)}
        </table>
      </div>

      <div class='section'><strong>Imaging Reports</strong>
        <table>
          <tr><th>Date</th><th>Type</th><th>Investigation Details</th></tr>
          {''.join(f"<tr><td>{r.date_of_report}</td><td>{r.report_type}</td><td>{r.investigation_details or '-'}</td></tr>" for r in case.imaging_reports)}
        </table>
      </div>

      <div class='section'><strong>Treatment History</strong>
        <table>
          <tr><th>Type</th><th>Key Fields</th></tr>
          {''.join(f"<tr><td>{t.treatment_type}</td><td>{t.chemo_protocol or t.radiation_dose or t.surgery_done or t.other_notes or '-'}</td></tr>" for t in case.treatments)}
        </table>
      </div>

      <div class='section'><strong>Consensus & Follow-ups</strong><br/>{(case.consensus and case.consensus.consensus_text) or '-'}
        <div>Follow-ups: {(case.consensus and case.consensus.followups_json) or '[]'}</div>
      </div>

    </body>
    </html>
    """
    pdf = HTML(string=html).write_pdf()
    return StreamingResponse(iter([pdf]), media_type="application/pdf")
