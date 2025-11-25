
# Linux Monitoring & Alerting Tool

**What this repo contains**

- `monitor.py` — core monitor script (collects CPU/MEM/DISK metrics with `psutil`, tails logs incrementally, triggers alerts, and sends email via SMTP).
- `web_ui/` — Flask-based dashboard (shows latest snapshot, logs, and charts; includes `/api/run` endpoint to trigger a manual check).
- `config.example.json` — safe example configuration. **Do not commit real credentials.**
- `requirements.txt` — minimal dependencies.

---
