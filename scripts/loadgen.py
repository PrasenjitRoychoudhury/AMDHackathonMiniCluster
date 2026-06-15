"""MiniCluster load generator — realistic mixed traffic with a gentle wave."""
import asyncio, math, random, time
import httpx

SERVICES = {
    "payments": 7001,
    "auth":     7002,
    "checkout": 7003,
    "fraud":    7004,
}
BASE_RPS = 4.0          # cluster-wide requests/sec at trough
WAVE_AMPL = 3.0         # extra rps at peak of the wave
WAVE_PERIOD_S = 600     # 10-minute "diurnal" wave

WEIGHTS = {"payments": 0.35, "checkout": 0.30, "auth": 0.20, "fraud": 0.15}

async def hit(client, name, port):
    try:
        await client.get(f"http://127.0.0.1:{port}/work", timeout=3.0)
    except Exception:
        pass  # failures show up in service-side error metrics

async def main():
    async with httpx.AsyncClient() as client:
        t0 = time.time()
        while True:
            phase = (time.time() - t0) % WAVE_PERIOD_S / WAVE_PERIOD_S
            rps = BASE_RPS + WAVE_AMPL * (0.5 + 0.5 * math.sin(2 * math.pi * phase))
            name = random.choices(list(WEIGHTS), weights=WEIGHTS.values())[0]
            asyncio.create_task(hit(client, name, SERVICES[name]))
            await asyncio.sleep(1.0 / rps)

if __name__ == "__main__":
    asyncio.run(main())
