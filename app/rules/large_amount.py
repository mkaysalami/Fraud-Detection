from typing import Optional

from app.models import Transaction
from app.rules.base import Rule, RuleResult


class LargeAmountRule(Rule):
    """
    Flags transactions at or above the 99th percentile of TRANSFER/CASH_OUT
    amounts in the real dataset (~2,650,000).

    Deliberately LOW severity: EDA showed this is a WEAK signal on its own.

        p90  (544,868):  precision  1.34%, recall 45.34%
        p95  (954,997):  precision  2.02%, recall 34.13%
        p99  (2,650,036): precision  4.75%, recall 16.04%
        p99.5(4,271,521): precision  6.19%, recall 10.45%

    Fraud and legitimate amounts overlap heavily in this dataset -- fraud
    amounts run higher on average, but "large" alone is nowhere near
    sufficient to distinguish them. Kept as a low-confidence supporting
    signal (useful for analyst triage/ranking) rather than a primary
    detector -- unlike FullAccountDrainRule, this should never be the sole
    basis for an alert in a real system.
    """

    name = "LARGE_AMOUNT"

    def __init__(self, threshold: float = 2_650_000.0):
        self.threshold = threshold

    def evaluate(self, transaction: Transaction) -> Optional[RuleResult]:
        if transaction.type not in self.applicable_types:
            return None

        if transaction.amount >= self.threshold:
            return RuleResult(
                rule_name=self.name,
                severity="LOW",
                reason=(
                    f"Amount {transaction.amount:,.2f} is in the top 1% of "
                    f"TRANSFER/CASH_OUT amounts (weak signal alone, ~5% precision)."
                ),
            )
        return None
