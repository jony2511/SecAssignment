"""
DDoS Attack Simulation — Stage C
===================================
Multiple independent worker processes simulating distributed bot clients.

Each process acts as an independent "bot" originating from a separate
source, all targeting the same server simultaneously.

Safety: Target is hardcoded to 127.0.0.1 only.
        Total request count and duration are bounded.
"""

import sys
import multiprocessing as mp
import time
import requests

URL = "http://127.0.0.1:5000/work"
NUM_BOTS = 5                    # independent worker processes
DEFAULT_REQUESTS_PER_BOT = 30   # each bot sends this many
INTER_REQUEST_DELAY = 0.01      # minimal delay for maximum pressure


def bot_worker(args):
    """
    Simulate one DDoS bot.
    Each bot runs in its own process — truly independent.
    Returns: (bot_id, success_count, busy_count, error_count, latencies)
    """
    bot_id, requests_count, stop_time = args
    success = 0
    busy = 0
    errors = 0
    latencies = []

    req_idx = 0
    while True:
        if stop_time is not None:
            if time.perf_counter() >= stop_time:
                break
        else:
            if req_idx >= requests_count:
                break

        req_idx += 1
        start = time.perf_counter()
        try:
            r = requests.get(URL, timeout=3)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

            if r.status_code == 200:
                success += 1
            elif r.status_code == 503:
                busy += 1
            else:
                errors += 1

        except requests.RequestException:
            errors += 1

        time.sleep(INTER_REQUEST_DELAY)

    return (bot_id, success, busy, errors, latencies)


def run_ddos(duration_seconds=None):
    total_req_display = NUM_BOTS * DEFAULT_REQUESTS_PER_BOT if duration_seconds is None else f"Continuous ({duration_seconds}s)"

    print("=" * 60)
    print("   STAGE C — DDoS ATTACK SIMULATION (Distributed)")
    print("=" * 60)
    print(f"  Target:            {URL}")
    print(f"  Simulated bots:    {NUM_BOTS} independent processes")
    if duration_seconds:
        print(f"  Mode:              Sustained bot swarm for {duration_seconds}s")
    else:
        print(f"  Requests per bot:  {DEFAULT_REQUESTS_PER_BOT}")
    print(f"  Total requests:    {total_req_display}")
    print(f"  Delay per bot:     {INTER_REQUEST_DELAY}s between requests")
    print("-" * 60)
    print("  Launching bot swarm...\n")

    # Reset server stats
    try:
        requests.get("http://127.0.0.1:5000/reset-stats", timeout=2)
    except Exception:
        pass

    start_time = time.perf_counter()
    stop_time = (start_time + duration_seconds) if duration_seconds else None

    bot_args = [
        (bot_id, DEFAULT_REQUESTS_PER_BOT, stop_time)
        for bot_id in range(1, NUM_BOTS + 1)
    ]

    # Launch independent processes
    with mp.Pool(NUM_BOTS) as pool:
        results = pool.map(bot_worker, bot_args)

    total_time = time.perf_counter() - start_time

    # ── Per-bot breakdown ──
    print("  " + "-" * 56)
    print(f"  {'Bot':>6} | {'200 OK':>8} | {'503 Busy':>10} | "
          f"{'Errors':>8} | {'Avg ms':>8}")
    print("  " + "-" * 56)

    total_success = 0
    total_busy = 0
    total_errors = 0
    all_latencies = []

    for bot_id, ok, busy, err, lats in results:
        total_success += ok
        total_busy += busy
        total_errors += err
        all_latencies.extend(lats)

        avg_lat = sum(lats) / len(lats) if lats else 0
        print(f"  Bot-{bot_id:>2} | {ok:>8} | {busy:>10} | "
              f"{err:>8} | {avg_lat:>7.1f}")

    # ── Aggregate summary ──
    total = total_success + total_busy + total_errors

    print("\n" + "=" * 60)
    print("   DDoS ATTACK RESULTS (AGGREGATE)")
    print("=" * 60)
    print(f"  Total requests sent:   {total}")
    print(f"  HTTP 200 (accepted):   {total_success}")
    print(f"  HTTP 503 (rejected):   {total_busy}")
    print(f"  Errors/timeouts:       {total_errors}")
    print(f"  Duration:              {total_time:.2f}s")
    if total_time > 0:
        print(f"  Request rate:          {total/total_time:.1f} req/s")

    if all_latencies:
        avg = sum(all_latencies) / len(all_latencies)
        print(f"  Average latency:       {avg:.1f} ms")
        print(f"  Min latency:           {min(all_latencies):.1f} ms")
        print(f"  Max latency:           {max(all_latencies):.1f} ms")

    if total > 0:
        reject_pct = total_busy / total * 100
        print(f"  Rejection rate:        {reject_pct:.1f}%")

    print("=" * 60)

    # Set server into persistent OVERLOADED mode for browser demonstration
    try:
        requests.get("http://127.0.0.1:5000/set-mode?mode=overloaded", timeout=2)
    except Exception:
        pass

    # Fetch server stats
    try:
        r = requests.get("http://127.0.0.1:5000/stats", timeout=2)
        if r.ok:
            print(f"\n  Server stats: {r.json()}")
    except Exception:
        pass

    print("\n  ========================================================")
    print("  DDoS simulation complete! Bot swarm deactivated.")
    print("  Server is currently in OVERLOADED state.")
    print("  Open http://127.0.0.1:5000 to see the RED OVERLOADED dashboard.")
    print("  When ready to verify recovery, click 'RESTORE / RECOVER' on the page or run baseline.py.")
    print("  ========================================================")


if __name__ == "__main__":
    dur = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].replace("--duration=", "").replace("--duration", "")
        if not arg and len(sys.argv) > 2:
            arg = sys.argv[2]
        try:
            dur = float(arg)
        except ValueError:
            if "sustained" in sys.argv[1].lower():
                dur = 15.0
    run_ddos(duration_seconds=dur)
