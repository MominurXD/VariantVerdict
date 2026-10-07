from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .models import AnalysisResult

DB_PATH = Path(os.getenv('VARIANTVERDICT_DB', '/tmp/variantverdict.sqlite3'))


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            run_id TEXT PRIMARY KEY,
            experiment_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            verdict TEXT NOT NULL,
            payload TEXT NOT NULL
        )
    ''')
    return conn


def save(result: AnalysisResult):
    with _conn() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO analyses(run_id, experiment_name, created_at, verdict, payload) VALUES(?,?,?,?,?)',
            (result.run_id, result.experiment_name, result.created_at, result.verdict, result.model_dump_json()),
        )


def recent(limit: int = 10):
    with _conn() as conn:
        rows = conn.execute(
            'SELECT run_id, experiment_name, created_at, verdict FROM analyses ORDER BY created_at DESC LIMIT ?',
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get(run_id: str):
    with _conn() as conn:
        row = conn.execute('SELECT payload FROM analyses WHERE run_id=?', (run_id,)).fetchone()
        return json.loads(row['payload']) if row else None
