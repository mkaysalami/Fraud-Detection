"""
Unit tests for each rule, using fixture transactions shaped like real
PaySim rows. Test cases are chosen to mirror the actual patterns found
during EDA (see scripts/evaluate_vectorized.py and README.md), not
arbitrary invented values.
"""
from app.models import Transaction
from app.rules.full_account_drain import FullAccountDrainRule
from app.rules.dest_balance_glitch import DestBalanceGlitchRule
from app.rules.large_amount import LargeAmountRule
from app.rules.round_amount import RoundAmountRule


def make_txn(**overrides):
    defaults = dict(
        type="TRANSFER",
        amount=1000.0,
        name_orig="C1",
        oldbalance_org=5000.0,
        newbalance_orig=4000.0,
        name_dest="C2",
        oldbalance_dest=500.0,
        newbalance_dest=1500.0,
    )
    defaults.update(overrides)
    return Transaction(**defaults)


class TestFullAccountDrainRule:
    def test_fires_when_amount_equals_full_balance(self):
        rule = FullAccountDrainRule()
        txn = make_txn(oldbalance_org=5000.0, amount=5000.0)

        result = rule.evaluate(txn)

        assert result is not None
        assert result.rule_name == "FULL_ACCOUNT_DRAIN"
        assert result.severity == "HIGH"

    def test_does_not_fire_for_partial_withdrawal(self):
        rule = FullAccountDrainRule()
        txn = make_txn(oldbalance_org=5000.0, amount=1000.0)

        assert rule.evaluate(txn) is None

    def test_does_not_fire_for_zero_balance_account(self):
        # oldbalance_org == 0 means there's nothing to "drain" -- guards
        # against a degenerate 0 == 0 match on an already-empty account.
        rule = FullAccountDrainRule()
        txn = make_txn(oldbalance_org=0.0, amount=0.0)

        assert rule.evaluate(txn) is None

    def test_does_not_apply_to_payment_type(self):
        # PAYMENT never contains fraud in the real dataset -- rule should
        # not even evaluate the balance condition for it.
        rule = FullAccountDrainRule()
        txn = make_txn(type="PAYMENT", oldbalance_org=5000.0, amount=5000.0)

        assert rule.evaluate(txn) is None


class TestDestBalanceGlitchRule:
    def test_fires_when_dest_balance_stays_zero(self):
        rule = DestBalanceGlitchRule()
        txn = make_txn(oldbalance_dest=0.0, newbalance_dest=0.0, amount=5000.0)

        result = rule.evaluate(txn)

        assert result is not None
        assert result.rule_name == "DEST_BALANCE_GLITCH"

    def test_does_not_fire_when_dest_balance_updates_normally(self):
        rule = DestBalanceGlitchRule()
        txn = make_txn(oldbalance_dest=500.0, newbalance_dest=1500.0, amount=1000.0)

        assert rule.evaluate(txn) is None

    def test_does_not_fire_for_zero_amount(self):
        rule = DestBalanceGlitchRule()
        txn = make_txn(oldbalance_dest=0.0, newbalance_dest=0.0, amount=0.0)

        assert rule.evaluate(txn) is None


class TestLargeAmountRule:
    def test_fires_above_calibrated_threshold(self):
        rule = LargeAmountRule(threshold=2_650_000.0)
        txn = make_txn(amount=3_000_000.0)

        result = rule.evaluate(txn)

        assert result is not None
        assert result.severity == "LOW"  # deliberately low confidence

    def test_does_not_fire_below_threshold(self):
        rule = LargeAmountRule(threshold=2_650_000.0)
        txn = make_txn(amount=100_000.0)

        assert rule.evaluate(txn) is None


class TestRoundAmountRule:
    def test_fires_on_exact_multiple(self):
        rule = RoundAmountRule(multiple_of=1000.0)
        txn = make_txn(amount=5000.0)

        result = rule.evaluate(txn)

        assert result is not None
        assert result.severity == "LOW"

    def test_does_not_fire_on_irregular_amount(self):
        rule = RoundAmountRule(multiple_of=1000.0)
        txn = make_txn(amount=1234.56)

        assert rule.evaluate(txn) is None
