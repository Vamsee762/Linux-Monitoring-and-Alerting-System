
# Linux Monitoring & Alerting Tool (Interview-ready)

**What this repo contains**

- `monitor.py` — core monitor script (collects CPU/MEM/DISK metrics with `psutil`, tails logs incrementally, triggers alerts, and sends email via SMTP).
- `web_ui/` — Flask-based dashboard (shows latest snapshot, logs, and charts; includes `/api/run` endpoint to trigger a manual check).
- `sample_logs/` — sample log(s) for local testing.
- `config.example.json` — safe example configuration. **Do not commit real credentials.**
- `requirements.txt` — minimal dependencies.
- `resume.pdf` — your resume (copied into the repo for demo/context).

---

## Quick start (local testing)

1. Clone the repo:
```bash
git clone https://github.com/YOUR_USERNAME/monitoring-system.git
cd monitoring-system
```

2. Create a Python virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

3. Create a working config:
```bash
cp config.example.json config.json
# Edit config.json: set your email/app-password if you want email alerts, or set "smtp": {} to disable email for testing.
```

4. Run a one-off check:
```bash
python monitor.py --once --config config.json
```

5. Run the web UI (in a separate terminal):
```bash
cd web_ui
python app.py
# Open http://127.0.0.1:5000 in your browser
```

---

## Security notes (IMPORTANT)
- **Never** commit real credentials, the `monitor_state.json`, or `monitor.log`. These are included in `.gitignore`.
- Use environment variables or a secrets manager to store production credentials.

---

## How to push to GitHub (exact commands)
```bash
git init
git add .
git commit -m "Initial commit - Monitoring system (cleaned for public)"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/monitoring-system.git
git push -u origin main
```

---

## Demo & interview talking points
- Explain log tailing (we save and reuse byte offset in `monitor_state.json` to avoid duplicate processing).
- Show how thresholds trigger alerts and how alerts are emailed (SMTP + app password).
- Demonstrate the dashboard, charts, and log search and how `/api/run` triggers a manual check.
- Show `monitor.log` entries for proof of runs and troubleshooting.

---

If you want, I can also:
- create a GitHub repo and push this for you (you must provide a personal access token or grant access), or
- generate a ready-to-upload ZIP (I've prepared one) which you can extract and push manually.
