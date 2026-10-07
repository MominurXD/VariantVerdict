import os
from pathlib import Path

os.environ['VARIANTVERDICT_DB'] = '/tmp/variantverdict-test.sqlite3'
Path(os.environ['VARIANTVERDICT_DB']).unlink(missing_ok=True)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_scenarios_list():
    r = client.get('/api/scenarios')
    assert r.status_code == 200
    assert len(r.json()) == 4


def test_run_scenario():
    r = client.post('/api/scenarios/growth-reliability')
    assert r.status_code == 200
    assert r.json()['verdict'] == 'hold'


def test_history_saved():
    client.post('/api/scenarios/healthy-winner')
    r = client.get('/api/history')
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_history_detail():
    payload = client.post('/api/scenarios/noisy-experiment').json()
    r = client.get('/api/history/' + payload['run_id'])
    assert r.status_code == 200
    assert r.json()['experiment_name'] == payload['experiment_name']


def test_unknown_scenario_404():
    assert client.post('/api/scenarios/nope').status_code == 404


def test_csv_import():
    csv_data = '''date,segment,variant,assigned,conversions,latency_ms,error_rate
2026-01-01,Desktop,control,1000,100,100,0.01
2026-01-01,Desktop,treatment,1000,120,101,0.01
2026-01-02,Desktop,control,1000,100,100,0.01
2026-01-02,Desktop,treatment,1000,120,101,0.01
'''
    r = client.post('/api/import/csv?experiment_name=CSV%20Test', content=csv_data, headers={'content-type':'text/csv'})
    assert r.status_code == 200
    assert r.json()['experiment_name'] == 'CSV Test'


def test_csv_missing_columns_rejected():
    r = client.post('/api/import/csv', content='date,variant\n2026-01-01,control\n')
    assert r.status_code == 422


def test_root_serves_dashboard():
    r = client.get('/')
    assert r.status_code == 200
    assert 'VariantVerdict' in r.text
