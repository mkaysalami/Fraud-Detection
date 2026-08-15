"""
RuleEngine: runs every registered Rule against a transaction and builds
Alert records for any that fire.
"""
from typing import List

from sqlalchemy.orm import Session

from app.models import Alert, Transaction
from app.rules.base import Rule
from app.rules.full_account_drain import FullAccountDrainRule
from app.rules.dest_balance_glitch import DestBalanceGlitchRule
from app.rules.large_amount import LargeAmountRule
from app.rules.round_amount import RoundAmountRule


class RuleEngine:
    def __init__(self, rules: List[Rule] = None):
        # Ordered roughly by strength (strongest signal first) -- doesn't
        # affect correctness since every rule runs regardless, but makes
        # alert lists read in a sensible priority order.
        self.rules: List[Rule] = rules or [
            FullAccountDrainRule(),
            DestBalanceGlitchRule(),
            LargeAmountRule(),
            RoundAmountRule(),
        ]

    def evaluate(self, transaction: Transaction, db: Session = None) -> List[Alert]:
        """Run all rules against a transaction, persist and return any alerts."""
        alerts: List[Alert] = []

        for rule in self.rules:
            result = rule.evaluate(transaction)
            if result is not None:
                alert = Alert(
                    transaction_id=transaction.id,
                    rule_name=result.rule_name,
                    severity=result.severity,
                    reason=result.reason,
                )
                alerts.append(alert)
                if db is not None:
                    db.add(alert)

        if db is not None and alerts:
            db.commit()
            for alert in alerts:
                db.refresh(alert)

        return alerts
