"""
Official TypeSafe JEV API Client Factory for Tetris AI.
Directory: jevTetris/
Connects to official production endpoint: https://api.typesafe.ai
"""

import os
from typesafe_sdk import TypeSafeClient

# Automatically load .env if present in project directory
def _load_env_file():
    env_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    ]
    for p in env_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break

_load_env_file()

API_KEY = os.environ.get("TYPESAFE_API_KEY", "")
BASE_URL = os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
MODEL_NAME = os.environ.get("TYPESAFE_MODEL", "jev-latest")


def get_official_jev_client() -> TypeSafeClient:
    """Return standard TypeSafeClient configured for official Jev service."""
    if not API_KEY:
        print("⚠️ Warning: TYPESAFE_API_KEY environment variable is not set!")
        print("   Please set it via: export TYPESAFE_API_KEY='your-key' or add it to .env")

    return TypeSafeClient(
        api_key=API_KEY,
        base_url=BASE_URL
    )
