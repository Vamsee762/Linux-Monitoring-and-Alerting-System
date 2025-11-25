
#!/usr/bin/env python3
"""
Linux System Monitoring & Alerting Tool (MVP)

Features:
- Polls CPU, Memory, Disk, Network usage (using psutil)
- Parses /var/log/syslog (or a specified log file) for ERROR/WARNING since last run
- Sends email alerts via SMTP when thresholds exceeded or when critical log lines found
- Writes its own operation log to monitor.log
- Can run once (--once) or as a loop (--interval seconds)
- Configurable via --config JSON file

Usage examples:
  python3 monitor.py --once --config config.json
  python3 monitor.py --interval 60 --config config.json

Note: Running log parsing for /var/log/syslog may require root privileges.
"""

import argparse
import json
import logging
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

try:
    import psutil
except ImportError:
    print("psutil is required. Install with: pip install psutil")
    raise

LOGFILE = Path(__file__).parent / "monitor.log"

def setup_logging():
    logging.basicConfig(
        filename=str(LOGFILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s"
    )

def read_config(path):
    with open(path) as f:
        return json.load(f)

def metrics_snapshot():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "mem_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        # network I/O bytes since boot - we'll return bytes_sent and bytes_recv cumulatives
        "net_bytes_sent": psutil.net_io_counters().bytes_sent,
        "net_bytes_recv": psutil.net_io_counters().bytes_recv,
    }

def check_thresholds(snapshot, thresholds):
    alerts = []
    if snapshot["cpu_percent"] >= thresholds.get("cpu_percent", 90):
        alerts.append(f"CPU usage high: {snapshot['cpu_percent']}%")
    if snapshot["mem_percent"] >= thresholds.get("mem_percent", 90):
        alerts.append(f"Memory usage high: {snapshot['mem_percent']}%")
    if snapshot["disk_percent"] >= thresholds.get("disk_percent", 90):
        alerts.append(f"Disk usage high: {snapshot['disk_percent']}%")
    return alerts

def tail_log(file_path, last_pos=0, max_bytes=200000):
    """
    Returns (new_lines, new_position). Reads from last_pos (byte offset).
    """
    if not os.path.exists(file_path):
        return [], 0
    with open(file_path, "rb") as f:
        f.seek(last_pos)
        data = f.read(max_bytes)
        new_pos = f.tell()
    try:
        text = data.decode(errors="replace")
    except Exception:
        text = ""
    lines = text.splitlines()
    return lines, new_pos

def scan_for_patterns(lines, patterns):
    hits = []
    for ln in lines:
        for p in patterns:
            if p.lower() in ln.lower():
                hits.append(ln)
                break
    return hits

def send_email(smtp_cfg, subject, body):
    msg = EmailMessage()
    msg["From"] = smtp_cfg["from"]
    msg["To"] = ",".join(smtp_cfg["to"]) if isinstance(smtp_cfg["to"], list) else smtp_cfg["to"]
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if smtp_cfg.get("use_tls", True):
            server = smtplib.SMTP(smtp_cfg["server"], smtp_cfg.get("port", 587), timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(smtp_cfg["server"], smtp_cfg.get("port", 25), timeout=10)
        if smtp_cfg.get("username"):
            server.login(smtp_cfg["username"], smtp_cfg.get("password", ""))
        server.send_message(msg)
        server.quit()
        logging.info("Alert email sent to %s", msg["To"])
    except Exception as e:
        logging.exception("Failed to send alert email: %s", e)

def humanize_snapshot(snapshot):
    return ("CPU: {cpu_percent}% | MEM: {mem_percent}% | DISK: {disk_percent}% | "
            "NET_SENT: {net_bytes_sent} | NET_RECV: {net_bytes_recv}").format(**snapshot)

def load_last_state(state_file):
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_last_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f)

def run_once(cfg):
    state_file = cfg.get("state_file", str(Path(__file__).parent / "monitor_state.json"))
    last_state = load_last_state(state_file)
    snapshot = metrics_snapshot()
    logging.info("Snapshot: %s", humanize_snapshot(snapshot))
    alerts = check_thresholds(snapshot, cfg.get("thresholds", {}))

    # log parsing
    log_path = cfg.get("log_file", "/var/log/syslog")
    last_pos = last_state.get("log_pos", 0)
    lines, new_pos = tail_log(log_path, last_pos=last_pos)
    logging.info("Read %d new log lines from %s", len(lines), log_path)
    patterns = cfg.get("log_patterns", ["error", "fail", "critical", "unauthorized"])
    hits = scan_for_patterns(lines, patterns)
    if hits:
        alerts.append(f"Found {len(hits)} matching log lines (examples: {hits[:3]})")

    # If any alerts, send email + write detailed log
    if alerts:
        subject = cfg.get("alert_subject", "ALERT: Linux Monitor")
        body_lines = [
            f"Timestamp: {time.ctime()}",
            humanize_snapshot(snapshot),
            "Alerts:",
            "\n".join(alerts),
            "",
            "Recent matching log lines:",
            "\n".join(hits[:50])
        ]
        body = "\n".join(body_lines)
        send_email(cfg["smtp"], subject, body)
        logging.warning("Alerts triggered: %s", alerts)
    else:
        logging.info("No thresholds breached and no log hits.")

    # save state
    last_state["log_pos"] = new_pos
    last_state["last_snapshot"] = snapshot
    save_last_state(state_file, last_state)

def main():
    parser = argparse.ArgumentParser(description="Linux System Monitor (MVP)")
    parser.add_argument("--config", "-c", required=True, help="path to config.json")
    parser.add_argument("--once", action="store_true", help="Run one iteration and exit")
    parser.add_argument("--interval", type=int, default=0, help="Run every N seconds (0=no loop)")
    args = parser.parse_args()

    cfg = read_config(args.config)
    setup_logging()
    logging.info("Starting monitor with config %s", args.config)

    if args.once or args.interval <= 0:
        run_once(cfg)
    else:
        try:
            while True:
                run_once(cfg)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logging.info("Interrupted by user. Exiting.")

if __name__ == "__main__":
    main()
