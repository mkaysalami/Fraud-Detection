"""
Vectorized version of the evaluation, for running against the full 6.3M
row dataset in seconds instead of minutes.

The row-by-row scripts.evaluate_on_dataset script runs the actual OOP
Rule classes (the same code path the live API uses), which is the
correct thing to test against but is too slow in pure Python at 6.3M
rows. This script reimplements the identical rule logic as vectorized
pandas boolean masks -- same thresholds, same conditions -- for
dataset-scale evaluation.

The unit tests (tests/test_rules.py) are what guarantee the OOP rules and
this vectorized logic agree on individual cases; this script's job is
just to get an accurate number fast.

Run:
    python -m scripts.evaluate_vectorized /path/to/PS_..._log.csv
"""
import sys
import pandas as pd


def evaluate(csv_path: str):
    print(f"Loading {csv_path} ...")
    df = pd.read_csv(csv_path)
    print(f"Evaluating {len(df):,} transactions...\n")

    applicable = df["type"].isin(["TRANSFER", "CASH_OUT"])

    full_drain = applicable & (abs(df["oldbalanceOrg"] - df["amount"]) <= 0.01) & (df["oldbalanceOrg"] > 0)
    dest_glitch = applicable & (df["oldbalanceDest"] == 0) & (df["newbalanceDest"] == 0) & (df["amount"] > 0)
    large_amount = applicable & (df["amount"] >= 2_650_000.0)
    round_amount = applicable & (df["amount"] > 0) & (df["amount"] % 1000 == 0)

    rule_masks = {
        "FULL_ACCOUNT_DRAIN": full_drain,
        "DEST_BALANCE_GLITCH": dest_glitch,
        "LARGE_AMOUNT": large_amount,
        "ROUND_AMOUNT": round_amount,
    }

    combined = full_drain | dest_glitch | large_amount | round_amount
    actual = df["isFraud"].astype(bool)

    tp = (combined & actual).sum()
    fp = (combined & ~actual).sum()
    tn = (~combined & ~actual).sum()
    fn = (~combined & actual).sum()

    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    print("=== Combined rule engine (any rule fires) -- full dataset ===")
    print(f"Total transactions: {len(df):,}")
    print(f"Total actual fraud: {actual.sum():,}")
    print()
    print(f"True Positives:  {tp:,}")
    print(f"False Positives: {fp:,}")
    print(f"True Negatives:  {tn:,}")
    print(f"False Negatives: {fn:,}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall:    {recall:.2%}")
    print(f"F1:        {f1:.2%}")
    print()
    print("=== Per-rule breakdown ===")
    for name, mask in rule_masks.items():
        rp = df[mask]["isFraud"].mean() if mask.sum() else 0
        rr = (mask & actual).sum() / actual.sum() if actual.sum() else 0
        print(f"  {name}: fires {mask.sum():,}x | precision {rp:.2%} | recall {rr:.2%}")

    print()
    print("=== Compare: dataset's own built-in isFlaggedFraud rule ===")
    flagged = df["isFlaggedFraud"].astype(bool)
    flagged_recall = (flagged & actual).sum() / actual.sum() if actual.sum() else 0
    print(f"  isFlaggedFraud catches {(flagged & actual).sum():,} of {actual.sum():,} fraud cases ({flagged_recall:.2%} recall)")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/PS_20174392719_1491204439457_log.csv"
    evaluate(path)
