"""
Baseline measurement — Stage A
================================
Sends a small number of sequential requests to the server
and records latency and success rate under normal conditions.

This establishes the "before attack" reference point.
"""

import time
import requests

URL = "http://127.0.0.1:5000/work"
TOTAL_REQUESTS = 20
INTER_REQUEST_DELAY = 0.15  # seconds between requests (gentle load)

def run_baseline():
    print("=" * 56)
    print("   STAGE A — BASELINE MEASUREMENT")
    print("=" * 56)
    print(f"  Target:     {URL}")
    print(f"  Requests:   {TOTAL_REQUESTS}")
    print(f"  Delay:      {INTER_REQUEST_DELAY}s between requests")
    print("-" * 56)

    # Reset server stats and mode before baseline
    try:
        requests.get("http://127.0.0.1:5000/set-mode?mode=normal", timeout=2)
        requests.get("http://127.0.0.1:5000/reset-stats", timeout=2)
    except Exception:
        pass

    latencies = []
    success = 0
    busy = 0
    errors = 0

    for i in range(1, TOTAL_REQUESTS + 1):
        start = time.perf_counter()
        try:
            r = requests.get(URL, timeout=3)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

            if r.status_code == 200:
                success += 1
                status_label = "200 OK"
            elif r.status_code == 503:
                busy += 1
                status_label = "503 BUSY"
            else:
                errors += 1
                status_label = f"{r.status_code} ???"

            print(f"  [{i:02d}/{TOTAL_REQUESTS}]  HTTP {status_label}  "
                  f"latency={elapsed_ms:.1f}ms")

        except requests.RequestException as e:
            errors += 1
            print(f"  [{i:02d}/{TOTAL_REQUESTS}]  ERROR: {e}")

        time.sleep(INTER_REQUEST_DELAY)

    # ── Summary ──
    print("\n" + "=" * 56)
    print("   BASELINE RESULTS")
    print("=" * 56)
    print(f"  Total requests sent:   {TOTAL_REQUESTS}")
    print(f"  HTTP 200 (success):    {success}")
    print(f"  HTTP 503 (busy):       {busy}")
    print(f"  Errors/timeouts:       {errors}")

    if latencies:
        avg = sum(latencies) / len(latencies)
        min_l = min(latencies)
        max_l = max(latencies)
        print(f"  Average latency:       {avg:.1f} ms")
        print(f"  Min latency:           {min_l:.1f} ms")
        print(f"  Max latency:           {max_l:.1f} ms")

    print(f"  Success rate:          {success/TOTAL_REQUESTS*100:.1f}%")
    print("=" * 56)

    # Fetch server-side stats
    try:
        r = requests.get("http://127.0.0.1:5000/stats", timeout=2)
        if r.ok:
            server_stats = r.json()
            print(f"\n  Server stats: {server_stats}")
    except Exception:
        pass


if __name__ == "__main__":
    run_baseline()
