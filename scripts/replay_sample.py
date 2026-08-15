"""
Replays a real, stratified sample of PaySim transactions against a
running API instance -- a mix of normal transactions and every fraud
type, so you can see actual alerts fire against real data (not invented
scenarios).

Run (with the API already running):
    python -m scripts.replay_sample data/PS_20174392719_1491204439457_log.csv
"""
import sys

import pandas as pd
import requests

BASE_URL = "http://localhost:8000"


def row_to_payload(row) -> dict:
    return {
        "step": int(row["step"]),
        "type": row["type"],
        "amount": float(row["amount"]),
        "name_orig": row["nameOrig"],
        "oldbalance_org": float(row["oldbalanceOrg"]),
        "newbalance_orig": float(row["newbalanceOrig"]),
        "name_dest": row["nameDest"],
        "oldbalance_dest": float(row["oldbalanceDest"]),
        "newbalance_dest": float(row["newbalanceDest"]),
    }


def main(csv_path: str, n_normal: int = 200, n_fraud: int = 50):
    df = pd.read_csv(csv_path)

    fraud_sample = df[df["isFraud"] == 1].sample(n=min(n_fraud, df["isFraud"].sum()), random_state=1)
    normal_sample = df[df["isFraud"] == 0].sample(n=n_normal, random_state=1)
    sample = pd.concat([normal_sample, fraud_sample]).sample(frac=1, random_state=1)  # shuffle

    tp = fp = fn = tn = 0
    for _, row in sample.iterrows():
        payload = row_to_payload(row)
        resp = requests.post(f"{BASE_URL}/transactions", json=payload)
        result = resp.json()

        flagged = result["flagged_for_review"]
        actual = bool(row["isFraud"])

        if flagged and actual:
            tp += 1
        elif flagged and not actual:
            fp += 1
        elif not flagged and actual:
            fn += 1
        else:
            tn += 1

    print(f"Replayed {len(sample)} real transactions ({n_fraud} known fraud, {n_normal} normal).")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print()
    stats = requests.get(f"{BASE_URL}/stats").json()
    print("Live /stats endpoint:", stats)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/PS_20174392719_1491204439457_log.csv"
    main(path)
