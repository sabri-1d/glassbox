"""Generate the GlassBox HTML dashboard with anomaly reporting."""

import os
import statistics
import webbrowser
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader

from tracer import all_calls

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHART_FONT = "IBM Plex Mono, monospace"
MUTED = "#8b95a1"
GRID = "rgba(255,255,255,0.08)"


def build_cost_over_time_chart(rows):
    cost_by_day = defaultdict(float)
    for row in rows:
        if row["cost"] is not None:
            cost_by_day[row["timestamp"][:10]] += row["cost"]
    days = sorted(cost_by_day)
    cumulative, running = [], 0.0
    for day in days:
        running += cost_by_day[day]
        cumulative.append(running)
    fig = go.Figure(go.Scatter(x=days, y=cumulative, mode="lines", fill="tozeroy",
        line=dict(color="#22d3ee", width=2), fillcolor="rgba(34,211,238,0.12)",
        hovertemplate="%{x}: $%{y:.4f} total<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=CHART_FONT, color=MUTED, size=12), margin=dict(l=10, r=10, t=10, b=30),
        height=240, xaxis=dict(showgrid=False, zeroline=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, color=MUTED, tickprefix="$"), showlegend=False)
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})


def build_latency_histogram(rows):
    latencies = [row["latency_ms"] for row in rows if row["latency_ms"] is not None]
    if not latencies:
        return None
    fig = go.Figure(go.Histogram(x=latencies, marker_color="#22d3ee", marker_line_width=0,
        nbinsx=20, hovertemplate="%{x}ms<br>%{y} calls<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=CHART_FONT, color=MUTED, size=12), margin=dict(l=10, r=10, t=10, b=30),
        height=220, xaxis=dict(showgrid=False, zeroline=False, color=MUTED, title="latency (ms)"),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, color=MUTED), showlegend=False, bargap=0.05)
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})


def build_model_breakdown_chart(rows):
    cost_by_model = defaultdict(float)
    for row in rows:
        if row["cost"] is not None:
            cost_by_model[row["model"] or "unknown"] += row["cost"]
    if not cost_by_model:
        return None
    models = list(cost_by_model)
    costs = [cost_by_model[model] for model in models]
    palette = ["#22d3ee", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#60a5fa"]
    fig = go.Figure(go.Pie(labels=models, values=costs, hole=0.55,
        marker=dict(colors=[palette[i % len(palette)] for i in range(len(models))],
        line=dict(color="#0a0e14", width=2)), textfont=dict(family=CHART_FONT, color="#e5e7eb", size=12),
        hovertemplate="%{label}: $%{value:.4f}<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=CHART_FONT, color="#e5e7eb", size=12), margin=dict(l=10, r=10, t=10, b=10),
        height=280, showlegend=True, legend=dict(font=dict(color=MUTED, size=11)))
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})


def main():
    rows = all_calls()
    if not rows:
        print("No calls logged yet. Run `python demo.py` first, or wire up a real call with @track().")
        return
    total_calls = len(rows)
    costs = [row["cost"] for row in rows if row["cost"] is not None]
    latencies = [row["latency_ms"] for row in rows if row["latency_ms"] is not None]
    error_count = sum(row["status"] == "error" for row in rows)
    error_rate = round(error_count / total_calls * 100, 1)
    health = "healthy" if error_rate < 2 else "watch" if error_rate < 5 else "unhealthy"
    priced_rows = [row for row in rows if row["cost"] is not None]
    top_expensive_fmt = [{"timestamp": row["timestamp"][:19].replace("T", " "),
        "function": row["function_name"], "model": row["model"] or "-", "cost": row["cost"],
        "latency": row["latency_ms"]} for row in sorted(priced_rows, key=lambda row: row["cost"], reverse=True)[:10]]
    recent_errors_fmt = [{"timestamp": row["timestamp"][:19].replace("T", " "),
        "function": row["function_name"], "message": row["error_message"] or "unknown error"}
        for row in [row for row in rows if row["status"] == "error"][-10:][::-1]]
    anomaly_rows = [row for row in rows if row["is_anomaly"]]
    anomalies_fmt = [{"timestamp": row["timestamp"][:19].replace("T", " "),
        "function": row["function_name"], "model": row["model"] or "-", "cost": row["cost"],
        "latency": row["latency_ms"], "reason": row["anomaly_reason"] or "flagged"}
        for row in anomaly_rows[-10:][::-1]]
    version_groups = defaultdict(lambda: {"costs": [], "latencies": [], "calls": 0, "errors": 0})
    for row in rows:
        if not row["version"]:
            continue
        group = version_groups[(row["function_name"], row["version"])]
        group["calls"] += 1
        group["errors"] += row["status"] == "error"
        if row["cost"] is not None:
            group["costs"].append(row["cost"])
        if row["latency_ms"] is not None:
            group["latencies"].append(row["latency_ms"])
    version_comparison = [{
        "function": function_name,
        "version": version,
        "calls": group["calls"],
        "avg_cost": statistics.mean(group["costs"]) if group["costs"] else None,
        "avg_latency": statistics.mean(group["latencies"]) if group["latencies"] else None,
        "error_rate": group["errors"] / group["calls"] * 100,
    } for (function_name, version), group in sorted(version_groups.items())]
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    html = env.get_template("report_template.html").render(
        total_calls=total_calls, total_cost=f"{sum(costs):.4f}",
        avg_latency=int(sum(latencies) / len(latencies)) if latencies else 0,
        error_rate=error_rate, error_count=error_count, health=health,
        date_range=f"{rows[0]['timestamp'][:10]} to {rows[-1]['timestamp'][:10]}",
        cost_chart=build_cost_over_time_chart(rows), latency_chart=build_latency_histogram(rows),
        model_chart=build_model_breakdown_chart(rows), top_expensive=top_expensive_fmt,
        recent_errors=recent_errors_fmt, anomalies=anomalies_fmt, anomaly_count=len(anomaly_rows),
        version_comparison=version_comparison,
        generated_at=datetime.now().strftime("%b %d, %Y %H:%M"))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "glassbox_report.html")
    with open(out_path, "w", encoding="utf-8") as output_file:
        output_file.write(html)
    print(f"Report saved to {out_path}")
    webbrowser.open(Path(out_path).resolve().as_uri())


if __name__ == "__main__":
    main()
