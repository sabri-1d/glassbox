# GlassBox

> Local observability for LLM calls: cost, latency, failures, anomalies, and prompt experiments in one place.

GlassBox wraps model calls with a small Python decorator, records usage in SQLite, estimates cost from editable pricing data, and generates a dark operations dashboard as a standalone HTML report.

[Open the GlassBox dashboard](output/glassbox_report.html)

##  What It Does.

- Logs model name, token usage, estimated cost, latency, status, and errors.
- Supports Anthropic-style and OpenAI-style usage objects.
- Detects unusual cost or latency after a baseline is established.
- Tags calls with prompt versions for before-and-after comparisons.
- Streams recent calls and anomaly flags in a live terminal view.
- Generates a self-contained report with charts and tables.
- Keeps existing SQLite data when the schema gains new Phase 3 columns.

## Dashboard

Run the report generator and open the resulting file in a browser:

```powershell
python report.py
```

The dashboard includes:

- Spend over time
- Latency distribution
- Spend by model
- Prompt version comparison
- Anomaly and system health view
- Most expensive calls
- Recent failures

The generated report is written to `output/glassbox_report.html`.

## Quick Start

From the project root:

```powershell
cd C:\Users\quiqzy\Desktop\glassbox
.\code\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python demo.py
python report.py
```

The demo uses simulated calls, so no API key is required.

## Live Monitoring

Open two terminals in the project root.

Terminal 1:

```powershell
python watch.py
```

Terminal 2:

```powershell
python demo.py
```

The watcher displays recent calls, status, cost, latency, and anomaly flags.

## Prompt Version Diffing

Phase 3 can compare the same function under different prompt versions:

```powershell
python demo_versions.py
python diff.py --function call_claude
```

Example output compares:

- Number of calls
- Average cost
- Average latency
- Error rate

In real code, tag the same function when a prompt changes:

```python
@track(version="v1-original-prompt")
def call_claude(prompt):
    return client.messages.create(...)
```

Then change only the version tag after editing the prompt:

```python
@track(version="v2-concise-prompt")
def call_claude(prompt):
    return client.messages.create(...)
```

## Anomaly Detection

A call can be flagged when its cost or latency is statistically higher than the historical baseline for the same function and model.

GlassBox waits for at least five successful baseline calls before evaluating an outlier. This keeps functions that route between different models from producing misleading alerts.

Anomaly data is stored in these SQLite columns:

- `version`
- `is_anomaly`
- `anomaly_reason`

## Project Layout

```text
.
|-- demo.py                       simulated workload
|-- demo_versions.py              prompt version demo
|-- diff.py                       version comparison CLI
|-- tracer.py                     decorator, SQLite logging, anomalies
|-- watch.py                      live terminal dashboard
|-- report.py                     HTML report generator
|-- pricing.py                    cost calculation
|-- pricing.json                  editable model pricing
|-- templates/report_template.html dashboard template
|-- requirements.txt              Python dependencies
|-- env.example                   API key placeholders
`-- output/                       generated reports, ignored by Git
```

## Using a Real Provider

Copy the example environment file and add your local key:

```powershell
Copy-Item env.example .env
```

Never commit `.env`, API keys, `glassbox.db`, virtual environments, or generated reports. These are excluded by `.gitignore`.

The provider SDKs are optional. Uncomment and install the provider you use in `requirements.txt`, then replace the simulated function body with your real model call while keeping `@track()` around it.

## Database

GlassBox stores runtime telemetry in `glassbox.db`. The database is intentionally local and ignored by Git. Existing rows are preserved when Phase 3 adds columns, so upgrading the code does not require deleting your history.

To start with a clean local dataset, stop any running process and remove `glassbox.db`. This is optional and permanently deletes local telemetry.

## Requirements

- Python 3.10 or newer
- Windows PowerShell, macOS Terminal, or Linux shell
- Internet access when loading Plotly from the dashboard CDN

Install dependencies with:

```powershell
python -m pip install -r requirements.txt
```

