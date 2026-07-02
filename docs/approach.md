# Approach Notes

## What the JD Really Asks For

The target role is a founding Senior AI Engineer for Redrob's intelligence layer.
The strongest candidates should show production experience in:

- retrieval, search, ranking, recommendation, embeddings, and vector/hybrid search
- ranking evaluation such as NDCG, MRR, MAP, offline-online validation, and A/B tests
- Python and ML systems shipped to real users
- product engineering judgment, not research-only work or framework demos
- realistic availability and platform engagement

The job description explicitly says not to select people just because their skill
list contains many AI terms. The ranker therefore treats skill names as one
signal, but gives more weight to career-history evidence and Redrob behavioral
signals.

## Scoring Design

The ranker streams the candidate JSONL and computes an interpretable score from:

1. **Role/title fit** - high weight for search, recommendation, senior ML, senior
   AI, applied ML, and NLP engineering titles.
2. **Career evidence** - regex-weighted evidence for retrieval/search/ranking,
   ranking evaluation, production ML systems, and product shipping.
3. **Skill trust** - relevant skills are weighted by proficiency, duration,
   endorsements, and Redrob assessment scores. Weak "expert" claims with little
   usage evidence are penalized.
4. **Seniority fit** - ideal fit is 5-9 years, with softer credit around the band.
5. **Product-company signal** - product industries are rewarded; service-only
   consulting careers are down-weighted.
6. **Behavioral availability** - recent activity, recruiter response rate,
   response speed, open-to-work flag, interview completion, notice period, GitHub
   activity, and recruiter demand.
7. **Location/logistics** - India and Pune/Noida/Delhi NCR/Mumbai/Hyderabad
   proximity are rewarded; overseas candidates are down-weighted unless they
   show relocation willingness.
8. **Trap resistance** - penalties catch severe experience inconsistencies,
   suspicious duration mismatches, non-technical keyword stuffers, stale
   profiles, research-only/off-domain AI profiles, and services-only histories.

The final score is a calibrated monotonic transform of the adjusted evidence
score. This keeps CSV scores in a readable 0-1 range while preserving ordering.

## Why This Should Match The Evaluation

The hidden metric heavily weights NDCG@10 and NDCG@50, so the system prioritizes
the first page of recruiter review: strong current role, direct production
retrieval/ranking evidence, realistic seniority, active platform behavior, and
logistics fit.

Manual review also samples reasoning quality. The reasoning generator only uses
facts present in the candidate record: title, years, location, evidence category,
response rate, recency, notice period, and concerns. It avoids fabricated
employers or skills.

## Runtime

The full 100,000-candidate ranking pass completed locally in roughly 3 minutes
20 seconds on CPU and uses only the Python standard library. It makes no network
calls and stores only a top-100 heap plus a small audit file.
