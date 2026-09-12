"""
tracer.py
The core of GlassBox: a decorator that wraps any LLM call and logs its
cost, token usage, latency, and status to a local SQLite database.

Phase 3 adds two things on top of that:
  - Anomaly detection: each call is compared against the historical
    pattern for that same function, and flagged if its cost or latency
    is a statistical outlier (simple z-score check, no ML needed).
  - Version tagging: pass version="..." to @track() so you can compare
    a function's behavior before and after you change its prompt
    (see diff.py).
"""

import time
import sqlite3
import statistics
import functools
from datetime import datetime, timezone
from pathlib import Path

from pricing import estimate_cost

DB_PATH = Path(__file__).parent / "glassbox.db"

ANOMALY_MIN_SAMPLES = 5
ANOMALY_Z_THRESHOLD = 2.5


def _ensure_columns(conn):
    """Adds columns introduced in later phases to an existing database,
    so upgrading GlassBox never breaks data you've already logged."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(calls)").fetchall()}
    additions = {
        "version": "TEXT",
        "is_anomaly": "INTEGER DEFAULT 0",
        "anomaly_reason": "TEXT",
    }
    for col, col_type in additions.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE calls ADD COLUMN {col} {col_type}")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            function_name TEXT NOT NULL,
            model TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cost REAL,
            latency_ms INTEGER,
            status TEXT NOT NULL,
            error_message TEXT,
            note TEXT
        )
    """)
    _ensure_columns(conn)
    conn.commit()
    return conn


def _extract_usage(response):
    """Best-effort extraction of token usage + model name from a response object."""
    usage = getattr(response, "usage", None)
    model = getattr(response, "model", None)

    if usage is None:
        return None, None, model

    if hasattr(usage, "input_tokens"):
        return usage.input_tokens, usage.output_tokens, model

    if hasattr(usage, "prompt_tokens"):
        return usage.prompt_tokens, usage.completion_tokens, model

    return None, None, model


def _check_anomaly(conn, function_name, model, cost, latency_ms):
    """Flag cost or latency outliers for this exact function and model."""
    history = conn.execute(
        "SELECT cost, latency_ms FROM calls WHERE function_name = ? AND model = ? AND status = 'ok'",
        (function_name, model),
    ).fetchall()

    reasons = []
    past_costs = [r["cost"] for r in history if r["cost"] is not None]
    if cost is not None and len(past_costs) >= ANOMALY_MIN_SAMPLES:
        mean_cost = statistics.mean(past_costs)
        std_cost = statistics.pstdev(past_costs)
        if mean_cost > 0:
            if std_cost > 0 and (cost - mean_cost) / std_cost > ANOMALY_Z_THRESHOLD:
                reasons.append(f"cost {cost / mean_cost:.1f}x avg")
            elif std_cost == 0 and cost > mean_cost * 1.5:
                reasons.append(f"cost {cost / mean_cost:.1f}x avg")

    past_latencies = [r["latency_ms"] for r in history if r["latency_ms"] is not None]
    if latency_ms is not None and len(past_latencies) >= ANOMALY_MIN_SAMPLES:
        mean_latency = statistics.mean(past_latencies)
        std_latency = statistics.pstdev(past_latencies)
        if mean_latency > 0:
            if std_latency > 0 and (latency_ms - mean_latency) / std_latency > ANOMALY_Z_THRESHOLD:
                reasons.append(f"latency {latency_ms / mean_latency:.1f}x avg")
            elif std_latency == 0 and latency_ms > mean_latency * 1.5:
                reasons.append(f"latency {latency_ms / mean_latency:.1f}x avg")

    return bool(reasons), "; ".join(reasons) if reasons else None


def track(model=None, note=None, version=None):
    """Log every call and optionally tag it with a prompt version."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            timestamp = datetime.now(timezone.utc).isoformat()
            status = "ok"
            error_message = None
            input_tokens = output_tokens = None
            resolved_model = model

            try:
                result = func(*args, **kwargs)
                input_tokens, output_tokens, extracted_model = _extract_usage(result)
                resolved_model = resolved_model or extracted_model or "unknown"
                return result
            except Exception as error:
                status = "error"
                error_message = str(error)
                resolved_model = resolved_model or "unknown"
                raise
            finally:
                latency_ms = int((time.perf_counter() - start) * 1000)
                cost = estimate_cost(resolved_model, input_tokens, output_tokens)
                conn = _get_connection()
                is_anomaly, anomaly_reason = False, None
                if status == "ok":
                    is_anomaly, anomaly_reason = _check_anomaly(
                        conn, func.__name__, resolved_model, cost, latency_ms
                    )
                conn.execute(
                    """INSERT INTO calls
                       (timestamp, function_name, model, input_tokens, output_tokens,
                        cost, latency_ms, status, error_message, note, version,
                        is_anomaly, anomaly_reason)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (timestamp, func.__name__, resolved_model, input_tokens, output_tokens,
                     cost, latency_ms, status, error_message, note, version,
                     int(is_anomaly), anomaly_reason),
                )
                conn.commit()
                conn.close()

        return wrapper
    return decorator


def recent_calls(limit=20):
    """Most recent calls, newest first."""
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM calls ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def all_calls():
    """Every call ever logged, oldest first."""
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM calls ORDER BY id ASC").fetchall()
    conn.close()
    return rows
