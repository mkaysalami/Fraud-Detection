# Fraud Detection System

A rule-based fraud detection API, deployed on AWS, with every detection rule calibrated and validated against a real, labeled dataset of 6.36 million transactions — not invented rules that merely sound plausible.

**Live API:** http://18.221.165.163:8000/docs

## Overview

Most student fraud-detection projects use rules that *sound* reasonable without checking whether they actually catch anything. This one starts from data: run EDA on 6.36M real transactions (PaySim dataset, 8,213 confirmed fraud cases), keep what the data supports, drop what it doesn't.

Two rules I originally built (structuring detection, geo-jump) had no support in the real data and were removed. The strongest signal — draining an account to exactly zero — turned out to catch 97.8% of fraud with 100% precision.

## Key results

| Rule set | Precision | Recall |
|---|---|---|
| Full account drain (primary rule) | 100.0% | 97.8% |
| + destination balance glitch (secondary rule) | 82.7% | 99.4% |

For comparison, the dataset's own built-in fraud flag catches only 0.2% of fraud — a useful baseline showing why data-calibrated rules beat naive thresholds.

## Stack

Python · FastAPI · SQLAlchemy · PostgreSQL · Docker · AWS (EC2, RDS) · pytest · GitHub Actions

## Architecture

Detection rules are a Strategy pattern (`Rule` abstract base class, `RuleEngine` runner) — each rule is an independently testable class; adding a new one never touches the API or database layer.

```
app/
  main.py, models.py, schemas.py, database.py, engine.py
  rules/            one class per detection rule
tests/              19 tests (unit + API integration)
scripts/            EDA / evaluation scripts against the real dataset
```

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Docs at http://localhost:8000/docs

## Full write-up

Detailed EDA findings, per-rule precision/recall, and design tradeoffs: [`docs/FINDINGS.md`](docs/FINDINGS.md)
