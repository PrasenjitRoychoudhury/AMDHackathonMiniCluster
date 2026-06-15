"""MiniCluster telemetry collector.
Every TICK_S real seconds: get PIDs from supervisord XML-RPC, sample psutil
CPU/mem per process, scrape each service's /metrics, compute RED deltas, and
append a row per service to live_metrics.csv — stamped as +1 SIMULATED MINUTE
per tick so the existing pipeline sees its expected 1/min cadence.
Columns match the existing pipeline: timestamp, service, cpu_utilization, rps,
latency_p95_ms, error_rate  (+ mem_mb, node).
"""
import csv, os, time
from datetime import datetime, timedelta
from xmlrpc.client import ServerProxy

import httpx
import psutil

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "live_metrics.csv")
TICK_S = 15                      # real seconds per simulated minute
SERVICES = {"payments": 7001, "auth": 7002, "checkout": 7003, "fraud": 7004}

COLS = ["timestamp", "service", "cpu_utilization", "rps",
        "latency_p95_ms", "error_rate", "mem_mb", "node"]

sup = ServerProxy("http://127.0.0.1:9001/RPC2")
prev = {}          # service -> (count, errors)
procs = {}         # service -> psutil.Process

def get_pids():
    out = {}
    try:
        for p in sup.supervisor.getAllProcessInfo():
            if p["name"] in SERVICES and p["pid"]:
                out[p["name"]] = p["pid"]
    except Exception:
        pass
    return out

def sample(name, port, pid, sim_ts):
    # cpu/mem via psutil (cache Process objects so cpu_percent has a window)
    cpu = mem = 0.0
    try:
        if name not in procs or procs[name].pid != pid:
            procs[name] = psutil.Process(pid)
            procs[name].cpu_percent(None)        # prime
        cpu = procs[name].cpu_percent(None)
        mem = procs[name].memory_info().rss / 1024 / 1024
    except Exception:
        procs.pop(name, None)

    # RED via /metrics scrape
    p95 = 0.0
    rps = 0.0
    err_rate = 0.0
    node = ""
    try:
        r = httpx.get(f"http://127.0.0.1:{port}/metrics", timeout=2.0).json()
        p95 = r.get("latency_p95_ms", 0.0)
        node = r.get("node", "")
        c, e = r.get("count", 0), r.get("errors", 0)
        pc, pe = prev.get(name, (c, e))
        dc, de = max(0, c - pc), max(0, e - pe)
        prev[name] = (c, e)
        rps = round(dc / TICK_S, 3)
        err_rate = round(de / dc, 4) if dc else 0.0
    except Exception:
        err_rate = 1.0           # probe failed = service effectively down

    return [sim_ts.isoformat(), name, round(cpu, 2), rps, p95, err_rate,
            round(mem, 1), node]

def main():
    new = not os.path.exists(OUT)
    sim_t = datetime.now().replace(second=0, microsecond=0)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLS)
            f.flush()
        while True:
            pids = get_pids()
            for name, port in SERVICES.items():
                row = sample(name, port, pids.get(name, 0), sim_t)
                w.writerow(row)
            f.flush()
            sim_t += timedelta(minutes=1)        # sim-minute stamping
            time.sleep(TICK_S)

if __name__ == "__main__":
    main()
