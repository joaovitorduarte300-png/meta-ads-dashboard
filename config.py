import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ACCESS_TOKEN = "EAANTGkkCPMABRTXnFpAyBEO5XDkN5OAGZATrIiP9oWDjLBYiDbkNHbZBjYi7ZAZBZCKaNCAKy7HasxR9rf6JfSFU4zCseZCEZB9DBMGwF70ZAtitBNgqFCUfjZBUYNTY3PlkEPDeB3GzEXQZBMFbx3Vd1Pl3YD3H0YoFhjqqzRKdWC9bR4qd3apOqennZB1sgZDZD"
BASE_URL = "https://graph.facebook.com/v21.0"

LIMITS_FILE = os.path.join(os.path.dirname(__file__), "..", "limits.json")

DEFAULT_LIMITS = {
    "frequencia_max": 4.0,
    "custo_por_compra_max": 100.0,
    "cpc_max": 5.0,
    "cpm_max": 50.0,
    "gasto_max": None,
}


def load_limits() -> dict:
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_LIMITS.copy()


def save_limits(limits: dict):
    with open(LIMITS_FILE, "w", encoding="utf-8") as f:
        json.dump(limits, f, indent=2, ensure_ascii=False)
