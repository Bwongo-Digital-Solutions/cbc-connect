from datetime import datetime, timezone
import os
import math
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import Base, engine, get_db
from .models import CBCResult, ResultReview, AuditEvent, AnalyteConfig, ReportTemplate, UserAccount, ReferenceInterval
from .schemas import AnalyzerPayload, ResultOut, ManualSample, ReviewIn, AnalyteIn
from .security import authenticate, create_access_token, hash_password, decode_access_token
from fastapi import Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from docxtpl import DocxTemplate
import subprocess, tempfile, shutil

app = FastAPI(title="CBC Connect API", version="0.2.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "Authorization", "X-Device-Id", "X-Analyzer-Key"])
TEMPLATE_DIR = Path(os.getenv("TEMPLATE_DIR", "./data/templates"))
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

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
    if path.endswith("/review") and role not in {"TECHNICIAN","SUPERVISOR","ADMIN"}:
        return JSONResponse(status_code=403, content={"detail":"Insufficient role"})
    if (request.method != "GET" and ("/analytes" in path or "/templates" in path) and role not in {"SUPERVISOR","ADMIN"}:
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
    return {"result": ResultOut.model_validate(result), "review": review, "audit": events}

@app.post("/api/v1/samples", response_model=ResultOut, status_code=201)
def create_sample(payload: ManualSample, request: Request, db: Session = Depends(get_db)):
    result = CBCResult(sample_id=payload.sample_id, patient_reference=payload.patient_reference,
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
def ingest(payload: AnalyzerPayload, x_device_id: str = Header(default="unregistered-device"),
           db: Session = Depends(get_db)):
    existing = db.query(CBCResult).filter_by(sample_id=payload.sample_id, device_id=x_device_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="A result for this sample and device already exists")
    result = db.query(CBCResult).filter_by(sample_id=payload.sample_id, device_id="manual-entry", analyzer="MANUAL").first()
    values = {key: measurement.model_dump() for key, measurement in payload.values.items()}
    if result:
        result.patient_reference = payload.patient_reference or result.patient_reference
        result.analyzer = payload.analyzer
        result.device_id = x_device_id
        result.observed_at = payload.observed_at
        result.values = values
        audit(db, "analyzer:" + x_device_id, "RESULT_ATTACHED_TO_REGISTERED_SAMPLE", result.id,
              {"analyzer": payload.analyzer, "sample_id": payload.sample_id})
    else:
        result = CBCResult(sample_id=payload.sample_id, patient_reference=payload.patient_reference,
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
    review = ResultReview(result_id=result_id, reviewer=reviewer_identity,
                          comments=payload.comments, reviewed_values=corrected)
    db.add(review)
    result.status = "REVIEWED"
    audit(db, reviewer_identity, "RESULT_REVIEWED", result_id,
          {"comments": payload.comments, "corrections_made": corrected != result.values})
    db.commit()
    return {"message": "Review recorded", "status": result.status, "reviewed_at": review.reviewed_at}

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

@app.post("/api/v1/users", status_code=201)
def create_user(payload: dict, request: Request, db: Session = Depends(get_db)):
    actor = getattr(request.state, "user", {})
    if actor.get("role") != "ADMIN":
        raise HTTPException(403, "Administrator role required")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "TECHNICIAN")).upper()
    if not username or role not in {"TECHNICIAN","SUPERVISOR","ADMIN"}:
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
    if not Path(template.storage_path).is_file():
        raise HTTPException(404, "Template file is unavailable")
    work = Path(tempfile.mkdtemp(prefix="cbc-report-"))
    try:
        doc = DocxTemplate(template.storage_path)
        context = {"sample_id":result.sample_id,"patient_reference":result.patient_reference or "",
            "analyzer":result.analyzer,"reviewer":review.reviewer,"comments":review.comments or "",
            "received_at":result.received_at.isoformat(),"reviewed_at":review.reviewed_at.isoformat(),
            "results":[{"code":k,"value":v.get("value"),"unit":v.get("unit") or "",
                       "flag":v.get("flag") or ""} for k,v in review.reviewed_values.items()]}
        doc.render(context)
        docx_path = work / f"CBC-{result.id}.docx"
        doc.save(docx_path)
        completed = subprocess.run(["libreoffice","--headless","--convert-to","pdf","--outdir",str(work),str(docx_path)],
                                   capture_output=True, timeout=60)
        pdf_path = work / f"CBC-{result.id}.pdf"
        if completed.returncode != 0 or not pdf_path.exists():
            raise HTTPException(500, "PDF conversion failed")
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
