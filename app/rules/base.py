"""
Base class for all fraud-detection rules.

Design pattern: Strategy pattern. Each concrete rule encapsulates one
detection heuristic behind a common interface (`evaluate`), so RuleEngine
can run an extensible list of rules over a transaction without knowing how
each one works internally.

Note on `evaluate`'s signature: an earlier version of this project passed
a database session into every rule, anticipating "history-based" rules
(e.g. flagging rapid-fire transactions from the same account). EDA against
the real PaySim dataset showed that pattern isn't actually present here --
99.94% of fraud-associated accounts send exactly one TRANSFER/CASH_OUT in
the entire 30-day simulation, so a history lookup would add complexity for
no signal. The two strongest real signals (account balance draining to
zero, and destination-balance inconsistency) are both fully determined by
a single row. So `evaluate` takes just the transaction. If a future rule
genuinely needs cross-transaction history, that's a deliberate signature
change, not a default.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.models import Transaction


@dataclass
class RuleResult:
    """What a rule returns when it fires. None means no alert."""
    rule_name: str
    severity: str  # "LOW" | "MEDIUM" | "HIGH"
    reason: str


class Rule(ABC):
    """Abstract base class every detection rule must implement."""

    name: str = "UnnamedRule"

    # Which transaction types this rule applies to. EDA showed fraud in
    # this dataset occurs exclusively in TRANSFER and CASH_OUT -- PAYMENT,
    # CASH_IN, and DEBIT never contain a single fraud case. Rules default
    # to only running on those two types; this cuts the space the engine
    # evaluates by ~55% with zero recall cost.
    applicable_types = {"TRANSFER", "CASH_OUT"}

    @abstractmethod
    def evaluate(self, transaction: Transaction) -> Optional[RuleResult]:
        """Inspect a transaction and return a RuleResult if it fires, else None."""
        raise NotImplementedError
