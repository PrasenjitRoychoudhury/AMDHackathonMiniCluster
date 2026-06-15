# AGENTS026 — Autonomous Incident Diagnosis & Resolution

> **AMD Instinct MI300X · 192GB VRAM · ROCm · Qwen3-30B-A3B · PyTorch · Streamlit**

An end-to-end AIOps platform for autonomous incident management in a synthetic banking microservices environment. Built for the **TCS AMD Hackathon 2026**.

---

## What is AGENTS026?

AGENTS026 detects, diagnoses, and resolves production incidents autonomously — without human intervention — while maintaining a **Human-in-the-Loop (HITL) gate** for high-severity actions.

It runs on **AMD Instinct MI300X** hardware (192GB VRAM, ROCm) with **Qwen3-30B-A3B** served via vLLM for all LLM reasoning tasks.

### Problems it solves

| Problem | Solution |
|---|---|
| Reactive incident management | TGNN predicts cascading failures **4+ minutes** before they occur |
| Alert fatigue | Redis-backed Alert Storm correlation reduces noise by **>80%** |
| Manual remediation | Policy-gated autonomous execution via supervisord XML-RPC |
| Blast radius blindness | GNN maps downstream service impact before action is taken |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  L1 — MiniCluster (supervisord)                                 │
│  payments:7001  auth:7002  fraud:7003  checkout:7004  loadgen   │
└────────────────────────┬────────────────────────────────────────┘
                         │ RED metrics every 5s
┌────────────────────────▼────────────────────────────────────────┐
│  L2 — Telemetry                                                 │
│  collector.py  →  live_metrics.csv  +  Redis:6379               │
└───────┬──────────────────────┬──────────────────────────────────┘
        │                      │
┌───────▼──────────────────────▼──────────────────────────────────┐
│  L3 — Detection  🔴 GPU (AMD MI300X)                            │
│  AE Detector (ae_model.pt)  ·  LSTM Forecast (lstm_model.pt)   │
│  Statistical Engine  ·  SLO Burn Rate  ·  Alert Storm UC-4      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ anomaly signals
┌───────────────────────────▼─────────────────────────────────────┐
│  L4 — AI Reasoning  🔴 GPU (AMD MI300X)                         │
│  Qwen3-30B-A3B (vLLM:8000)  ·  GNN Blast Radius                │
│  TGNN Predictor (tgnn_model.pt)  ·  FAISS + BGE embeddings     │
│  Distributed Trace Correlation  ·  Log Embedding                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ RCA + blast radius + predictions
┌───────────────────────────▼─────────────────────────────────────┐
│  L5 — Remediation                                               │
│  Remediation Pipeline (pydantic-ai)  ·  HITL Queue             │
│  Canary Analysis (Mann-Whitney U)  ·  AI Actions               │
│  Chaos Scheduler  ·  RLHF Reward Model                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│  L6 — Observability                                             │
│  Streamlit Console — live_console.py :8502 — 20 tabs            │
└─────────────────────────────────────────────────────────────────┘

AMD Instinct MI300X — 192GB VRAM — ROCm
AE · LSTM · GNN · TGNN · RLHF trained on MI300X
Qwen3-30B-A3B inference — 96–97% GPU utilisation during TGNN training
```

---

## Features

### Monitoring
| Tab | Description |
|---|---|
| Cluster Health | Real-time RED metrics for all 4 services. Auto-refresh 10s. |
| Live Telemetry | Streaming time-series charts from `live_metrics.csv` |
| Anomalies | Threshold-based statistical engine. SLO breach detection. |
| Topology | Live service dependency graph — 4 nodes, 6 edges. GPU Insight via Qwen3-30B. |

### Intelligence
| Tab | Description |
|---|---|
| AE Detector 🔴 | Autoencoder anomaly detector trained on MI300X. `ae_model.pt` |
| Trend Forecast | Rolling window statistical trend forecasting |
| FAISS Search | Semantic incident search — BGE-large-en-v1.5 + FAISS index |
| Log Embedding | Service log vectorisation for similarity search |

### Operations
| Tab | Description |
|---|---|
| Fault Injection | REST-based fault injector — latency, error rate, CPU stress |
| Chaos Scheduler | Automated randomised fault scenarios |
| Alert Storm UC-4 | Redis-backed alert correlation and deduplication |
| HITL Queue | Human-in-the-Loop approval gate for high/critical actions |
| AI Actions | LLM-driven action executor via supervisord XML-RPC |

### Advanced GPU 🔴
| Tab | Description |
|---|---|
| RLHF Reward Model | Reward scoring of remediation action candidates. `rlhf_model.pt` |
| LSTM Forecasting | 5-step metric anomaly forecasting. `lstm_model.pt` |
| Remediation Pipeline | detect → diagnose → plan → HITL → execute → verify |
| Canary Analysis | Mann-Whitney U test with auto-rollback. `canary_log.jsonl` |
| GNN Blast Radius | 2-layer GNN — downstream failure impact. `gnn_blast_radius.pt` |
| Trace Correlation | Netflix Critical Path algorithm + RCA scoring |
| SLO Burn Rate | Google SRE Book Ch.5 — PAGE / TICKET / OK alerts |
| TGNN Predictor | Temporal Graph Attention Network — 64,522 params, 60M datapoints, 4-min early warning |

---

## GPU Models (AMD MI300X)

| Model | File | Params | Training |
|---|---|---|---|
| Autoencoder | `ae_model.pt` | ~50K | Reconstruction error on metric sequences |
| RLHF Reward | `rlhf_model.pt` | ~100K | Reward scoring of remediation candidates |
| LSTM | `lstm_model.pt` | ~200K | 5-step metric forecasting |
| GNN | `gnn_blast_radius.pt` | ~30K | Graph-based blast radius prediction |
| **TGNN** | `tgnn_model.pt` | **64,522** | **100 epochs · 60M datapoints · 23.1 min on MI300X** |

---

## Service Graph

```
payments (0) ──► auth (1) ──► checkout (3)
    │                │
    ▼                ▼
fraud (2) ◄──────────┘
    │
    ▼
checkout (3)

edge_index = [[0,0,1,1,2],[1,2,2,3,3]]
```

---

## Port Map

| Port | Service | Notes |
|---|---|---|
| 7001 | payments | Core payment processing |
| 7002 | auth | Authentication & authorisation |
| 7003 | fraud | Fraud detection |
| 7004 | checkout | Checkout orchestration |
| 6379 | Redis | Alert Storm + metric time-series cache |
| 8000 | vLLM / Qwen3-30B-A3B | LLM inference — `api-key: abc-123` |
| 8502 | Streamlit Console | 20-tab AIOps dashboard |
| 9001 | supervisord XML-RPC | Process control |

---

## Quick Start

### Prerequisites

- AMD Instinct MI300X with ROCm
- Python 3.12
- vLLM with Qwen3-30B-A3B model cached

### Step 1 — Check persistence

```bash
ls /workspace/shared/minicluster && echo "CODE SURVIVED" || echo "RESTORE NEEDED"
```

### Step 2 — Install dependencies

```bash
pip install pydantic-ai-slim faiss-cpu pandas matplotlib pyarrow sentence-transformers && \
pip install -U openai && \
pip install streamlit --ignore-installed blinker "starlette>=0.40,<0.49" "numpy>=2,<2.3" "protobuf<7" "pandas<3" && \
pip install fastapi uvicorn httpx psutil redis supervisor pgserver networkx scikit-learn
```

### Step 3 — Start vLLM (Terminal 1)

```bash
unset HF_HOME
VLLM_USE_TRITON_FLASH_ATTN=0 \
vllm serve Qwen/Qwen3-30B-A3B \
  --served-model-name Qwen3-30B-A3B \
  --api-key abc-123 \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --trust-remote-code
```

### Step 4 — Start MiniCluster (Terminal 2)

```bash
cd /workspace/shared/minicluster
rm -f supervisord.pid
python3 gen_conf.py
supervisord -c supervisord.conf
sleep 4 && supervisorctl -c supervisord.conf status
```

Expected output:
```
auth       RUNNING   pid XXXX, uptime 0:00:04
checkout   RUNNING   pid XXXX, uptime 0:00:04
collector  RUNNING   pid XXXX, uptime 0:00:04
fraud      RUNNING   pid XXXX, uptime 0:00:04
loadgen    RUNNING   pid XXXX, uptime 0:00:04
payments   RUNNING   pid XXXX, uptime 0:00:04
```

### Step 5 — Start Redis (Terminal 2)

```bash
apt-get update && apt-get install -y redis-server
redis-server --port 6379 --daemonize yes --save '' --loglevel warning \
  --logfile /workspace/shared/minicluster/logs/redis.log
redis-cli ping   # expect: PONG
```

### Step 6 — Start Streamlit (Terminal 3)

```bash
cd /workspace/shared/minicluster
streamlit run live_console.py \
  --server.port 8502 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false
```

Open the console at:
```
https://<your-notebook-url>/proxy/8502/
```

### Step 7 — Verify full stack

```bash
echo "=== CLUSTER ===" && supervisorctl -c supervisord.conf status
echo "=== REDIS ===" && redis-cli ping
echo "=== vLLM ===" && curl -s http://localhost:8000/v1/models | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data']])"
echo "=== ARTEFACTS ===" && ls -lh /workspace/shared/*.pt
echo "=== METRICS ===" && tail -3 /workspace/shared/minicluster/live_metrics.csv
```

---

## Repository Structure

```
/workspace/shared/minicluster/
├── app.py                     # Universal FastAPI service (payments/auth/fraud/checkout)
├── gen_conf.py                # supervisord.conf generator (112-core pinning)
├── collector.py               # Metrics collector daemon (5s poll → CSV + Redis)
├── live_console.py            # Streamlit 20-tab console
├── supervisord.conf           # Generated process control config
├── live_metrics.csv           # Live telemetry (latency_p95_ms · error_rate · cpu)
├── ae_anomaly_detector.ipynb  # Autoencoder training (MI300X)
├── agents026_rca_agent.ipynb  # LLM RCA agent (Qwen3-30B + pydantic-ai)
├── canary_analysis.ipynb      # Canary engine (Mann-Whitney U + auto-rollback)
├── chaos_scheduler.ipynb      # Chaos engineering scheduler
├── faiss_vector_search.ipynb  # FAISS index builder (BGE-large-en-v1.5)
├── gnn_blast_radius.ipynb     # GNN training (MI300X)
├── logs/                      # Per-service logs + redis.log + supervisord.log
└── ...

/workspace/shared/
├── ae_model.pt                # Autoencoder weights (~2MB)
├── lstm_model.pt              # LSTM weights (~8MB)
├── gnn_blast_radius.pt        # GNN weights (~1MB)
├── tgnn_model.pt              # TGNN weights (64,522 params, ~300KB)
├── rlhf_model.pt              # RLHF Reward Model (~4MB)
├── tgnn_inference.py          # TGNN inference script
├── canary_log.jsonl           # Canary test results
├── rollback_log.jsonl         # Auto-rollback events
├── trace_log.jsonl            # Distributed trace records
├── slo_log.jsonl              # SLO burn rate events
├── tgnn_predictions.jsonl     # TGNN failure probability scores
├── hitl_queue.jsonl           # Pending HITL approvals
└── tgnn_dataset/              # Training data (237MB — excluded from backup)
    ├── scenarios.pt           # 50,000 scenarios · 60M datapoints
    └── labels.pt              # Binary failure labels
```

---

## Key Design Decisions

**Why AMD MI300X?**
192GB unified memory pool allows training TGNN on 60M datapoints and serving Qwen3-30B-A3B simultaneously — impossible on standard 80GB A100 configurations.

**Why Qwen3-30B-A3B?**
Mixture-of-experts architecture activates only 3B params per forward pass while maintaining 30B-scale reasoning quality. Ideal for continuous RCA inference with low latency.

**Why supervisord over Kubernetes?**
Single-node hackathon environment. supervisord gives process lifecycle management, restart policies, and XML-RPC control without orchestration overhead. The remediation executor calls `supervisorctl restart <service>` directly.

**Why Mann-Whitney U for canary testing?**
Non-parametric — makes no assumption about metric distribution shape. Robust to the heavy-tailed latency distributions typical in banking microservices.

**Why TGNN over standard GNN?**
Temporal dimension captures *when* failures propagate, not just *which* services are affected. The LSTM component models metric time-series alongside the graph attention layers.

---

## Known Limitations

- Redis runs as a manually daemonised process (no systemd in AMD notebook containers). `supervisorctl status` shows `redis FATAL` — this is expected. Verify with `redis-cli ping`.
- `tgnn_dataset/` (237MB) is excluded from tar backups. Only `tgnn_model.pt` (300KB) is backed up.
- vLLM must be started before any pip installs in the same terminal to avoid dependency conflicts.
- The critical CSV column name is `latency_p95_ms` — not `latency_p95`.

---

## Incident Response Flow

```
loadgen → /metrics → collector.py → live_metrics.csv + Redis
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              AE Detector           LSTM Forecast         Stat Engine
                    │                     │                     │
                    └─────────┬───────────┘                     │
                              ▼                                 │
                     Alert Storm UC-4 ◄──────────────────────── ┘
                              │  deduplicate + correlate
                              ▼
                    TGNN Predictor (4-min early warning)
                    GNN Blast Radius (downstream impact)
                    Qwen3-30B RCA (root cause analysis)
                              │
                              ▼
                   Remediation Pipeline
                         │       │
                    low/med    high/critical
                         │       │
                    auto-exe   HITL Queue → operator approval
                         │       │
                         └───────┘
                              │
                         AI Actions → supervisord XML-RPC
                              │
                         Canary Analysis → auto-rollback if regression
```

---

## Author

**Prasenjit Roychoudhury**  
AWS Community Builder (Year 2) · Claude Certified Architect – Foundations  
TCS · June 2026

---

## Hardware

Built and trained on **AMD Instinct MI300X** (192GB VRAM, ROCm) via AMD Hackathon 2026 notebook environment.

```
rocm-smi --showuse --showmemuse
```

TGNN training peak: **96–97% GPU utilisation · 92–95% VRAM · 23.1 minutes**
