"""MiniCluster service template — one file, four services (via env vars).
SERVICE_NAME, PORT, NODE set by supervisord. Talks to redis for real work.
RED metrics self-reported at /metrics; faults injected via /fault/*.
"""
import os, time, threading, asyncio, random
from collections import deque

import redis as redis_lib
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

SERVICE = os.environ.get("SERVICE_NAME", "svc")
PORT = int(os.environ.get("PORT", "7001"))
NODE = os.environ.get("NODE", "node-1")

rds = redis_lib.Redis(host="127.0.0.1", port=6379, socket_timeout=1.5,
                      socket_connect_timeout=1.5, decode_responses=True)

app = FastAPI(title=SERVICE)

# ---- fault state -----------------------------------------------------------
fault = {"latency_ms": 0, "error_pct": 0.0, "spin_until": 0.0, "leak": [],
         "leak_mb_per_min": 0}

def _cpu_spin_worker():
    while True:
        if time.time() < fault["spin_until"]:
            x = 0
            for i in range(200_000):
                x += i * i
        else:
            time.sleep(0.2)

def _mem_leak_worker():
    while True:
        rate = fault["leak_mb_per_min"]
        if rate > 0:
            fault["leak"].append(bytearray(1024 * 1024 * rate // 6))  # per 10s
            time.sleep(10)
        else:
            time.sleep(1)

threading.Thread(target=_cpu_spin_worker, daemon=True).start()
threading.Thread(target=_mem_leak_worker, daemon=True).start()

# ---- RED metrics middleware ------------------------------------------------
m = {"count": 0, "errors": 0, "lats": deque(maxlen=1000)}

@app.middleware("http")
async def red_middleware(request: Request, call_next):
    is_work = request.url.path == "/work"
    t0 = time.perf_counter()
    if is_work and fault["latency_ms"]:
        await asyncio.sleep(fault["latency_ms"] / 1000.0)
    if is_work and fault["error_pct"] and random.random() < fault["error_pct"]:
        m["count"] += 1; m["errors"] += 1
        m["lats"].append((time.perf_counter() - t0) * 1000)
        return JSONResponse({"error": "injected"}, status_code=500)
    resp = await call_next(request)
    if is_work:
        m["count"] += 1
        m["lats"].append((time.perf_counter() - t0) * 1000)
        if resp.status_code >= 500:
            m["errors"] += 1
    return resp

# ---- endpoints ---------------------------------------------------------------
@app.get("/health")
def health():
    return {"service": SERVICE, "node": NODE, "status": "ok"}

@app.get("/work")
def work():
    """Real work: session ops in redis. If redis is down -> 500 (UC-4 cascade)."""
    try:
        key = f"{SERVICE}:counter"
        val = rds.incr(key)
        rds.setex(f"{SERVICE}:session:{val % 100}", 300, "x")
        return {"service": SERVICE, "ops": val}
    except Exception as e:
        return JSONResponse({"service": SERVICE, "error": str(e)[:80]}, status_code=500)

@app.get("/metrics")
def metrics():
    lats = sorted(m["lats"])
    p95 = lats[int(len(lats) * 0.95) - 1] if len(lats) >= 20 else (lats[-1] if lats else 0.0)
    return {"service": SERVICE, "node": NODE, "count": m["count"],
            "errors": m["errors"], "latency_p95_ms": round(p95, 2)}

# ---- fault injection ---------------------------------------------------------
@app.post("/fault/latency")
def f_latency(ms: int = 500):
    fault["latency_ms"] = ms
    return {"fault": "latency", "ms": ms}

@app.post("/fault/errors")
def f_errors(pct: float = 0.2):
    fault["error_pct"] = pct
    return {"fault": "errors", "pct": pct}

@app.post("/fault/cpu_spin")
def f_spin(seconds: int = 120):
    fault["spin_until"] = time.time() + seconds
    return {"fault": "cpu_spin", "seconds": seconds}

@app.post("/fault/mem_leak")
def f_leak(mb_per_min: int = 30):
    fault["leak_mb_per_min"] = mb_per_min
    return {"fault": "mem_leak", "mb_per_min": mb_per_min}

@app.post("/fault/clear")
def f_clear():
    fault.update({"latency_ms": 0, "error_pct": 0.0, "spin_until": 0.0,
                  "leak_mb_per_min": 0})
    fault["leak"].clear()
    return {"fault": "cleared"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
