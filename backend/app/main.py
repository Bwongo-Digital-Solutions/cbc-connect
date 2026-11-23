import os
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import Base, engine, get_db
from .models import CBCResult
from .schemas import AnalyzerPayload, ResultOut

Base.metadata.create_all(bind=engine)
app = FastAPI(title="CBC Connect API", version="0.1.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "X-Device-Id"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "cbc-connect-api"}

@app.get("/api/v1/results", response_model=list[ResultOut])
def list_results(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(CBCResult).order_by(CBCResult.received_at.desc())
    if status:
        query = query.filter(CBCResult.status == status.upper())
    return query.limit(200).all()

@app.post("/api/v1/analyzer/ingest", response_model=ResultOut, status_code=201)
def ingest(payload: AnalyzerPayload, x_device_id: str = Header(default="unregistered-device"),
           db: Session = Depends(get_db)):
    result = CBCResult(sample_id=payload.sample_id, patient_reference=payload.patient_reference,
        analyzer=payload.analyzer, device_id=x_device_id, observed_at=payload.observed_at,
        status="PENDING_REVIEW",
        values={key: measurement.model_dump() for key, measurement in payload.values.items()})
    db.add(result)
    try:
        db.commit()
        db.refresh(result)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A result for this sample and device already exists")
    return result
