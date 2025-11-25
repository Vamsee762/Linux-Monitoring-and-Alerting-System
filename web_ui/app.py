from flask import Flask, render_template, jsonify, request
import subprocess, json, os, time, re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # points to monitor_project
LOG_FILE = BASE / "monitor.log"
STATE_FILE = BASE / "monitor_state.json"
CONFIG_FILE = BASE / "config.json"
MONITOR_SCRIPT = BASE / "monitor.py"

app = Flask(__name__, static_folder="static", template_folder="templates")

def read_log_lines(n=1000):
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    return lines[-n:]

def read_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def read_config_snapshot():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def parse_history_from_logs(max_points=100):
    if not LOG_FILE.exists():
        return []
    hist = []
    pattern = re.compile(r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*Snapshot: CPU: (?P<cpu>[\d\.]+)% \| MEM: (?P<mem>[\d\.]+)% \| DISK: (?P<disk>[\d\.]+)%', re.IGNORECASE)
    with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                hist.append({
                    "ts": m.group("ts"),
                    "cpu": float(m.group("cpu")),
                    "mem": float(m.group("mem")),
                    "disk": float(m.group("disk"))
                })
    return hist[-max_points:]

@app.route("/")
def index():
    state = read_state()
    log_lines = read_log_lines(1000)
    cfg = read_config_snapshot()
    last_snapshot = state.get("last_snapshot", {})
    last_pos = state.get("log_pos", 0)
    warnings = [l for l in log_lines if "WARNING" in l or "ALERT" in l or "ERROR" in l]
    history = parse_history_from_logs(max_points=200)
    return render_template("index.html",
                           last_snapshot=last_snapshot,
                           config=cfg,
                           log_lines=log_lines[::-1],  # newest first
                           warnings=warnings[:10],
                           last_pos=last_pos,
                           history=history
                           )

@app.route("/api/run", methods=["POST"])
def run_check():
    try:
        proc = subprocess.run(
            ["python", str(MONITOR_SCRIPT), "--once", "--config", str(CONFIG_FILE)],
            capture_output=True, text=True, timeout=120
        )
        return jsonify({
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "monitor run timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/logs")
def api_logs():
    return jsonify(read_log_lines(1000)[-1000:])

@app.route("/api/state")
def api_state():
    return jsonify(read_state())

if __name__ == "__main__":
    app.run(debug=True)
