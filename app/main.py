from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .analysis import analyze
from .models import AggregateRow, AnalysisRequest
from .scenarios import scenarios
from .storage import get, recent, save

app = FastAPI(title='VariantVerdict', version='1.0.0', description='Experiment evidence and guardrail analysis.')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'VariantVerdict', 'version': '1.0.0'}


@app.get('/api/scenarios')
def list_scenarios():
    return [
        {'id': 'growth-reliability', 'name': 'Growth vs reliability', 'description': 'Lift with a hidden cost'},
        {'id': 'healthy-winner', 'name': 'Healthy winner', 'description': 'Clear, balanced gains'},
        {'id': 'allocation-drift', 'name': 'Allocation drift', 'description': 'The deceptive test'},
        {'id': 'noisy-experiment', 'name': 'Noisy experiment', 'description': 'Know when to wait'},
    ]


@app.post('/api/scenarios/{scenario_id}')
def run_scenario(scenario_id: str):
    request = scenarios().get(scenario_id)
    if not request:
        raise HTTPException(status_code=404, detail='Unknown scenario')
    result = analyze(request)
    save(result)
    return result


@app.post('/api/analyze')
def analyze_request(request: AnalysisRequest):
    try:
        result = analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    save(result)
    return result


@app.post('/api/import/csv')
async def import_csv(request: Request, experiment_name: str = Query(default='Imported experiment')):
    text = (await request.body()).decode('utf-8-sig')
    try:
        reader = csv.DictReader(io.StringIO(text))
        required = {'date', 'segment', 'variant', 'assigned', 'conversions', 'latency_ms', 'error_rate'}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            missing = sorted(required - set(reader.fieldnames or []))
            raise HTTPException(status_code=422, detail=f"CSV missing columns: {', '.join(missing)}")
        rows = [AggregateRow(**row) for row in reader]
        payload = AnalysisRequest(experiment_name=experiment_name, rows=rows)
        result = analyze(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    save(result)
    return result


@app.get('/api/history')
def history(limit: int = Query(default=10, ge=1, le=50)):
    return recent(limit)


@app.get('/api/history/{run_id}')
def history_item(run_id: str):
    payload = get(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail='Run not found')
    return payload


WEB = Path(__file__).resolve().parent.parent / 'web'
app.mount('/', StaticFiles(directory=WEB, html=True), name='web')
