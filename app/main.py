"""
FastAPI application.

Endpoints:
  POST /transactions             submit a transaction (runs the rule engine)
  GET  /transactions             list transactions
  GET  /alerts                   list alerts (filterable by severity/rule)
  GET  /alerts/{alert_id}        get a single alert with its transaction
  GET  /stats                    summary counts (transactions, alerts by rule)
"""
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import Base, engine, get_db
from app.engine import RuleEngine
from app.models import Transaction, Alert
from app import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Transaction Monitoring & Fraud Alert System",
    description=(
        "Rule-based fraud detection calibrated against the real PaySim "
        "mobile-money dataset (6.3M transactions, 8,213 confirmed fraud cases)."
    ),
    version="2.0.0",
)

rule_engine = RuleEngine()


@app.post("/transactions", response_model=schemas.TransactionResult, status_code=201)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    valid_types = {"PAYMENT", "CASH_IN", "CASH_OUT", "TRANSFER", "DEBIT"}
    if payload.type not in valid_types:
        raise HTTPException(400, f"type must be one of {sorted(valid_types)}")

    txn = Transaction(**payload.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)

    rule_engine.evaluate(txn, db)
    db.refresh(txn)

    flagged = any(a.severity in ("HIGH", "MEDIUM") for a in txn.alerts)

    return schemas.TransactionResult(
        transaction=txn, alerts=txn.alerts, flagged_for_review=flagged
    )


@app.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/alerts", response_model=list[schemas.AlertOut])
def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: LOW/MEDIUM/HIGH"),
    rule_name: Optional[str] = Query(None, description="Filter by rule name"),
    db: Session = Depends(get_db),
):
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if rule_name:
        query = query.filter(Alert.rule_name == rule_name.upper())
    return query.order_by(Alert.created_at.desc()).all()


@app.get("/alerts/{alert_id}", response_model=schemas.AlertOut)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found.")
    return alert


@app.get("/stats")
def stats(db: Session = Depends(get_db)):
    total_txns = db.query(func.count(Transaction.id)).scalar()
    total_alerts = db.query(func.count(Alert.id)).scalar()
    by_rule = dict(
        db.query(Alert.rule_name, func.count(Alert.id)).group_by(Alert.rule_name).all()
    )
    return {
        "total_transactions": total_txns,
        "total_alerts": total_alerts,
        "alerts_by_rule": by_rule,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
