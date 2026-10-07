# VariantVerdict

**Experiment decision intelligence for teams that want evidence before rollout.**

Personal project by **Mohammed Mominur Rahman Miah**.

VariantVerdict is a full-stack A/B-testing decision dashboard. It analyses aggregate experiment results, checks statistical validity and operational guardrails, explores segment-level signals, and stores an auditable history of each decision.

The project is intentionally built around a more realistic product question than “is the p-value below 0.05?” A treatment can improve conversion and still be unsafe to ship if allocation is broken, latency regresses, or the experiment is underpowered.

## Highlights

- Two-proportion z-test for conversion experiments.
- 95% confidence interval for absolute lift.
- Sample-ratio mismatch (SRM) detection using a chi-square test.
- Statistical power and minimum detectable effect diagnostics.
- Operational latency guardrail.
- Segment analysis with Holm multiple-testing correction.
- Daily control/treatment trajectory visualisation.
- Aggregate CSV import with schema validation.
- SQLite-backed audit history.
- Reproducible synthetic scenarios designed to expose common experimentation mistakes.
- Responsive, dependency-free dashboard frontend.
- FastAPI backend, automated tests, Docker and GitHub Actions CI.

## Dashboard preview

![VariantVerdict dashboard](docs/screenshots/dashboard.png)

The UI is responsive; a mobile capture is also included in `docs/screenshots/mobile.png`.

## Why this project is different

Most portfolio A/B-testing projects stop at “variant B won.” VariantVerdict models the decision layer around an experiment:

1. **Is the assignment trustworthy?** SRM catches badly split traffic.
2. **Did the treatment improve the primary metric?** A two-proportion z-test estimates lift and uncertainty.
3. **Did the experience regress elsewhere?** A latency guardrail can block an otherwise statistically significant winner.
4. **Was the test informative enough?** Power and MDE are shown as planning diagnostics.
5. **Are subgroup findings robust?** Segment p-values are adjusted with Holm’s method and clearly labelled exploratory.
6. **Can the decision be reproduced?** Each run is stored as an evidence snapshot in SQLite.

## Built-in scenarios

| Scenario | Expected decision | Why |
| --- | --- | --- |
| Growth vs reliability | Hold | Conversion improves, but latency breaches the release guardrail |
| Healthy winner | Ship | Positive lift, healthy allocation, sufficient power, clean guardrails |
| Allocation drift | Hold | Sample-ratio mismatch invalidates the experiment |
| Noisy experiment | Collect | Not enough evidence to make a rollout decision |

## CSV schema

VariantVerdict deliberately accepts **aggregate** data rather than individual customer events.

```csv
date,segment,variant,assigned,conversions,latency_ms,error_rate
2026-09-01,Desktop,control,1000,112,180,0.006
2026-09-01,Desktop,treatment,1000,128,218,0.006
```

Required columns:

- `date`
- `segment`
- `variant` (`control` or `treatment`)
- `assigned`
- `conversions`
- `latency_ms`
- `error_rate` (0–1)

## Statistical methods

### Primary metric

Two-sided pooled two-proportion z-test for the conversion difference. The interval shown for absolute lift uses the unpooled normal-approximation standard error.

### Sample-ratio mismatch

Pearson chi-square goodness-of-fit test against the planned treatment allocation. A very small p-value is treated as an experiment-integrity blocker.

### Segment analysis

Each segment is analysed with the same two-proportion test. P-values are corrected with the Holm step-down procedure to control family-wise error across the displayed exploratory segments.

### Power / MDE

Normal-approximation diagnostics are included to help explain whether the experiment was likely capable of detecting the observed/planned effect. They are not presented as a replacement for a pre-registered power analysis.

## Architecture

```text
Browser dashboard
      |
      v
FastAPI REST API
  |      |      |
  |      |      +--> SQLite audit history
  |      +---------> statistical analysis engine
  +----------------> reproducible scenarios / CSV import
```

The production frontend uses plain HTML/CSS/JavaScript so the statistical logic and backend remain the focus.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

## Tests

```bash
PYTHONPATH=. pytest -q
node --check web/app.js
docker build -t variantverdict .
```

## API

- `GET /api/health`
- `GET /api/scenarios`
- `POST /api/scenarios/{scenario_id}`
- `POST /api/analyze`
- `POST /api/import/csv`
- `GET /api/history`
- `GET /api/history/{run_id}`

Interactive API documentation is available at `/docs` when the FastAPI app is running.

## Responsible interpretation

VariantVerdict does not auto-deploy products and does not claim that a p-value alone determines business truth. Statistical significance, experiment integrity, operational guardrails, effect size and product context should all be reviewed together.

## Licence

MIT.
