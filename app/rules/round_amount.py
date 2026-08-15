from typing import Optional

from app.models import Transaction
from app.rules.base import Rule, RuleResult


class RoundAmountRule(Rule):
    """
    Flags amounts that are exact multiples of 1,000.

    Validated against real data (TRANSFER/CASH_OUT):
        fraud rate among round amounts:     8.77%
        fraud rate among non-round amounts: 0.29%

    A ~30x lift -- real, but still a LOW severity supporting signal, not a
    primary detector (92% of round-amount transactions are still legit).
    """

    name = "ROUND_AMOUNT"

    def __init__(self, multiple_of: float = 1000.0):
        self.multiple_of = multiple_of

    def evaluate(self, transaction: Transaction) -> Optional[RuleResult]:
        if transaction.type not in self.applicable_types:
            return None
        if transaction.amount <= 0:
            return None

        if transaction.amount % self.multiple_of == 0:
            return RuleResult(
                rule_name=self.name,
                severity="LOW",
                reason=(
                    f"Amount {transaction.amount:,.2f} is an exact multiple of "
                    f"{self.multiple_of:,.0f} (~30x higher fraud rate than "
                    f"irregular amounts in validation data)."
                ),
            )
        return None
