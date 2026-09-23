"""
CyberShield NOC — Controlled DoS/DDoS Simulation Server
=========================================================
A deliberately capacity-limited Flask web server for demonstrating
how request floods affect service availability.

Safety: Bound to 127.0.0.1 only. Never expose to external networks.
"""

from flask import Flask, jsonify, render_template, request
import threading
import time

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ── Deliberate capacity constraints ──────────────────────────────
CAPACITY = 4          # max concurrent /work handlers
PROCESSING_TIME = 0.3  # seconds of simulated CPU-bound work per request

slots = threading.BoundedSemaphore(CAPACITY)

# ── Live statistics & state ──────────────────────────────────────
stats_lock = threading.Lock()
stats = {
    "accepted": 0,
    "rejected": 0,
    "total": 0,
    "active_workers": 0,
    "last_rejected_time": 0,
    "mode": "normal",  # "normal" or "overloaded"
    "start_time": time.time()
}


# ── Routes ───────────────────────────────────────────────────────

@app.get("/")
def home():
    """Serve the CyberShield NOC dashboard."""
    return render_template("index.html")


@app.get("/work")
def work():
    """
    Simulated expensive endpoint.
    If server mode is "overloaded" OR capacity slots are full:
      → return 503 immediately
    Otherwise:
      → process for 0.3s and return 200
    """
    with stats_lock:
        stats["total"] += 1
        is_manual_overload = (stats["mode"] == "overloaded")

    if is_manual_overload:
        with stats_lock:
            stats["rejected"] += 1
            stats["last_rejected_time"] = time.time()
        return jsonify({
            "status": "busy",
            "code": 503,
            "message": "Server is OVERLOADED — request rejected"
        }), 503

    acquired = slots.acquire(blocking=False)

    if not acquired:
        with stats_lock:
            stats["rejected"] += 1
            stats["last_rejected_time"] = time.time()
        return jsonify({
            "status": "busy",
            "code": 503,
            "message": "Server capacity full (4/4 workers) — request rejected"
        }), 503

    with stats_lock:
        stats["active_workers"] += 1

    try:
        time.sleep(PROCESSING_TIME)
        with stats_lock:
            stats["accepted"] += 1
        return jsonify({
            "status": "ok",
            "code": 200,
            "message": "Request processed successfully"
        }), 200
    finally:
        with stats_lock:
            stats["active_workers"] = max(0, stats["active_workers"] - 1)
        slots.release()


@app.get("/health")
def health():
    """
    Health check endpoint:
    Returns 503 if server is overloaded, or 200 if healthy.
    """
    with stats_lock:
        is_overloaded = (stats["mode"] == "overloaded") or (stats["active_workers"] >= CAPACITY)
        active = stats["active_workers"]
        total_rej = stats["rejected"]

    if is_overloaded:
        return jsonify({
            "status": "overloaded",
            "code": 503,
            "active_workers": active,
            "capacity": CAPACITY,
            "total_rejected": total_rej,
            "message": "SERVER OVERLOADED — service degraded under attack"
        }), 503

    return jsonify({
        "status": "healthy",
        "code": 200,
        "active_workers": active,
        "capacity": CAPACITY,
        "uptime_seconds": round(time.time() - stats["start_time"], 1)
    }), 200


@app.get("/stats")
def get_stats():
    """Return live server statistics as JSON."""
    with stats_lock:
        now = time.time()
        active = stats["active_workers"]
        is_overloaded = (stats["mode"] == "overloaded") or (active >= CAPACITY)

        return jsonify({
            "accepted": stats["accepted"],
            "rejected": stats["rejected"],
            "total": stats["total"],
            "active_workers": active,
            "capacity": CAPACITY,
            "status": "overloaded" if is_overloaded else "healthy",
            "mode": stats["mode"],
            "uptime_seconds": round(now - stats["start_time"], 1)
        })


@app.route("/set-mode", methods=["GET", "POST"])
def set_mode():
    """Set server mode: 'normal' or 'overloaded'."""
    new_mode = request.args.get("mode") or request.form.get("mode") or "normal"
    with stats_lock:
        stats["mode"] = new_mode
        if new_mode == "overloaded":
            stats["last_rejected_time"] = time.time()
    return jsonify({"status": "mode_updated", "mode": new_mode})


@app.get("/reset-stats")
def reset_stats():
    """Reset counters between experiment stages."""
    with stats_lock:
        stats["accepted"] = 0
        stats["rejected"] = 0
        stats["total"] = 0
        stats["active_workers"] = 0
        stats["last_rejected_time"] = 0
        stats["mode"] = "normal"
        stats["start_time"] = time.time()
    return jsonify({"status": "stats_reset"})


# ── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 52)
    print("   CYBERSHIELD NOC — Security Lab Server")
    print("=" * 52)
    print(f"  Address:        http://127.0.0.1:5000")
    print(f"  Capacity:       {CAPACITY} concurrent workers")
    print(f"  Processing:     {PROCESSING_TIME}s per /work request")
    print(f"  Health check:   http://127.0.0.1:5000/health")
    print(f"  Live stats:     http://127.0.0.1:5000/stats")
    print("=" * 52)
    print("  Waiting for connections...\n")

    app.run(host="127.0.0.1", port=5000, threaded=True)
