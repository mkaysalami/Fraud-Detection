from typing import Optional

from app.models import Transaction
from app.rules.base import Rule, RuleResult


class DestBalanceGlitchRule(Rule):
    """
    Flags a transaction where the destination account's balance is
    reported as zero both before AND after receiving a nonzero amount --
    i.e. oldbalanceDest == 0 and newbalanceDest == 0 despite amount > 0.

    Validated against the real PaySim dataset (TRANSFER/CASH_OUT only):
        precision: 70.46%
        recall:    49.56%

    Intuition: a legitimate transfer updates the recipient's balance. Money
    mule / drop accounts used in fraud schemes are often not tracked
    properly by the system generating this data, so their balance fields
    stay at zero even as money passes through -- a bookkeeping tell rather
    than a behavioral one, but a real and useful one.

    Complements FullAccountDrainRule: on its own it only catches about half
    of fraud cases, but running both together pushes combined recall to
    99.6% (see scripts/evaluate_on_dataset.py).
    """

    name = "DEST_BALANCE_GLITCH"

    def evaluate(self, transaction: Transaction) -> Optional[RuleResult]:
        if transaction.type not in self.applicable_types:
            return None

        if (
            transaction.oldbalance_dest == 0
            and transaction.newbalance_dest == 0
            and transaction.amount > 0
        ):
            return RuleResult(
                rule_name=self.name,
                severity="MEDIUM",
                reason=(
                    f"Destination account balance shows 0.00 both before and "
                    f"after receiving {transaction.amount:,.2f} -- balance not "
                    f"tracked, a common mule-account signature."
                ),
            )
        return None
