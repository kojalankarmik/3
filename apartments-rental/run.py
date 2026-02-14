import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPS_DIR = ROOT / ".deps"
REQ = ROOT / "requirements.txt"

DEPS_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(DEPS_DIR))  # чтобы импорты искались в .deps


def pip_install(args: list[str]):
    cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-t", str(DEPS_DIR)] + args
    print("[deps] running:", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def ensure_module(module: str, pip_name: str | None = None):
    try:
        __import__(module)
        return
    except ModuleNotFoundError:
        name = pip_name or module
        print(f"[deps] missing {module} -> installing {name}", flush=True)
        pip_install(["--upgrade", name])
        __import__(module)


def ensure_requirements():
    if REQ.exists():
        print(f"[deps] installing from {REQ}", flush=True)
        pip_install(["--upgrade", "-r", str(REQ)])


# 1) ставим всё из requirements (если Deploy-F не ставит — это спасёт)
ensure_requirements()

# 2) гарантируем ключевые модули (чтобы не ловить по одному)
ensure_module("uvicorn")
ensure_module("fastapi")
ensure_module("sqlalchemy")
ensure_module("asyncpg")  # <-- ВАЖНО ДЛЯ postgresql+asyncpg

import uvicorn  # noqa: E402

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
