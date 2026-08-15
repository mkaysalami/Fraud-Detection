<<<<<<< HEAD
# Fraud-Detection-System
=======
# Transaction Monitoring & Fraud Alert System

A rule-based fraud detection API, with every rule chosen, calibrated, and
validated against a real, labeled dataset of 6.36 million mobile-money
transactions (PaySim, 8,213 confirmed fraud cases) — not invented rules
that merely sound plausible.

## Why this exists

Most "fraud detection" portfolio projects use a handful of rules that
*sound* reasonable (large amount, odd hour, round number...) without ever
checking whether those rules actually catch anything. This project starts
from the opposite direction: run real EDA first, keep what the data
supports, throw out what it doesn't, and report the actual precision/recall
numbers rather than assuming.

That process changed the design substantially. Two rules I initially built
(structuring/rapid-succession detection, geographic impossible-travel)
turned out to have **no support in the real data** and were removed. Two
rules that sounded weak in theory (a large-amount threshold, a round-number
check) turned out to be real signals, just much weaker than expected — so
they're kept, but demoted to low-confidence supporting evidence rather than
primary detectors.

## Data & methodology

Dataset: [PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1) — a
synthetic mobile-money transaction log built from real financial logs of a
mobile-money service operating in 14 countries. 6,362,620 transactions,
744 simulated hours (30 days), 5 transaction types, 8,213 labeled fraud
cases (0.13% base rate).

**Finding 1 — fraud is confined to two transaction types.**
Zero fraud cases exist in `PAYMENT`, `CASH_IN`, or `DEBIT`. All fraud is in
`TRANSFER` (0.77% of those txns) and `CASH_OUT` (0.18%). Every rule in this
system only evaluates those two types — this alone eliminates 55% of
transaction volume from consideration with zero recall cost.

**Finding 2 — draining an account to exactly zero is a near-perfect fraud signal.**
When `oldbalanceOrg == amount` (the origin account's entire balance is
moved out in one transaction), that transaction is fraud **100.00%** of
the time in this dataset, and this single condition catches **97.82%** of
all fraud. This became the primary detection rule (`FULL_ACCOUNT_DRAIN`).

**Finding 3 — a destination-balance bookkeeping glitch is a real, secondary signal.**
When a transaction's destination account shows `oldbalanceDest == 0` *and*
`newbalanceDest == 0` despite receiving a nonzero amount, it's fraud 70.46%
of the time, and adds recall on top of Finding 2 — combined, the two rules
reach 99.43% recall.

**Finding 4 — the dataset's own built-in fraud flag (`isFlaggedFraud`) is nearly useless.**
It's a simple ">200,000 in one transaction" business rule and catches only
16 of 8,213 fraud cases (0.19% recall) — a useful baseline to show *why*
naive threshold rules underperform data-driven ones.

**Finding 5 — two intuitive rules I originally built don't hold up:**
- *Rapid succession / structuring*: 99.94% of accounts send exactly **one**
  TRANSFER/CASH_OUT in the entire 30-day simulation. There's no
  multi-transaction pattern to detect here. Removed.
- *Geographic impossible travel*: this dataset has no location field.
  Untestable, so removed rather than kept on faith.

**Finding 6 — a large-amount threshold is real but weak, and combining it
naively with the strong rules actively hurts the system:**

| Rule set | Precision | Recall | F1 |
|---|---|---|---|
| `FULL_ACCOUNT_DRAIN` alone | 100.00% | 97.63% | 98.80% |
| `FULL_ACCOUNT_DRAIN` + `DEST_BALANCE_GLITCH` | **82.72%** | **99.43%** | **90.31%** |
| All 4 rules combined (naive OR) | 22.48% | 99.43% | 36.67% |

Adding `LARGE_AMOUNT` and `ROUND_AMOUNT` to the alerting decision adds
**zero** additional recall but drops precision by 60 points — they fire on
thousands of legitimate transactions. Full numbers in
[`scripts/evaluate_vectorized.py`](scripts/evaluate_vectorized.py) output.

**Design decision that followed from this:** the API distinguishes
`flagged_for_review` (true only when a HIGH/MEDIUM severity rule fires)
from the full `alerts` list (which still includes LOW-severity signals as
context for a human analyst, they just don't drive the flag alone). This
mirrors a real tradeoff fraud/AML systems have to make — more rules isn't
automatically better if they're not independently predictive.

## Detection rules

| Rule | Severity | Precision | Recall | Basis |
|---|---|---|---|---|
| `FULL_ACCOUNT_DRAIN` | HIGH | 100.00% | 97.82% | `oldbalanceOrg == amount` |
| `DEST_BALANCE_GLITCH` | MEDIUM | 70.46% | 49.56% | dest balance stuck at 0 despite nonzero amount |
| `LARGE_AMOUNT` | LOW | 4.75% | 16.04% | amount ≥ 99th percentile (~2.65M) |
| `ROUND_AMOUNT` | LOW | 8.77% | 3.49% | amount is an exact multiple of 1,000 |

## Architecture

Rules are a Strategy pattern: `Rule` (abstract base) defines
`evaluate(transaction) -> RuleResult | None`; each concrete rule is one
independently testable class; `RuleEngine` runs the full list against a
transaction. Adding a new rule never requires touching the API, database
layer, or other rules — write one class, register it in `engine.py`.

```
app/
  main.py                    FastAPI app and routes
  models.py                  Transaction, Alert (SQLAlchemy)
  schemas.py                 Pydantic request/response models
  database.py                DB engine/session
  engine.py                  RuleEngine
  rules/
    base.py                          Rule ABC + RuleResult
    full_account_drain.py            HIGH — primary signal
    dest_balance_glitch.py           MEDIUM — secondary signal
    large_amount.py                  LOW — weak supporting signal
    round_amount.py                  LOW — weak supporting signal
tests/
  test_rules.py               unit tests per rule
  test_api.py                 integration tests against the live API
scripts/
  evaluate_on_dataset.py       runs the actual OOP rules row-by-row against
                                labeled data (correct but slow at 6M+ rows)
  evaluate_vectorized.py       same logic as vectorized pandas ops, for
                                full-dataset-scale evaluation in seconds
  replay_sample.py              replays a real stratified sample against
                                the live API to demo end-to-end behavior
```

## Tech stack

FastAPI · SQLAlchemy · PostgreSQL (SQLite for local/tests) · pytest ·
GitHub Actions CI · Docker

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Docs at http://localhost:8000/docs

### Reproducing the evaluation

Download the dataset from
[Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1) (free account
required, ~470MB), then:

```bash
# Fast: vectorized, full 6.3M rows in seconds
python -m scripts.evaluate_vectorized path/to/PS_20174392719_1491204439457_log.csv

# Slower but exercises the actual production Rule classes; pass a sample
# size as the 2nd arg for a quick check
python -m scripts.evaluate_on_dataset path/to/PS_..._log.csv 200000

# Demo against the live API (start the server first)
python -m scripts.replay_sample path/to/PS_..._log.csv
```

## Running tests

```bash
pytest tests/ -v
```

19 tests: unit tests per rule (using realistic PaySim-shaped fixtures) and
integration tests against the full API.

## Deploying to AWS

- **RDS**: provision PostgreSQL, set `DATABASE_URL` accordingly.
- **API**: Docker image to Elastic Beanstalk, ECS, or EC2.
- `DATABASE_URL` is the only config needed to move from local SQLite to
  RDS Postgres.

## Honest limitations

- This is a synthetic dataset from a single mobile-money service; the
  specific numeric thresholds (e.g. the 2.65M large-amount cutoff) are
  calibrated to *this* data's distribution and would need re-calibration
  against any other dataset, not treated as universal constants.
- `FULL_ACCOUNT_DRAIN`'s near-perfect performance is partly an artifact of
  how PaySim's fraud-injection logic was built — real-world fraud is
  adversarial and would likely adapt once a rule like this became known,
  which is exactly why real systems combine rules with ML models and keep
  evolving them rather than shipping a static rule set forever.
- No feature here uses the `step` (time) field, since the two signals that
  actually worked don't need it — a natural next step would be exploring
  velocity/time-based features more rigorously than the (unsupported)
  rapid-succession hypothesis I started with.
>>>>>>> 5671340 (Initial commit)
