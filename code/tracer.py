"""Decorate LLM calls and log usage, cost, latency, and status to SQLite."""

import functools
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from pricing import estimate_cost

DB_PATH = Path(__file__).parent / "glassbox.db"


def _get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("""CREATE TABLE IF NOT EXISTS calls (
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
    )""")
    connection.commit()
    return connection


def _extract_usage(response):
    usage = getattr(response, "usage", None)
    model = getattr(response, "model", None)
    if usage is None:
        return None, None, model
    if hasattr(usage, "input_tokens"):
        return usage.input_tokens, usage.output_tokens, model
    if hasattr(usage, "prompt_tokens"):
        return usage.prompt_tokens, usage.completion_tokens, model
    return None, None, model


def track(model=None, note=None):
    """Log every call made by the decorated function."""
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            timestamp = datetime.now(timezone.utc).isoformat()
            status = "ok"
            error_message = None
            input_tokens = output_tokens = None
            resolved_model = model
            try:
                result = function(*args, **kwargs)
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
                connection = _get_connection()
                connection.execute("""INSERT INTO calls
                    (timestamp, function_name, model, input_tokens, output_tokens,
                     cost, latency_ms, status, error_message, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (timestamp, function.__name__, resolved_model, input_tokens,
                     output_tokens, estimate_cost(resolved_model, input_tokens, output_tokens),
                     latency_ms, status, error_message, note))
                connection.commit()
                connection.close()
        return wrapper
    return decorator


def recent_calls(limit=20):
    connection = _get_connection()
    rows = connection.execute("""SELECT timestamp, function_name, model,
        input_tokens, output_tokens, cost, latency_ms, status
        FROM calls ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()
    connection.close()
    return rows