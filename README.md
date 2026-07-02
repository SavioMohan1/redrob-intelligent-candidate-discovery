# Redrob Intelligent Candidate Discovery Ranker

This repository contains a reproducible offline ranker for the Redrob Senior AI
Engineer candidate-ranking challenge.

## Approach

The solution converts the job description into interpretable scoring signals:

- production retrieval, search, recommendation, embedding, and ranking evidence
- ranking/evaluation maturity such as NDCG, MRR, A/B testing, and eval harnesses
- seniority fit around the intended 5-9 year band
- product-company and shipping background
- trusted skills, using proficiency, duration, endorsements, and assessments
- behavioral availability from Redrob signals
- logistics fit for Pune/Noida or relocation
- penalties for keyword stuffing, stale profiles, service-only careers, off-domain
  AI profiles, and consistency issues that can indicate honeypots

The ranker is deliberately lightweight. It streams `candidates.jsonl`, keeps only
the top candidates in memory, and does not call any network APIs.

## Reproduce

```bash
python rank.py --candidates ./candidates.jsonl --out ./outputs/submission.csv
python validate_submission.py ./outputs/submission.csv
```

The ranking step is CPU-only, uses no network, and has no third-party runtime
dependencies.

## Files

- `rank.py` - command-line entry point.
- `src/ranker.py` - feature extraction, scoring, reasoning, and CSV writing.
- `outputs/submission.csv` - generated top-100 ranking.
- `outputs/audit_top100.json` - debug/audit view of the top 100.
