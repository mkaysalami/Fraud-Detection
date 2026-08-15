"""
Evaluates the rule engine directly against the real, labeled PaySim
dataset -- no API/DB round trip, just the rules run in-process against
every row, compared to the ground-truth isFraud column.

This is the actual validation behind every precision/recall number quoted
in the rule docstrings and the README.

Run:
    python -m scripts.evaluate_on_dataset /path/to/PS_..._log.csv
"""
import sys

import pandas as pd

from app.models import Transaction
from app.engine import RuleEngine


def row_to_transaction(row) -> Transaction:
    """Build an in-memory (unsaved) Transaction from a dataframe row."""
    return Transaction(
        step=int(row["step"]),
        type=row["type"],
        amount=float(row["amount"]),
        name_orig=row["nameOrig"],
        oldbalance_org=float(row["oldbalanceOrg"]),
        newbalance_orig=float(row["newbalanceOrig"]),
        name_dest=row["nameDest"],
        oldbalance_dest=float(row["oldbalanceDest"]),
        newbalance_dest=float(row["newbalanceDest"]),
    )


def evaluate(csv_path: str, sample: int = None):
    print(f"Loading {csv_path} ...")
    df = pd.read_csv(csv_path)
    if sample:
        df = df.sample(n=sample, random_state=42)
    print(f"Evaluating {len(df):,} transactions...\n")

    engine = RuleEngine()

    tp = fp = tn = fn = 0
    per_rule_hits = {rule.name: 0 for rule in engine.rules}

    for _, row in df.iterrows():
        txn = row_to_transaction(row)
        actual_fraud = bool(row["isFraud"])

        alerts = engine.evaluate(txn, db=None)
        flagged = len(alerts) > 0

        for a in alerts:
            per_rule_hits[a.rule_name] += 1

        if flagged and actual_fraud:
            tp += 1
        elif flagged and not actual_fraud:
            fp += 1
        elif not flagged and not actual_fraud:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    print("=== Combined rule engine (any rule fires) ===")
    print(f"True Positives:  {tp:,}")
    print(f"False Positives: {fp:,}")
    print(f"True Negatives:  {tn:,}")
    print(f"False Negatives: {fn:,}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall:    {recall:.2%}")
    print(f"F1:        {f1:.2%}")
    print()
    print("=== Alerts fired per rule ===")
    for name, count in per_rule_hits.items():
        print(f"  {name}: {count:,}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/PS_20174392719_1491204439457_log.csv"
    # Full 6.3M rows takes a few minutes in pure Python; pass a sample size
    # as a 2nd arg for a quick smoke test, e.g.:
    #   python -m scripts.evaluate_on_dataset data/paysim.csv 200000
    sample = int(sys.argv[2]) if len(sys.argv) > 2 else None
    evaluate(path, sample)
