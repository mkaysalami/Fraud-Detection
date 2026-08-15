from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TransactionCreate(BaseModel):
    type: str  # PAYMENT | CASH_IN | CASH_OUT | TRANSFER | DEBIT
    amount: float
    name_orig: str
    oldbalance_org: float
    newbalance_orig: float
    name_dest: str
    oldbalance_dest: float
    newbalance_dest: float
    step: Optional[int] = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_name: str
    severity: str
    reason: str
    created_at: datetime


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    step: Optional[int]
    type: str
    amount: float
    name_orig: str
    oldbalance_org: float
    newbalance_orig: float
    name_dest: str
    oldbalance_dest: float
    newbalance_dest: float
    created_at: datetime


class TransactionResult(BaseModel):
    """Returned right after submitting a transaction: the txn + any alerts it triggered."""
    transaction: TransactionOut
    alerts: list[AlertOut]
    flagged_for_review: bool
    # True if any HIGH/MEDIUM severity alert fired. Full-dataset evaluation
    # showed that including LOW-severity signals (LARGE_AMOUNT, ROUND_AMOUNT)
    # in this determination drops precision from 82.7% to 22.5% while adding
    # 0 percentage points of recall -- so this flag deliberately only
    # considers HIGH/MEDIUM alerts. LOW alerts still ride along in `alerts`
    # as informational context for an analyst, they just don't drive the
    # flag on their own. See README "Data & methodology".
