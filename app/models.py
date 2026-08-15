"""
Database models.

Transaction fields mirror the real PaySim mobile-money dataset schema
(step, type, amount, orig/dest balances) rather than an invented schema,
since the detection rules are calibrated directly against that data.
See README.md "Data & methodology" for the EDA that drove this design.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    step = Column(Integer, nullable=True)  # simulation hour, 1-744; optional for live-submitted txns
    type = Column(String, nullable=False)  # PAYMENT | CASH_IN | CASH_OUT | TRANSFER | DEBIT

    amount = Column(Float, nullable=False)

    name_orig = Column(String, index=True, nullable=False)
    oldbalance_org = Column(Float, nullable=False)
    newbalance_orig = Column(Float, nullable=False)

    name_dest = Column(String, index=True, nullable=False)
    oldbalance_dest = Column(Float, nullable=False)
    newbalance_dest = Column(Float, nullable=False)

    # Ground truth label, only populated when replaying labeled historical
    # data (e.g. via the evaluation script). NULL for live-submitted txns
    # where we don't know the answer yet -- that's the whole point.
    is_fraud_actual = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    alerts = relationship("Alert", back_populates="transaction")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    rule_name = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # LOW / MEDIUM / HIGH
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transaction = relationship("Transaction", back_populates="alerts")
