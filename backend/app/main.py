from datetime import datetime, timezone
import os
import math
import json
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import Base, engine, get_db
from .models import CBCResult, ResultReview, AuditEvent, AnalyteConfig, ReportTemplate, UserAccount, ReferenceInterval, ResultDocument, ClinicProfile
from .schemas import AnalyzerPayload, ResultOut, ManualSample, ReviewIn, AnalyteIn
from .security import authenticate, create_access_token, hash_password, decode_access_token
from fastapi import Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from docxtpl import DocxTemplate
from docx import Document
from docx.shared import Inches
import subprocess, tempfile, shutil, zipfile

app = FastAPI(title="CBC Connect API", version="0.2.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "PUT"],
                   allow_headers=["Content-Type", "Authorization", "X-Device-Id", "X-Analyzer-Key"])
TEMPLATE_DIR = Path(os.getenv("TEMPLATE_DIR", "./data/templates"))
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENT_DIR = Path(os.getenv('DOCUMENT_DIR', './data/documents'))
DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

@app.on_event("startup")
def bootstrap_admin():
    username = os.getenv("CBC_BOOTSTRAP_ADMIN")
    password = os.getenv("CBC_BOOTSTRAP_PASSWORD")
    if username and password:
        db = next(get_db())
        try:
            if not db.query(UserAccount).filter_by(username=username).first():
                db.add(UserAccount(username=username, password_hash=hash_password(password), role="ADMIN", active=True))
                db.commit()
        finally:
            db.close()


@app.on_event("startup")
def seed_draft_reference_intervals():
    """Load the sourced adult comparator catalogue as DRAFT records, never clinically active by default."""
    catalogue = Path(__file__).resolve().parent.parent / "demo" / "cbc_adult_reference_intervals_draft.json"
    if not catalogue.exists():
        return
    db = next(get_db())
    try:
        data = json.loads(catalogue.read_text(encoding="utf-8"))
        for row in data.get("intervals", []):
            exists = db.query(ReferenceInterval).filter_by(
                analyte_code=row["analyte_code"], population=row["population"],
                sex=row.get("sex", "ALL"), source=row["source"],
                lower_value=float(row["lower_value"]), upper_value=float(row["upper_value"]),
                unit=row["unit"]
            ).first()
            if not exists:
                db.add(ReferenceInterval(
                    analyte_code=row["analyte_code"], population=row["population"],
                    sex=row.get("sex", "ALL"), lower_value=float(row["lower_value"]),
                    upper_value=float(row["upper_value"]), unit=row["unit"],
                    source=row["source"], created_by="catalogue-import", status="DRAFT"
                ))
        db.commit()
    finally:
        db.close()

@app.middleware("http")
async def require_api_auth(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith("/api/v1/") or path == "/api/v1/auth/login":
        return await call_next(request)
    if path == "/api/v1/analyzer/ingest":
        expected = os.getenv("CBC_ANALYZER_API_KEY")
        if not expected:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=503, content={"detail":"Analyzer API key is not configured"})
        if request.headers.get("x-analyzer-key") != expected:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail":"Invalid analyzer API key"})
        return await call_next(request)
    from fastapi.responses import JSONResponse
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail":"Authentication required"})
    try:
        user = decode_access_token(header[7:])
    except Exception:
        return JSONResponse(status_code=401, content={"detail":"Invalid or expired token"})
    role = user.get("role")
    if path.endswith("/review") and role not in {"TECHNICIAN","SUPERVISOR","ADMIN","CLINICIAN"}:
        return JSONResponse(status_code=403, content={"detail":"Insufficient role"})
    if (request.method != "GET" and ("/analytes" in path or "/templates" in path or path.startswith("/api/v1/clinic-profile")) and role not in {"SUPERVISOR","ADMIN"}):
        return JSONResponse(status_code=403, content={"detail":"Supervisor or administrator role required"})
    request.state.user = user
    return await call_next(request)

@app.post("/api/v1/auth/login")
def login(payload: dict, db: Session = Depends(get_db)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    user = db.query(UserAccount).filter_by(username=username, active=True).first()
    if not user or not authenticate(password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    return {"access_token": create_access_token({"sub": user.username, "role": user.role}),
            "token_type":"bearer", "role":user.role}


def audit(db: Session, actor: str, action: str, result_id: int | None = None, details: dict | None = None):
    db.add(AuditEvent(result_id=result_id, actor=actor, action=action, details=details or {}))

@app.get("/health")
def health():
    return {"status": "ok", "service": "cbc-connect-api"}

@app.get("/api/v1/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total = db.query(CBCResult).count()
    pending = db.query(CBCResult).filter(CBCResult.status == "PENDING_REVIEW").count()
    reviewed = db.query(CBCResult).filter(CBCResult.status == "REVIEWED").count()
    return {"total": total, "pending": pending, "reviewed": reviewed}

@app.get("/api/v1/results", response_model=list[ResultOut])
def list_results(status: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CBCResult).order_by(CBCResult.received_at.desc())
    if status and status != "ALL":
        query = query.filter(CBCResult.status == status.upper())
    if q:
        term = f"%{q.strip()}%"
        query = query.filter((CBCResult.sample_id.ilike(term)) | (CBCResult.patient_reference.ilike(term)))
    return query.limit(500).all()

@app.get("/api/v1/results/{result_id}")
def result_detail(result_id: int, db: Session = Depends(get_db)):
    result = db.get(CBCResult, result_id)
    if not result:
        raise HTTPException(404, "Result not found")
    review = db.query(ResultReview).filter_by(result_id=result_id).first()
    events = db.query(AuditEvent).filter_by(result_id=result_id).order_by(AuditEvent.created_at.desc()).all()
    documents = db.query(ResultDocument).filter_by(result_id=result_id).order_by(ResultDocument.uploaded_at.desc()).all()
    codes = list(result.values.keys())
    intervals = db.query(ReferenceInterval).filter(ReferenceInterval.analyte_code.in_(codes)).order_by(ReferenceInterval.analyte_code, ReferenceInterval.sex).all() if codes else []
    document_rows = [{"id": d.id, "filename": d.filename, "content_type": d.content_type,
                      "uploaded_by": d.uploaded_by, "notes": d.notes, "uploaded_at": d.uploaded_at,
                      "parent_document_id": d.parent_document_id, "document_kind": d.document_kind}
                     for d in documents]
    return {"result": ResultOut.model_validate(result), "review": review, "audit": events,
            "documents": document_rows, "reference_intervals": intervals}

@app.post("/api/v1/samples", response_model=ResultOut, status_code=201)
def create_sample(payload: ManualSample, request: Request, db: Session = Depends(get_db)):
    result = CBCResult(sample_id=payload.sample_id, patient_reference=payload.patient_reference,
        patient_name=payload.patient_name, patient_age=payload.patient_age, patient_address=payload.patient_address,
        analyzer="MANUAL", device_id="manual-entry", observed_at=payload.collected_at,
        status="PENDING_REVIEW", values={})
    db.add(result)
    try:
        db.flush()
        audit(db, request.state.user.get("sub", "staff"), "SAMPLE_REGISTERED", result.id,
              {"sample_id": payload.sample_id, "patient_reference": payload.patient_reference})
        db.commit()
        db.refresh(result)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This sample is already registered")
    return result

@app.post("/api/v1/analyzer/ingest", response_model=ResultOut, status_code=201)
def ingest(payload: AnalyzerPayload, response: Response,
           x_device_id: str = Header(default="unregistered-device"), db: Session = Depends(get_db)):
    incoming_patient_fields = [field for field in ("patient_reference", "patient_name", "patient_age", "patient_address")
                               if getattr(payload, field) is not None and str(getattr(payload, field)).strip()]
    existing = db.query(CBCResult).filter_by(sample_id=payload.sample_id, device_id=x_device_id).first()
    if existing:
        # Analyzer retries may safely enrich missing biodata, but never replace
        # existing identity values or the original CBC measurements.
        enriched_fields = []
        for field in incoming_patient_fields:
            incoming_value = getattr(payload, field)
            if not str(getattr(existing, field) or "").strip():
                setattr(existing, field, incoming_value)
                enriched_fields.append(field)
        if enriched_fields:
            existing.patient_fields_from_analyzer = sorted(
                set(existing.patient_fields_from_analyzer or []) | set(enriched_fields)
            )
            audit(db, "analyzer:" + x_device_id, "RESULT_BIODATA_ENRICHED_FROM_ANALYZER",
                  existing.id, {"sample_id": payload.sample_id, "fields": enriched_fields})
            db.commit()
            db.refresh(existing)
        response.status_code = 200
        return existing
    result = db.query(CBCResult).filter_by(sample_id=payload.sample_id, device_id="manual-entry", analyzer="MANUAL").first()
    values = {key: measurement.model_dump() for key, measurement in payload.values.items()}
    if result:
        result.patient_reference = payload.patient_reference or result.patient_reference
        result.patient_name = payload.patient_name or result.patient_name
        result.patient_age = payload.patient_age or result.patient_age
        result.patient_address = payload.patient_address or result.patient_address
        result.patient_fields_from_analyzer = sorted(set(result.patient_fields_from_analyzer or []) | set(incoming_patient_fields))
        result.analyzer = payload.analyzer
        result.device_id = x_device_id
        result.observed_at = payload.observed_at
        result.values = values
        audit(db, "analyzer:" + x_device_id, "RESULT_ATTACHED_TO_REGISTERED_SAMPLE", result.id,
              {"analyzer": payload.analyzer, "sample_id": payload.sample_id})
    else:
        result = CBCResult(sample_id=payload.sample_id, patient_reference=payload.patient_reference,
            patient_name=payload.patient_name, patient_age=payload.patient_age, patient_address=payload.patient_address,
            patient_fields_from_analyzer=incoming_patient_fields,
            analyzer=payload.analyzer, device_id=x_device_id, observed_at=payload.observed_at,
            status="PENDING_REVIEW", values=values)
        db.add(result)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="A result for this sample and device already exists")
        audit(db, "analyzer:" + x_device_id, "RESULT_RECEIVED", result.id,
              {"analyzer": payload.analyzer, "sample_id": payload.sample_id})
    db.commit()
    db.refresh(result)
    return result

@app.post("/api/v1/results/{result_id}/review")
def review_result(result_id: int, payload: ReviewIn, request: Request, db: Session = Depends(get_db)):
    result = db.get(CBCResult, result_id)
    if not result:
        raise HTTPException(404, "Result not found")
    if result.status != "PENDING_REVIEW":
        raise HTTPException(409, "Only pending results can be reviewed")
    if db.query(ResultReview).filter_by(result_id=result_id).first():
        raise HTTPException(409, "A review already exists for this result")
    original_keys = set(result.values)
    reviewed_keys = set(payload.reviewed_values)
    if original_keys != reviewed_keys:
        raise HTTPException(422, "Reviewed analytes must match the received analyte set")
    corrected = {k: v.model_dump() for k, v in payload.reviewed_values.items()}
    reviewer_identity = request.state.user.get("sub", "staff")
    unknown_comment_codes = set(payload.analyte_comments) - original_keys
    if unknown_comment_codes:
        raise HTTPException(422, "Per-analyte comments must match received analytes")
    cleaned_comments = {k: str(v).strip() for k, v in payload.analyte_comments.items() if str(v).strip()}
    reviewer_account = db.query(UserAccount).filter_by(username=reviewer_identity, active=True).first()
    is_clinician = bool(reviewer_account and reviewer_account.role == "CLINICIAN")
    if is_clinician and not all([reviewer_account.full_name, reviewer_account.credentials, reviewer_account.signature_path]):
        raise HTTPException(422, "Complete your clinician signatory profile, including a signature image, before recording a clinician review")
    review = ResultReview(result_id=result_id, reviewer=reviewer_identity,
                          comments=payload.comments, analyte_comments=cleaned_comments, reviewed_values=corrected,
                          signatory_name=(reviewer_account.full_name if is_clinician else None),
                          signatory_credentials=(reviewer_account.credentials if is_clinician else None),
                          signatory_signature_path=(reviewer_account.signature_path if is_clinician else None),
                          signatory_stamp_path=(reviewer_account.stamp_path if is_clinician else None))
    db.add(review)
    result.status = "REVIEWED"
    audit(db, reviewer_identity, "RESULT_REVIEWED", result_id,
          {"comments": payload.comments, "analyte_comments": list(cleaned_comments.keys()), "corrections_made": corrected != result.values})
    db.commit()
    return {"message": "Review recorded", "status": result.status, "reviewed_at": review.reviewed_at}


@app.post("/api/v1/results/{result_id}/documents", status_code=201)
async def upload_result_document(result_id: int, request: Request,
                                 file: UploadFile = File(...), notes: str = Form(""),
                                 db: Session = Depends(get_db)):
    result = db.get(CBCResult, result_id)
    if not result:
        raise HTTPException(404, "Result not found")
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {
        ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if suffix not in allowed:
        raise HTTPException(415, "Upload a PDF, DOC, DOCX, PNG or JPG source report")
    content = await file.read()
    if not content or len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "Document must be between 1 byte and 15 MB")
    valid = ((suffix == ".pdf" and content.startswith(b"%PDF-")) or
             (suffix == ".png" and content[:8] == bytes([137,80,78,71,13,10,26,10])) or
             (suffix in {".jpg", ".jpeg"} and content[:3] == bytes([255,216,255])) or
             (suffix == ".doc" and content.startswith(bytes([0xD0,0xCF,0x11,0xE0,0xA1,0xB1,0x1A,0xE1]))))
    if suffix == ".docx":
        try:
            import io
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                valid = "word/document.xml" in archive.namelist() and archive.testzip() is None
        except (zipfile.BadZipFile, OSError):
            valid = False
    if not valid:
        raise HTTPException(415, "The file content does not match its document extension")
    stored_name = os.urandom(16).hex() + suffix
    target = DOCUMENT_DIR / stored_name
    target.write_bytes(content)
    actor = request.state.user.get("sub", "staff")
    item = ResultDocument(result_id=result_id, filename=Path(file.filename or stored_name).name,
        content_type=allowed[suffix], storage_path=str(target), uploaded_by=actor, notes=notes.strip() or None)
    db.add(item)
    audit(db, actor, "RESULT_SOURCE_DOCUMENT_UPLOADED", result_id,
          {"filename": item.filename, "content_type": item.content_type})
    db.commit()
    db.refresh(item)
    return {"id": item.id, "filename": item.filename, "content_type": item.content_type,
            "uploaded_by": item.uploaded_by, "notes": item.notes, "uploaded_at": item.uploaded_at}


@app.get("/api/v1/results/{result_id}/documents/{document_id}/preview")
def preview_result_document(result_id: int, document_id: int, db: Session = Depends(get_db)):
    item = db.query(ResultDocument).filter_by(id=document_id, result_id=result_id).first()
    if not item or not Path(item.storage_path).is_file():
        raise HTTPException(404, "Source document not found")
    suffix = Path(item.filename).suffix.lower()
    if suffix not in {".doc", ".docx"}:
        return FileResponse(item.storage_path, media_type=item.content_type,
                            filename=item.filename, content_disposition_type="inline",
                            headers={"X-Content-Type-Options": "nosniff"})
    workdir = Path(tempfile.mkdtemp(prefix="cbc-doc-preview-"))
    try:
        completed = subprocess.run(
            ["libreoffice", "-env:UserInstallation=file://" + str(workdir / "profile"),
             "--headless", "--convert-to", "pdf", "--outdir", str(workdir), item.storage_path],
            capture_output=True, text=True, timeout=45, check=False
        )
        converted = workdir / (Path(item.storage_path).stem + ".pdf")
        if completed.returncode != 0 or not converted.is_file():
            shutil.rmtree(workdir, ignore_errors=True)
            raise HTTPException(422, "This Word document could not be converted for preview or printing")
        return FileResponse(str(converted), media_type="application/pdf",
                            filename=Path(item.filename).stem + ".pdf",
                            content_disposition_type="inline",
                            headers={"X-Content-Type-Options": "nosniff"},
                            background=BackgroundTask(shutil.rmtree, str(workdir), ignore_errors=True))
    except subprocess.TimeoutExpired:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(422, "Word document conversion timed out")

@app.get("/api/v1/results/{result_id}/documents/{document_id}")
def view_result_document(result_id: int, document_id: int, db: Session = Depends(get_db)):
    item = db.query(ResultDocument).filter_by(id=document_id, result_id=result_id).first()
    if not item or not Path(item.storage_path).is_file():
        raise HTTPException(404, "Source document not found")
    return FileResponse(item.storage_path, media_type=item.content_type,
                        filename=item.filename, content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff"})


@app.post("/api/v1/results/{result_id}/documents/{document_id}/annotated", status_code=201)
async def save_annotated_document(result_id: int, document_id: int, request: Request,
                                  file: UploadFile = File(...), annotations: str = Form("{}"),
                                  db: Session = Depends(get_db)):
    source = db.query(ResultDocument).filter_by(id=document_id, result_id=result_id).first()
    if not source or source.parent_document_id is not None:
        raise HTTPException(404, "Original source document not found")
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    if suffix not in allowed:
        raise HTTPException(415, "Annotated copy must be a PDF, PNG or JPG")
    content = await file.read()
    if not content or len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Annotated copy must be between 1 byte and 20 MB")
    valid = ((suffix == ".pdf" and content.startswith(b"%PDF-")) or
             (suffix == ".png" and content[:8] == bytes([137,80,78,71,13,10,26,10])) or
             (suffix in {".jpg", ".jpeg"} and content[:3] == bytes([255,216,255])))
    if not valid:
        raise HTTPException(415, "The file content does not match its extension")
    try:
        annotation_data = __import__("json").loads(annotations)
        if not isinstance(annotation_data, dict) or len(annotations) > 500000:
            raise ValueError()
    except Exception:
        raise HTTPException(422, "Invalid annotation data")
    target = DOCUMENT_DIR / (os.urandom(16).hex() + suffix)
    target.write_bytes(content)
    actor = request.state.user.get("sub", "staff")
    item = ResultDocument(result_id=result_id, filename="ANNOTATED-" + Path(source.filename).stem + suffix,
        content_type=allowed[suffix], storage_path=str(target), uploaded_by=actor,
        parent_document_id=source.id, document_kind="ANNOTATED", annotation_data=annotation_data)
    db.add(item)
    db.flush()
    audit(db, actor, "RESULT_DOCUMENT_ANNOTATED_COPY_SAVED", result_id,
          {"source_document_id": source.id, "annotated_document_id": item.id, "filename": item.filename})
    db.commit()
    db.refresh(item)
    return {"id": item.id, "filename": item.filename, "content_type": item.content_type,
            "uploaded_by": item.uploaded_by, "uploaded_at": item.uploaded_at,
            "parent_document_id": item.parent_document_id, "document_kind": item.document_kind}

@app.patch("/api/v1/results/{result_id}/documents/{document_id}/notes")
def update_result_document_notes(result_id: int, document_id: int, payload: dict,
                                 request: Request, db: Session = Depends(get_db)):
    item = db.query(ResultDocument).filter_by(id=document_id, result_id=result_id).first()
    if not item:
        raise HTTPException(404, "Source document not found")
    notes = str(payload.get("notes", "")).strip()
    if len(notes) > 5000:
        raise HTTPException(422, "Notes must be 5,000 characters or fewer")
    item.notes = notes or None
    actor = request.state.user.get("sub", "staff")
    audit(db, actor, "RESULT_DOCUMENT_NOTES_UPDATED", result_id, {"document_id": document_id})
    db.commit()
    return {"id": item.id, "notes": item.notes}



@app.post("/api/v1/results/{result_id}/demo-document", status_code=201)
def create_synthetic_demo_document(result_id: int, request: Request, db: Session = Depends(get_db)):
    result = db.get(CBCResult, result_id)
    if not result:
        raise HTTPException(404, "Result not found")
    if result.sample_id != "SYNTH-CBC-0001" or "SIMULATED" not in result.analyzer.upper():
        raise HTTPException(403, "This feature is available only for the labelled synthetic demo result")
    existing = db.query(ResultDocument).filter_by(result_id=result_id, filename="SYNTH-CBC-0001-demo-report.pdf").first()
    if existing and Path(existing.storage_path).is_file():
        return {"created": False, "document_id": existing.id, "message": "The synthetic demo report already exists."}
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    target = DOCUMENT_DIR / (os.urandom(16).hex() + ".pdf")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("CBC Connect — Sample CBC Report", styles["Title"]),
        Paragraph("SYNTHETIC TRAINING DATA ONLY — NOT A PATIENT REPORT", styles["Heading2"]),
        Spacer(1, 10),
        Paragraph("Fictional example for demonstrating the source-document viewer and review workflow. It is not an authentic analyzer export and contains no patient identifiers or clinical reference intervals.", styles["BodyText"]),
        Spacer(1, 12),
        Paragraph("<b>Sample ID:</b> SYNTH-CBC-0001 &nbsp;&nbsp; <b>Analyzer:</b> HumaCount 30TS (SIMULATED)", styles["BodyText"]),
        Spacer(1, 12)
    ]
    rows = [["Parameter", "Illustrative result", "Unit", "Flag"]]
    for code, measurement in result.values.items():
        rows.append([code, str(measurement.get("value", "")), str(measurement.get("unit") or ""), str(measurement.get("flag") or "Not supplied")])
    table = Table(rows, repeatRows=1, colWidths=[120, 110, 100, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8f3ff")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE")
    ]))
    story.append(table)
    story.extend([Spacer(1, 16), Paragraph("Training document only. Do not use these values for patient care, diagnosis, treatment, or clinical decision-making.", styles["Italic"])])
    SimpleDocTemplate(str(target), pagesize=A4).build(story)
    actor = request.state.user.get("sub", "staff")
    item = ResultDocument(result_id=result_id, filename="SYNTH-CBC-0001-demo-report.pdf",
        content_type="application/pdf", storage_path=str(target), uploaded_by=actor,
        notes="Synthetic training document; not a real patient report.")
    db.add(item)
    audit(db, actor, "SYNTHETIC_DEMO_DOCUMENT_CREATED", result_id, {"filename": item.filename})
    db.commit()
    db.refresh(item)
    return {"created": True, "document_id": item.id, "filename": item.filename}




@app.patch("/api/v1/results/{result_id}/patient")
def update_patient_details(result_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    result = db.get(CBCResult, result_id)
    if not result:
        raise HTTPException(404, "Result not found")
    fields = {"sample_id": 120, "patient_reference": 120, "patient_name": 200,
              "patient_age": 80, "patient_address": 1000}
    updated = []
    for field, limit in fields.items():
        if field not in payload:
            continue
        value = str(payload.get(field) or "").strip()
        if len(value) > limit:
            raise HTTPException(422, f"{field.replace('_', ' ').title()} must be {limit} characters or fewer")
        current_value = str(getattr(result, field) or "").strip()
        analyzer_fields = set(result.patient_fields_from_analyzer or [])
        if field == "sample_id":
            if not value:
                raise HTTPException(422, "Sample / accession ID cannot be empty")
            if result.device_id != "manual-entry" and value != current_value:
                raise HTTPException(409, "The sample ID was supplied by the analyzer and cannot be changed here")
            duplicate = db.query(CBCResult).filter(
                CBCResult.sample_id == value,
                CBCResult.device_id == result.device_id,
                CBCResult.id != result_id
            ).first()
            if duplicate:
                raise HTTPException(409, "That sample ID already exists for this analyzer device")
        elif field in analyzer_fields and value != current_value:
            raise HTTPException(409, f"{field.replace('_', ' ').title()} was supplied by the analyzer and cannot be edited")
        setattr(result, field, value or None)
        updated.append(field)
    actor = request.state.user.get("sub", "staff")
    audit(db, actor, "PATIENT_AND_SAMPLE_DETAILS_UPDATED", result_id,
          {"fields_updated": updated})
    db.commit()
    return {"sample_id": result.sample_id, "patient_reference": result.patient_reference,
            "patient_name": result.patient_name, "patient_age": result.patient_age,
            "patient_address": result.patient_address}


def _clinic_profile_dict(profile: ClinicProfile):
    return {"clinic_name": profile.clinic_name, "address": profile.address, "phone": profile.phone,
            "email": profile.email, "theme_color": profile.theme_color, "font_color": profile.font_color, "font_family": profile.font_family, "header_text": profile.header_text,
            "footer_text": profile.footer_text, "logo_display_mode": profile.logo_display_mode,
            "logo_opacity": profile.logo_opacity, "has_logo": bool(profile.logo_path),
            "updated_by": profile.updated_by, "updated_at": profile.updated_at}


def _get_or_create_clinic_profile(db: Session):
    profile = db.get(ClinicProfile, 1)
    if profile is None:
        profile = ClinicProfile(id=1, clinic_name="Clinic", address="",
            phone="0775-872-454, 0751-319-201", email="", theme_color="#0879D9", font_color="#243447", font_family="Arial",
            header_text="", footer_text="Powered by ClinicHIS",
            updated_at=datetime.now(timezone.utc))
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@app.get("/api/v1/clinic-profile")
def get_clinic_profile(db: Session = Depends(get_db)):
    return _clinic_profile_dict(_get_or_create_clinic_profile(db))


@app.put("/api/v1/clinic-profile")
def save_clinic_profile(payload: dict, request: Request, db: Session = Depends(get_db)):
    profile = _get_or_create_clinic_profile(db)
    limits = {"clinic_name": 200, "address": 1000, "phone": 120, "email": 160,
              "header_text": 1000, "footer_text": 500}
    for field, limit in limits.items():
        if field in payload:
            value = str(payload.get(field) or "").strip()
            if len(value) > limit:
                raise HTTPException(422, f"{field.replace('_', ' ').title()} must be {limit} characters or fewer")
            setattr(profile, field, value)
    if "logo_display_mode" in payload:
        mode = str(payload.get("logo_display_mode") or "header").strip().lower()
        if mode not in {"header", "watermark", "background", "both"}:
            raise HTTPException(422, "Logo display mode must be header, watermark, background or both")
        profile.logo_display_mode = mode
    if "logo_opacity" in payload:
        try:
            opacity = float(payload.get("logo_opacity"))
        except (TypeError, ValueError):
            raise HTTPException(422, "Logo opacity must be a number between 0.03 and 0.30")
        if not 0.03 <= opacity <= 0.30:
            raise HTTPException(422, "Logo opacity must be between 0.03 and 0.30")
        profile.logo_opacity = opacity
    import re
    if "theme_color" in payload:
        color = str(payload.get("theme_color") or "").strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise HTTPException(422, "Theme colour must be a six-digit hex colour such as #0879D9")
        profile.theme_color = color.upper()
    if "font_color" in payload:
        color = str(payload.get("font_color") or "").strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise HTTPException(422, "Font colour must be a six-digit hex colour such as #243447")
        profile.font_color = color.upper()
    if "font_family" in payload:
        font_family = str(payload.get("font_family") or "").strip()
        allowed_fonts = {"Arial", "Calibri", "Aptos", "Times New Roman", "Georgia", "Verdana", "Tahoma", "Trebuchet MS"}
        if font_family not in allowed_fonts:
            raise HTTPException(422, "Choose a font from the supported clinic document font list")
        profile.font_family = font_family
    profile.updated_by = request.state.user.get("sub", "staff")
    profile.updated_at = datetime.now(timezone.utc)
    audit(db, profile.updated_by, "CLINIC_DOCUMENT_BRANDING_UPDATED",
          details={"clinic_name": profile.clinic_name})
    db.commit()
    db.refresh(profile)
    return _clinic_profile_dict(profile)


@app.post("/api/v1/clinic-profile/logo")
async def upload_clinic_logo(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    if suffix not in mime:
        raise HTTPException(415, "Clinic logo must be a PNG or JPG image")
    content = await file.read()
    if not content or len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Logo must be between 1 byte and 2 MB")
    valid = ((suffix == ".png" and content[:8] == bytes([137,80,78,71,13,10,26,10])) or
             (suffix in {".jpg", ".jpeg"} and content[:3] == bytes([255,216,255])))
    if not valid:
        raise HTTPException(415, "The logo content does not match its file extension")
    profile = _get_or_create_clinic_profile(db)
    target = DOCUMENT_DIR / ("clinic-logo-" + os.urandom(12).hex() + suffix)
    target.write_bytes(content)
    old_path = profile.logo_path
    profile.logo_path = str(target)
    profile.updated_by = request.state.user.get("sub", "staff")
    profile.updated_at = datetime.now(timezone.utc)
    audit(db, profile.updated_by, "CLINIC_LOGO_UPDATED")
    db.commit()
    if old_path and Path(old_path).name.startswith("clinic-logo-"):
        Path(old_path).unlink(missing_ok=True)
    return {"uploaded": True, "has_logo": True}


@app.get("/api/v1/clinic-profile/logo")
def get_clinic_logo(db: Session = Depends(get_db)):
    profile = _get_or_create_clinic_profile(db)
    if not profile.logo_path or not Path(profile.logo_path).is_file():
        raise HTTPException(404, "No clinic logo has been uploaded")
    suffix = Path(profile.logo_path).suffix.lower()
    return FileResponse(profile.logo_path, media_type="image/png" if suffix == ".png" else "image/jpeg")


@app.get("/api/v1/results/{result_id}/branded-report")
def generate_branded_report(result_id: int, db: Session = Depends(get_db)):
    result = db.get(CBCResult, result_id)
    if not result or result.status != "REVIEWED":
        raise HTTPException(409, "Only reviewed results can be rendered")
    review = db.query(ResultReview).filter_by(result_id=result_id).first()
    if not review:
        raise HTTPException(409, "A recorded review is required before generating the final report")
    if not all([result.patient_name, result.patient_age, result.patient_address]):
        raise HTTPException(422, "Enter the patient name, age and address before generating the final report")

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from xml.sax.saxutils import escape

    profile = _get_or_create_clinic_profile(db)
    try:
        theme = colors.HexColor(profile.theme_color or "#0879D9")
    except Exception:
        theme = colors.HexColor("#0879D9")
    work = Path(tempfile.mkdtemp(prefix="cbc-branded-report-"))
    pdf_path = work / f"CBC-{result.id}-final.pdf"
    phone_text = profile.phone or ""
    if "0775-872-454" not in phone_text or "0751-319-201" not in phone_text:
        phone_text = (phone_text + " | " if phone_text else "") + "0775-872-454, 0751-319-201"
    clinic_name = escape(profile.clinic_name or "Clinic")
    clinic_address = escape(profile.address or "")
    header_text = escape(profile.header_text or "")
    footer_label = profile.footer_text or ""
    if "Powered by ClinicHIS" not in footer_label:
        footer_label = (footer_label + " | " if footer_label else "") + "Powered by ClinicHIS"
    footer_text = escape(footer_label)
    logo_path = profile.logo_path if profile.logo_path and Path(profile.logo_path).is_file() else None

    def draw_page(canvas, document):
        canvas.saveState()
        width, height = A4
        display_mode = profile.logo_display_mode or "header"
        if logo_path and display_mode in {"watermark", "background", "both"}:
            try:
                from reportlab.lib.utils import ImageReader
                canvas.saveState()
                canvas.setFillAlpha(float(profile.logo_opacity or 0.10))
                if display_mode == "background":
                    canvas.drawImage(ImageReader(logo_path), 0, 0, width=width, height=height,
                                     preserveAspectRatio=False, mask="auto")
                else:
                    mark_w, mark_h = 105 * mm, 105 * mm
                    canvas.drawImage(ImageReader(logo_path), (width-mark_w)/2, (height-mark_h)/2,
                                     width=mark_w, height=mark_h, preserveAspectRatio=True,
                                     anchor="c", mask="auto")
                canvas.restoreState()
            except Exception:
                canvas.restoreState()
        canvas.setFillColor(theme)
        canvas.rect(0, height - 7 * mm, width, 7 * mm, fill=1, stroke=0)
        left = 24 * mm
        if logo_path and display_mode in {"header", "both"}:
            try:
                from reportlab.lib.utils import ImageReader
                canvas.drawImage(ImageReader(logo_path), left, height - 31 * mm,
                                 width=22 * mm, height=20 * mm, preserveAspectRatio=True,
                                 anchor="sw", mask="auto")
                left += 27 * mm
            except Exception:
                pass
        canvas.setFillColor(font_ink)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(left, height - 17 * mm, profile.clinic_name or "Clinic")
        canvas.setFont("Helvetica", 8)
        y = height - 22 * mm
        for line in (profile.address or "").splitlines()[:2]:
            canvas.drawString(left, y, line[:130])
            y -= 4 * mm
        if profile.email:
            canvas.drawString(left, y, profile.email[:130])
        if header_text:
            canvas.setFont("Helvetica-Oblique", 8)
            canvas.drawRightString(width - 20 * mm, height - 17 * mm, header_text[:100])
        canvas.setStrokeColor(theme)
        canvas.setLineWidth(1.2)
        canvas.line(20 * mm, height - 36 * mm, width - 20 * mm, height - 36 * mm)
        canvas.setStrokeColor(colors.HexColor("#D8E1EA"))
        canvas.line(20 * mm, 17 * mm, width - 20 * mm, 17 * mm)
        canvas.setFillColor(font_ink)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(20 * mm, 11 * mm, footer_text[:130])
        canvas.drawString(20 * mm, 7 * mm, f"Contact: {phone_text}"[:130])
        canvas.drawRightString(width - 20 * mm, 7 * mm, f"Page {document.page}")
        canvas.restoreState()

    styles = getSampleStyleSheet()
    try:
        font_ink = colors.HexColor(profile.font_color or "#243447")
    except Exception:
        font_ink = colors.HexColor("#243447")
    for style_name in ("BodyText", "Normal", "Title", "Heading1", "Heading2", "Heading3"):
        if style_name in styles:
            styles[style_name].textColor = font_ink
    styles.add(ParagraphStyle(name="ClinicTitle", parent=styles["Title"], textColor=font_ink,
                              fontName="Helvetica-Bold", fontSize=17, alignment=TA_LEFT, spaceAfter=3))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], textColor=font_ink,
                              fontSize=11, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallMuted", parent=styles["BodyText"], textColor=colors.HexColor("#536579"),
                              fontSize=8, leading=11))
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=43*mm, bottomMargin=24*mm, title=f"CBC Report {result.sample_id}",
                            author=profile.clinic_name or "Clinic")
    story = [Paragraph("COMPLETE BLOOD COUNT REPORT", styles["ClinicTitle"]),
             Paragraph("Patient and specimen information", styles["SectionHeading"])]
    patient_rows = [
        [Paragraph("<b>Patient name</b>", styles["BodyText"]), escape(result.patient_name or "Not recorded"),
         Paragraph("<b>Age</b>", styles["BodyText"]), escape(result.patient_age or "Not recorded")],
        [Paragraph("<b>Address</b>", styles["BodyText"]), Paragraph(escape(result.patient_address or "Not recorded"), styles["BodyText"]),
         Paragraph("<b>Patient reference</b>", styles["BodyText"]), escape(result.patient_reference or "—")],
        [Paragraph("<b>Sample ID</b>", styles["BodyText"]), escape(result.sample_id),
         Paragraph("<b>Analyzer</b>", styles["BodyText"]), escape(result.analyzer)],
    ]
    patient_table = Table(patient_rows, colWidths=[28*mm, 57*mm, 30*mm, 55*mm])
    patient_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F4F7FA")),("TEXTCOLOR",(0,0),(-1,-1),font_ink),
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#D8E1EA")),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story.extend([patient_table, Paragraph("Reviewed CBC measurements", styles["SectionHeading"])])
    rows = [[Paragraph("<b>Analyte</b>", styles["BodyText"]), Paragraph("<b>Result</b>", styles["BodyText"]),
             Paragraph("<b>Unit</b>", styles["BodyText"]), Paragraph("<b>Flag</b>", styles["BodyText"]),
             Paragraph("<b>Doctor's comment</b>", styles["BodyText"])]]
    for code, value in review.reviewed_values.items():
        rows.append([escape(str(code)), escape(str(value.get("value", ""))),
                     escape(str(value.get("unit") or "")), escape(str(value.get("flag") or "")),
                     Paragraph(escape(str((review.analyte_comments or {}).get(code, ""))), styles["SmallMuted"])])
    result_table = Table(rows, repeatRows=1, colWidths=[25*mm, 25*mm, 25*mm, 20*mm, 75*mm])
    result_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),theme),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),("TEXTCOLOR",(0,1),(-1,-1),font_ink),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#D8E1EA")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FC")]),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story.extend([result_table, Paragraph("Review information", styles["SectionHeading"]),
        Paragraph(f"<b>Reviewed by:</b> {escape(review.reviewer)} &nbsp;&nbsp; <b>Reviewed:</b> {escape(review.reviewed_at.strftime('%Y-%m-%d %H:%M'))}", styles["BodyText"]),
        Spacer(1, 5), Paragraph(f"<b>Review comments:</b> {escape(review.comments or 'None')}", styles["BodyText"]),
        Spacer(1, 10), Paragraph("CLINICIAN SIGN-OFF", styles["SectionHeading"])])
    if review.signatory_name and review.signatory_credentials:
        from reportlab.platypus import Image as ReportImage
        sign_cells = []
        if review.signatory_signature_path and Path(review.signatory_signature_path).is_file():
            sign_cells.append(ReportImage(review.signatory_signature_path, width=38*mm, height=16*mm, kind="proportional"))
        else:
            sign_cells.append(Paragraph("Signature not on file at review time", styles["SmallMuted"]))
        sign_cells.append(Paragraph(f"<b>{escape(review.signatory_name)}</b><br/>{escape(review.signatory_credentials)}", styles["BodyText"]))
        if review.signatory_stamp_path and Path(review.signatory_stamp_path).is_file():
            sign_cells.append(ReportImage(review.signatory_stamp_path, width=24*mm, height=24*mm, kind="proportional"))
        sign_table = Table([sign_cells], colWidths=[55*mm, 75*mm] + ([35*mm] if len(sign_cells) == 3 else []))
        sign_table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),4),
                                        ("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),6),
                                        ("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        story.append(sign_table)
        story.append(Paragraph("Clinician details and signature image were captured from the authenticated reviewer profile when this review was recorded.", styles["SmallMuted"]))
    else:
        story.append(Paragraph("No clinician signatory profile was captured for this review. A laboratory review record is not, by itself, a signed or authorized clinical release.", styles["SmallMuted"]))
    story.extend([Spacer(1, 12), HRFlowable(width="100%", color=theme, thickness=0.8),
        Paragraph("A displayed signature or stamp image is a visual mark, not a cryptographic digital signature. Verify authorization under the clinic's approved procedures before clinical release.", styles["SmallMuted"])])
    try:
        doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
        actor = "report-service"
        audit(db, actor, "BRANDED_FINAL_REPORT_GENERATED", result_id,
              {"clinic_name": profile.clinic_name, "theme_color": profile.theme_color})
        db.commit()
        return FileResponse(str(pdf_path), media_type="application/pdf",
                            filename=f"CBC-{result.id}-final.pdf",
                            background=BackgroundTask(shutil.rmtree, str(work), ignore_errors=True))
    except Exception as exc:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(500, "Branded PDF generation failed") from exc


@app.get("/api/v1/results/{result_id}/audit")
def result_audit(result_id: int, db: Session = Depends(get_db)):
    if not db.get(CBCResult, result_id):
        raise HTTPException(404, "Result not found")
    return db.query(AuditEvent).filter_by(result_id=result_id).order_by(AuditEvent.created_at.desc()).all()

@app.get("/api/v1/analytes")
def list_analytes(db: Session = Depends(get_db)):
    return db.query(AnalyteConfig).order_by(AnalyteConfig.code).all()

@app.post("/api/v1/analytes", status_code=201)
def save_analyte(payload: AnalyteIn, db: Session = Depends(get_db)):
    item = db.query(AnalyteConfig).filter_by(code=payload.code.upper()).first()
    if item is None:
        item = AnalyteConfig(code=payload.code.upper(), display_name=payload.display_name,
            unit=payload.unit, precision=payload.precision, enabled=payload.enabled)
        db.add(item)
    else:
        item.display_name, item.unit = payload.display_name, payload.unit
        item.precision, item.enabled = payload.precision, payload.enabled
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/v1/users/me/profile")
def get_my_clinician_profile(request: Request, db: Session = Depends(get_db)):
    username = request.state.user.get("sub", "")
    user = db.query(UserAccount).filter_by(username=username, active=True).first()
    if not user:
        raise HTTPException(404, "User account not found")
    if user.role != "CLINICIAN":
        raise HTTPException(403, "Only clinician accounts can configure a report signatory")
    return {"username": user.username, "full_name": user.full_name or "",
            "credentials": user.credentials or "", "has_signature": bool(user.signature_path and Path(user.signature_path).is_file()),
            "has_stamp": bool(user.stamp_path and Path(user.stamp_path).is_file())}


@app.put("/api/v1/users/me/profile")
def update_my_clinician_profile(payload: dict, request: Request, db: Session = Depends(get_db)):
    username = request.state.user.get("sub", "")
    user = db.query(UserAccount).filter_by(username=username, active=True).first()
    if not user or user.role != "CLINICIAN":
        raise HTTPException(403, "Only clinician accounts can configure a report signatory")
    full_name = str(payload.get("full_name", "")).strip()
    credentials = str(payload.get("credentials", "")).strip()
    if not full_name or not credentials or len(full_name) > 200 or len(credentials) > 200:
        raise HTTPException(422, "Provide the clinician's name and professional credentials")
    user.full_name, user.credentials = full_name, credentials
    audit(db, username, "CLINICIAN_SIGNATORY_PROFILE_UPDATED", details={"full_name": full_name, "credentials": credentials})
    db.commit()
    return {"username": user.username, "full_name": user.full_name, "credentials": user.credentials}


async def _save_clinician_mark(request: Request, file: UploadFile, db: Session, field: str):
    username = request.state.user.get("sub", "")
    user = db.query(UserAccount).filter_by(username=username, active=True).first()
    if not user or user.role != "CLINICIAN":
        raise HTTPException(403, "Only clinician accounts can upload report signature or stamp images")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(415, "Only PNG or JPG signature and stamp images are accepted")
    content = await file.read()
    if not content or len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Image must be between 1 byte and 2 MB")
    valid = (suffix == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n")) or (
        suffix in {".jpg", ".jpeg"} and content.startswith(b"\xff\xd8\xff"))
    if not valid:
        raise HTTPException(415, "Image content does not match its file extension")
    target = DOCUMENT_DIR / (f"clinician-{field}-" + os.urandom(12).hex() + suffix)
    target.write_bytes(content)
    setattr(user, field, str(target))
    audit(db, username, "CLINICIAN_" + field.upper() + "_UPLOADED")
    db.commit()
    return {"message": "Clinician image saved", "field": field}


@app.post("/api/v1/users/me/signature")
async def upload_my_signature(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _save_clinician_mark(request, file, db, "signature_path")


@app.post("/api/v1/users/me/stamp")
async def upload_my_stamp(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _save_clinician_mark(request, file, db, "stamp_path")


@app.post("/api/v1/users", status_code=201)
def create_user(payload: dict, request: Request, db: Session = Depends(get_db)):
    actor = getattr(request.state, "user", {})
    if actor.get("role") != "ADMIN":
        raise HTTPException(403, "Administrator role required")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "TECHNICIAN")).upper()
    if not username or role not in {"TECHNICIAN","SUPERVISOR","ADMIN","CLINICIAN"}:
        raise HTTPException(422, "Provide a username and a valid role")
    if len(password) < 12:
        raise HTTPException(422, "Password must be at least 12 characters")
    if db.query(UserAccount).filter_by(username=username).first():
        raise HTTPException(409, "Username already exists")
    item = UserAccount(username=username, password_hash=hash_password(password), role=role, active=True)
    db.add(item)
    audit(db, actor.get("sub", "admin"), "USER_CREATED", details={"username":username,"role":role})
    db.commit()
    return {"username":username,"role":role}

@app.get("/api/v1/templates")
def list_templates(db: Session = Depends(get_db)):
    rows = db.query(ReportTemplate).order_by(ReportTemplate.uploaded_at.desc()).all()
    return [{"id":r.id,"name":r.name,"filename":r.filename,"uploaded_by":r.uploaded_by,"uploaded_at":r.uploaded_at} for r in rows]

@app.post("/api/v1/templates/generate-sample", status_code=201)
def generate_sample_template(request: Request, db: Session = Depends(get_db)):
    """Create a starter DOCX template only when the clinic has no DOCX template."""
    existing = db.query(ReportTemplate).filter(ReportTemplate.filename.ilike("%.docx")).order_by(
        ReportTemplate.uploaded_at.desc()).first()
    if existing and Path(existing.storage_path).is_file():
        return {"created": False, "message": "A DOCX report template already exists.",
                "template": {"id": existing.id, "name": existing.name,
                             "filename": existing.filename, "uploaded_at": existing.uploaded_at}}

    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin =  Inches(0.65)
    doc.add_heading("CBC Connect", 0)
    doc.add_heading("Complete Blood Count Report", level=1)
    doc.add_paragraph("Clinic: {{ clinic_name }}")
    info = doc.add_table(rows=0, cols=2)
    info.style = "Table Grid"
    for label, placeholder in [
        ("Sample / accession ID", "{{ sample_id }}"),
        ("Patient reference", "{{ patient_reference }}"),
        ("Analyzer", "{{ analyzer }}"),
        ("Received", "{{ received_at }}"),
        ("Reviewed by", "{{ reviewer }}"),
        ("Reviewed at", "{{ reviewed_at }}"),
    ]:
        cells = info.add_row().cells
        cells[0].text, cells[1].text = label, placeholder
    doc.add_paragraph("")
    doc.add_heading("CBC Measurements", level=2)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for cell, label in zip(table.rows[0].cells, ["Analyte", "Result", "Unit", "Flag"]):
        cell.text = label
    start = table.add_row()
    start.cells[0].text = "{%tr for item in results %}"
    data = table.add_row()
    for cell, value in zip(data.cells, ["{{ item.code }}", "{{ item.value }}", "{{ item.unit }}", "{{ item.flag }}"]):
        cell.text = value
    end = table.add_row()
    end.cells[0].text = "{%tr endfor %}"
    doc.add_paragraph("Review comments: {{ comments }}")
    doc.add_paragraph("This report is generated from reviewed values. Follow the clinic's approved authorization and release procedure.")
    filename = "cbc-connect-sample-report.docx"
    target = TEMPLATE_DIR / f"{os.urandom(12).hex()}.docx"
    doc.save(target)
    actor = request.state.user.get("sub", "staff")
    item = ReportTemplate(name="CBC Connect Sample Report", filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        storage_path=str(target), uploaded_by=actor)
    db.add(item)
    audit(db, actor, "SAMPLE_REPORT_TEMPLATE_GENERATED",
          details={"name": item.name, "filename": filename})
    db.commit()
    db.refresh(item)
    return {"created": True, "message": "Starter DOCX template generated. Download and customize it for your clinic.",
            "template": {"id": item.id, "name": item.name, "filename": item.filename,
                         "uploaded_at": item.uploaded_at}}


@app.get("/api/v1/templates/{template_id}/download")
def download_template(template_id: int, db: Session = Depends(get_db)):
    item = db.get(ReportTemplate, template_id)
    if not item:
        raise HTTPException(404, "Template not found")
    path = Path(item.storage_path)
    if not path.is_file():
        raise HTTPException(404, "Template file is unavailable")
    media_type = item.content_type or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=item.filename)


@app.post("/api/v1/templates", status_code=201)
async def upload_template(request: Request, name: str = Form(...), uploaded_by: str = Form(...),
                          file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".docx", ".pdf"}:
        raise HTTPException(415, "Only DOCX and PDF templates are accepted")
    content = await file.read()
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Template must be between 1 byte and 10 MB")
    safe_name = f"{os.urandom(12).hex()}{suffix}"
    target = TEMPLATE_DIR / safe_name
    target.write_bytes(content)
    item = ReportTemplate(name=name, filename=file.filename or safe_name,
        content_type=file.content_type or "application/octet-stream",
        storage_path=str(target), uploaded_by=request.state.user.get("sub", "staff"))
    db.add(item)
    audit(db, request.state.user.get("sub", "staff"), "REPORT_TEMPLATE_UPLOADED", details={"name": name, "filename": file.filename})
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "filename": item.filename, "uploaded_at": item.uploaded_at}


@app.get("/api/v1/results/{result_id}/report")
def generate_report(result_id: int, template_id: int, db: Session = Depends(get_db)):
    result = db.get(CBCResult, result_id)
    if not result or result.status != "REVIEWED":
        raise HTTPException(409, "Only reviewed results can be rendered")
    review = db.query(ResultReview).filter_by(result_id=result_id).first()
    template = db.get(ReportTemplate, template_id)
    if not review or not template or not template.filename.lower().endswith(".docx"):
        raise HTTPException(422, "A reviewed result and DOCX template are required")
    if not all([result.patient_name, result.patient_age, result.patient_address]):
        raise HTTPException(422, "Enter the patient name, age and address before generating the final report")
    if not Path(template.storage_path).is_file():
        raise HTTPException(404, "Template file is unavailable")
    work = Path(tempfile.mkdtemp(prefix="cbc-report-"))
    try:
        doc = DocxTemplate(template.storage_path)
        profile = _get_or_create_clinic_profile(db)
        context = {"sample_id":result.sample_id,"patient_reference":result.patient_reference or "",
            "patient_name":result.patient_name or "Not recorded","patient_age":result.patient_age or "Not recorded",
            "patient_address":result.patient_address or "Not recorded",
            "clinic_name":profile.clinic_name,"clinic_address":profile.address,"clinic_phone":profile.phone,
            "clinic_email":profile.email,"header_text":profile.header_text,"footer_text":profile.footer_text,
            "analyzer":result.analyzer,"reviewer":review.reviewer,"signatory_name":review.signatory_name or "Not recorded","signatory_credentials":review.signatory_credentials or "","comments":review.comments or "",
            "received_at":result.received_at.isoformat(),"reviewed_at":review.reviewed_at.isoformat(),
            "results":[{"code":k,"value":v.get("value"),"unit":v.get("unit") or "",
                       "flag":v.get("flag") or ""} for k,v in review.reviewed_values.items()]}
        doc.render(context)
        docx_path = work / f"CBC-{result.id}.docx"
        doc.save(docx_path)

        # Apply the saved clinic identity to every DOCX-template report, even when
        # the uploaded template does not contain explicit branding placeholders.
        branded_doc = Document(docx_path)
        from docx.shared import RGBColor, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        try:
            rgb = tuple(int(profile.theme_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            rgb = (8, 121, 217)
        try:
            font_rgb = tuple(int(profile.font_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            font_rgb = (36, 52, 71)
        for paragraph in branded_doc.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(*font_rgb)
        for existing_table in branded_doc.tables:
            for existing_row in existing_table.rows:
                for cell in existing_row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = RGBColor(*font_rgb)
        for section in branded_doc.sections:
            header = section.header
            header.is_linked_to_previous = False
            hp = header.paragraphs[0]
            hp.clear()
            if profile.logo_path and Path(profile.logo_path).is_file():
                try:
                    hp.add_run().add_picture(profile.logo_path, width=Inches(0.55))
                    hp.add_run("   ")
                except Exception:
                    pass
            clinic_run = hp.add_run(profile.clinic_name or "Clinic")
            clinic_run.bold = True
            clinic_run.font.size = Pt(12)
            clinic_run.font.color.rgb = RGBColor(*font_rgb)
            address_text = " | ".join(x for x in [profile.address, profile.email] if x)
            if address_text:
                address_run = hp.add_run("\n" + address_text)
                address_run.font.size = Pt(8)
                address_run.font.color.rgb = RGBColor(*font_rgb)
            if profile.header_text:
                extra = hp.add_run("\n" + profile.header_text)
                extra.font.size = Pt(8)
            footer = section.footer
            footer.is_linked_to_previous = False
            fp = footer.paragraphs[0]
            fp.clear()
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            footer_label = profile.footer_text or ""
            if "Powered by ClinicHIS" not in footer_label:
                footer_label = (footer_label + " | " if footer_label else "") + "Powered by ClinicHIS"
            contacts = profile.phone or ""
            if "0775-872-454" not in contacts or "0751-319-201" not in contacts:
                contacts = (contacts + " | " if contacts else "") + "0775-872-454, 0751-319-201"
            footer_run = fp.add_run(f"{footer_label} | {contacts}")
            footer_run.font.size = Pt(8)
            footer_run.font.color.rgb = RGBColor(*font_rgb)

        # Patient identity is inserted automatically, independently of template placeholders.
        patient_table = branded_doc.add_table(rows=5, cols=2)
        patient_table.style = "Table Grid"
        patient_rows = [("Patient name", result.patient_name or "Not recorded"),
                        ("Age", result.patient_age or "Not recorded"),
                        ("Address", result.patient_address or "Not recorded"),
                        ("Patient reference", result.patient_reference or "Not recorded"),
                        ("Sample / accession ID", result.sample_id)]
        for row, (label, value) in zip(patient_table.rows, patient_rows):
            row.cells[0].text = label
            row.cells[1].text = value
            for run in row.cells[1].paragraphs[0].runs:
                run.font.color.rgb = RGBColor(*font_rgb)
            shade = OxmlElement("w:shd")
            shade.set(qn("w:fill"), profile.theme_color.lstrip("#").upper() if profile.theme_color else "0879D9")
            row.cells[0]._tc.get_or_add_tcPr().append(shade)
            for run in row.cells[0].paragraphs[0].runs:
                run.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
        if branded_doc.paragraphs:
            branded_doc.paragraphs[0]._p.addnext(patient_table._tbl)
        sign_heading = branded_doc.add_paragraph()
        sign_heading.add_run("CLINICIAN SIGN-OFF").bold = True
        sign_heading.runs[0].font.color.rgb = RGBColor(*font_rgb)
        if review.signatory_name and review.signatory_credentials:
            sign_table = branded_doc.add_table(rows=1, cols=3)
            sign_table.style = "Table Grid"
            signature_cell, name_cell, stamp_cell = sign_table.rows[0].cells
            if review.signatory_signature_path and Path(review.signatory_signature_path).is_file():
                signature_cell.paragraphs[0].add_run().add_picture(review.signatory_signature_path, width=Inches(1.35))
            else:
                signature_cell.text = "Signature not on file"
            name_cell.text = (review.signatory_name or "") + "\n" + (review.signatory_credentials or "")
            if review.signatory_stamp_path and Path(review.signatory_stamp_path).is_file():
                stamp_cell.paragraphs[0].add_run().add_picture(review.signatory_stamp_path, width=Inches(0.8))
            for row in sign_table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = RGBColor(*font_rgb)
        else:
            note = branded_doc.add_paragraph("No clinician signatory profile was captured when this review was recorded.")
            for run in note.runs:
                run.font.color.rgb = RGBColor(*font_rgb)
        # Apply the selected clinic font consistently to all generated DOCX text,
        # including template content, inserted patient details, tables and sign-off.
        selected_font = profile.font_family or "Arial"
        from docx.oxml.ns import qn as font_qn
        for style in branded_doc.styles:
            try:
                style.font.name = selected_font
                style._element.rPr.rFonts.set(font_qn("w:eastAsia"), selected_font)
            except Exception:
                pass
        def apply_font_family(paragraphs):
            for paragraph in paragraphs:
                for run in paragraph.runs:
                    run.font.name = selected_font
                    run._element.get_or_add_rPr().rFonts.set(font_qn("w:eastAsia"), selected_font)
        apply_font_family(branded_doc.paragraphs)
        for table in branded_doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    apply_font_family(cell.paragraphs)
        for section in branded_doc.sections:
            apply_font_family(section.header.paragraphs)
            apply_font_family(section.footer.paragraphs)
            for table in list(section.header.tables) + list(section.footer.tables):
                for row in table.rows:
                    for cell in row.cells:
                        apply_font_family(cell.paragraphs)
        branded_doc.save(docx_path)
        completed = subprocess.run(["libreoffice","--headless","--convert-to","pdf","--outdir",str(work),str(docx_path)],
                                   capture_output=True, timeout=60)
        pdf_path = work / f"CBC-{result.id}.pdf"
        if completed.returncode != 0 or not pdf_path.exists():
            raise HTTPException(500, "PDF conversion failed")
        if profile.logo_path and Path(profile.logo_path).is_file() and profile.logo_display_mode in {"watermark", "background", "both"}:
            from io import BytesIO
            from reportlab.pdfgen import canvas as pdf_canvas
            from reportlab.lib.utils import ImageReader
            from pypdf import PdfReader, PdfWriter
            source_pdf = PdfReader(str(pdf_path))
            writer = PdfWriter()
            for page in source_pdf.pages:
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                overlay_buffer = BytesIO()
                overlay_canvas = pdf_canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
                overlay_canvas.saveState()
                overlay_canvas.setFillAlpha(float(profile.logo_opacity or 0.10))
                if profile.logo_display_mode == "background":
                    overlay_canvas.drawImage(ImageReader(profile.logo_path), 0, 0, width=page_width,
                                             height=page_height, preserveAspectRatio=False, mask="auto")
                else:
                    mark_w = min(page_width * 0.52, 300)
                    mark_h = min(page_height * 0.52, 300)
                    overlay_canvas.drawImage(ImageReader(profile.logo_path), (page_width-mark_w)/2,
                                             (page_height-mark_h)/2, width=mark_w, height=mark_h,
                                             preserveAspectRatio=True, anchor="c", mask="auto")
                overlay_canvas.restoreState()
                overlay_canvas.save()
                overlay_buffer.seek(0)
                page.merge_page(PdfReader(overlay_buffer).pages[0], over=False)
                writer.add_page(page)
            with pdf_path.open("wb") as output:
                writer.write(output)
        audit(db, "report-service", "REPORT_GENERATED", result_id, {"template_id":template_id})
        db.commit()
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"CBC-{result.id}.pdf",
                            background=BackgroundTask(shutil.rmtree, work, ignore_errors=True))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Report generation failed") from exc


@app.get("/api/v1/reference-intervals")
def list_reference_intervals(db: Session = Depends(get_db)):
    return db.query(ReferenceInterval).order_by(ReferenceInterval.analyte_code, ReferenceInterval.population).all()

@app.post("/api/v1/reference-intervals", status_code=201)
def add_reference_interval(payload: dict, request: Request, db: Session = Depends(get_db)):
    actor = request.state.user.get("sub", "staff")
    code = str(payload.get("analyte_code", "")).strip().upper()
    source = str(payload.get("source", "")).strip()
    population = str(payload.get("population", "")).strip()
    unit = str(payload.get("unit", "")).strip()
    lower, upper = payload.get("lower_value"), payload.get("upper_value")
    if not all([code, source, population, unit]) or lower is None or upper is None:
        raise HTTPException(422, "Provide analyte, population, source and unit")
    if not math.isfinite(float(lower)) or not math.isfinite(float(upper)) or float(lower) > float(upper):
        raise HTTPException(422, "Reference interval bounds must be finite and lower must not exceed upper")
    age_min, age_max = payload.get("age_min_days"), payload.get("age_max_days")
    if age_min is not None and age_max is not None and int(age_min) > int(age_max):
        raise HTTPException(422, "Minimum age must not exceed maximum age")
    item = ReferenceInterval(analyte_code=code, population=population,
        age_min_days=payload.get("age_min_days"), age_max_days=payload.get("age_max_days"),
        sex=str(payload.get("sex", "ALL")).upper(), lower_value=float(lower), upper_value=float(upper),
        unit=unit, source=source, created_by=actor, status="DRAFT")
    db.add(item)
    audit(db, actor, "REFERENCE_INTERVAL_DRAFTED", details={"analyte_code":code,"source":source})
    db.commit()
    db.refresh(item)
    return item

@app.post("/api/v1/reference-intervals/{interval_id}/verify")
def verify_reference_interval(interval_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    actor = request.state.user.get("sub", "staff")
    if request.state.user.get("role") not in {"SUPERVISOR","ADMIN"}:
        raise HTTPException(403, "Supervisor or administrator role required")
    item = db.get(ReferenceInterval, interval_id)
    if not item:
        raise HTTPException(404, "Reference interval not found")
    if item.created_by == actor:
        raise HTTPException(409, "A different authorized reviewer must verify this interval")
    if not str(payload.get("evidence", "")).strip():
        raise HTTPException(422, "Document the verification evidence")
    item.status = "VERIFIED"
    item.verified_by = actor
    item.verified_at = datetime.now(timezone.utc)
    audit(db, actor, "REFERENCE_INTERVAL_VERIFIED", details={"interval_id":interval_id,"evidence":payload["evidence"]})
    db.commit()
    return {"id":item.id,"status":item.status,"verified_by":actor,"verified_at":item.verified_at,
            "note":"Verification is a local laboratory governance action, not automated clinical validation."}
