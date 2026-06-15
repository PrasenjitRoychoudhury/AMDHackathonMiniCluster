"""Generate supervisord.conf with a dynamic node split (run once before supervisord)."""
import os, multiprocessing

BASE = os.path.dirname(os.path.abspath(__file__))
N = multiprocessing.cpu_count()
half = N // 2
NODE1 = f"0-{half-1}"          # e.g. 0-55 on the 112-core box
NODE2 = f"{half}-{N-1}"        # e.g. 56-111

SERVICES = [  # (name, port, node)
    ("payments",  7001, 1),
    ("auth",      7002, 1),
    ("checkout",  7003, 2),
    ("fraud",     7004, 2),
]

def prog(name, cores, command, env=""):
    envline = f"environment={env}\n" if env else ""
    return f"""[program:{name}]
command=taskset -c {cores} {command}
directory={BASE}
autorestart=true
startsecs=2
stopwaitsecs=5
stdout_logfile={BASE}/logs/{name}.log
stderr_logfile={BASE}/logs/{name}.err
{envline}"""

parts = [f"""[supervisord]
nodaemon=false
logfile={BASE}/logs/supervisord.log
pidfile={BASE}/supervisord.pid

[inet_http_server]
port=127.0.0.1:9001

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=http://127.0.0.1:9001
"""]

# redis on node-1 (the dependency hub)
parts.append(prog("redis", NODE1,
    "redis-server --port 6379 --save '' --appendonly no --protected-mode yes --bind 127.0.0.1"))

for name, port, node in SERVICES:
    cores = NODE1 if node == 1 else NODE2
    parts.append(prog(name, cores, "python3 app.py",
        env=f'SERVICE_NAME="{name}",PORT="{port}",NODE="node-{node}"'))

# loadgen + collector unpinned-ish: park them on node-2's last few cores
tail = f"{N-4}-{N-1}"
parts.append(prog("loadgen", tail, "python3 loadgen.py"))
parts.append(prog("collector", tail, "python3 collector.py"))

os.makedirs(f"{BASE}/logs", exist_ok=True)
with open(f"{BASE}/supervisord.conf", "w") as f:
    f.write("\n".join(parts))

print(f"wrote supervisord.conf | {N} cores | node-1: {NODE1} | node-2: {NODE2}")
print("services: redis(n1) payments:7001(n1) auth:7002(n1) checkout:7003(n2) fraud:7004(n2) + loadgen + collector")
