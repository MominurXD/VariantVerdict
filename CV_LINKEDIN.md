# Portfolio wording

## CV project entry

**VariantVerdict — Experiment Decision Intelligence Platform**  
Python, FastAPI, SciPy, SQLite, JavaScript, Docker, GitHub Actions

- Built a full-stack A/B-testing decision platform that evaluates conversion lift, statistical significance, confidence intervals, sample-ratio mismatch, power and operational guardrails before recommending ship/hold/collect decisions.
- Implemented segment-level experiment analysis with Holm multiple-testing correction, CSV ingestion and a SQLite audit trail for reproducible decision evidence.
- Designed a responsive analytics dashboard and automated CI pipeline covering API behaviour, statistical edge cases, JavaScript validation and production Docker builds.

## Short LinkedIn project description

Built **VariantVerdict**, an experimentation decision-intelligence platform for analysing A/B tests beyond a single p-value. The app checks conversion lift, confidence intervals, sample-ratio mismatch, statistical power, latency guardrails and subgroup results before producing a transparent ship/hold/collect recommendation. It includes aggregate CSV import, an auditable SQLite run history, a responsive dashboard, Docker and automated CI.

## LinkedIn launch post

I’ve built **VariantVerdict**, a full-stack experimentation decision platform focused on a problem I find interesting: a statistically significant A/B-test result is not automatically a safe product decision.

VariantVerdict analyses aggregate experiment data and checks:

- conversion lift and 95% confidence intervals
- two-proportion significance tests
- sample-ratio mismatch / allocation drift
- statistical power and minimum detectable effect
- latency guardrails
- segment-level results with multiple-testing correction
- reproducible run history in SQLite

One of the built-in scenarios deliberately creates a “winner” with higher conversion but worse latency, so the correct recommendation is to hold the release rather than blindly ship the uplift.

Tech: **Python, FastAPI, SciPy, SQLite, JavaScript, Docker and GitHub Actions**.

The project was designed to demonstrate statistical reasoning, backend engineering, data validation and product decision-making in one application.
