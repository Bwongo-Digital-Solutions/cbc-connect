import os
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import Base, engine, get_db
from .models import CBCResult, ResultReview, AuditEvent, AnalyteConfig, ReportTemplate
from .schemas import AnalyzerPayload, ResultOut, ManualSample, ReviewIn, AnalyteIn

Base.metadata.create_all(bind=engine)
app = FastAPI(title="CBC Connect API", version="0.2.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "X-Device-Id"])
TEMPLATE_DIR = Path(os.getenv("TEMPLATE_DIR", "/data/templates"))
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

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
def create_sample(payload: ManualSample, db: Session = Depends(get_db)):
    result = CBCResult(sample_id=payload.sample_id, patient_reference=payload.patient_reference,
        analyzer="MANUAL", device_id="manual-entry", observed_at=payload.collected_at,
        status="PENDING_REVIEW", values={})
    db.add(result)
    try:
        db.flush()
        audit(db, "sample-registration", "SAMPLE_REGISTERED", result.id,
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
    result = CBCResult(sample_id=payload.sample_id, patient_reference=payload.patient_reference,
        analyzer=payload.analyzer, device_id=x_device_id, observed_at=payload.observed_at,
        status="PENDING_REVIEW",
        values={key: measurement.model_dump() for key, measurement in payload.values.items()})
    db.add(result)
    try:
        db.flush()
        audit(db, "analyzer:" + x_device_id, "RESULT_RECEIVED", result.id,
              {"analyzer": payload.analyzer, "sample_id": payload.sample_id})
        db.commit()
        db.refresh(result)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A result for this sample and device already exists")
    return result

@app.post("/api/v1/results/{result_id}/review")
def review_result(result_id: int, payload: ReviewIn, db: Session = Depends(get_db)):
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
    review = ResultReview(result_id=result_id, reviewer=payload.reviewer,
                          comments=payload.comments, reviewed_values=corrected)
    db.add(review)
    result.status = "REVIEWED"
    audit(db, payload.reviewer, "RESULT_REVIEWED", result_id,
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

@app.get("/api/v1/templates")
def list_templates(db: Session = Depends(get_db)):
    return db.query(ReportTemplate).order_by(ReportTemplate.uploaded_at.desc()).all()

@app.post("/api/v1/templates", status_code=201)
async def upload_template(name: str = Form(...), uploaded_by: str = Form(...),
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
        storage_path=str(target), uploaded_by=uploaded_by)
    db.add(item)
    audit(db, uploaded_by, "REPORT_TEMPLATE_UPLOADED", details={"name": name, "filename": file.filename})
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "filename": item.filename, "uploaded_at": item.uploaded_at}
