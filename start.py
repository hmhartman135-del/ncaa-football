#!/usr/bin/env python3
"""Start the NCAA Football Analytics Platform (backend + frontend)."""

import subprocess
import sys
import os
import time
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
PYTHON = VENV / "bin" / "python"
UVICORN = VENV / "bin" / "uvicorn"
NPM = (
    shutil.which("npm")
    or next((p for p in ["/usr/local/bin/npm", "/opt/homebrew/bin/npm"] if os.path.exists(p)), None)
)

# Docker Desktop on Mac installs to /usr/local/bin or /opt/homebrew/bin;
# those dirs are often missing from the PATH when scripts are run directly.
DOCKER = (
    shutil.which("docker")
    or next((p for p in ["/usr/local/bin/docker", "/opt/homebrew/bin/docker"] if os.path.exists(p)), None)
)

# Ensure common tool paths are always in PATH for subprocesses
_extra_paths = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
BASE_ENV = {**os.environ, "PATH": _extra_paths + ":" + os.environ.get("PATH", "")}


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env or BASE_ENV, check=True)


def free_port(port):
    result = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True)
    pids = result.stdout.strip().split()
    for pid in pids:
        subprocess.run(["kill", "-9", pid], capture_output=True)
    if pids:
        warn(f"Killed stale process(es) on port {port}")


def step(msg):
    print(f"\n\033[1;34m→ {msg}\033[0m")


def ok(msg):
    print(f"\033[1;32m✓ {msg}\033[0m")


def warn(msg):
    print(f"\033[1;33m! {msg}\033[0m")


def die(msg):
    print(f"\033[1;31m✗ {msg}\033[0m")
    sys.exit(1)


# ── 1. Check .env ────────────────────────────────────────────────────────────
step("Checking environment")
env_file = BACKEND / ".env"
if not env_file.exists():
    warn(".env not found — copying from .env.example")
    run(["cp", str(BACKEND / ".env.example"), str(env_file)])
    warn("Add your ANTHROPIC_API_KEY and CFBD_API_KEY to backend/.env then re-run this script.")
    sys.exit(0)

env_text = env_file.read_text()
if "your_anthropic_api_key_here" in env_text:
    die("ANTHROPIC_API_KEY is not set in backend/.env — edit it and re-run.")
if "your_collegefootballdata_api_key_here" in env_text:
    warn("CFBD_API_KEY is not set in backend/.env — the app will start, but data ingestion")
    warn("will fail until you add a free key from https://collegefootballdata.com/key.")
ok(".env looks good")


# ── 2. Docker (postgres + redis) ─────────────────────────────────────────────
step("Starting Docker services (postgres + redis)")
if not DOCKER:
    die("Docker not found. Install Docker Desktop and try again.")
try:
    run([DOCKER, "compose", "up", "postgres", "redis", "-d"], cwd=ROOT)
    ok("Docker services running")
except subprocess.CalledProcessError:
    die("docker compose failed — make sure Docker Desktop is running.")


# ── 3. Python venv ───────────────────────────────────────────────────────────
step("Setting up Python virtual environment")
if not PYTHON.exists():
    run([sys.executable, "-m", "venv", str(VENV)])
    ok("venv created")
else:
    ok("venv already exists")

step("Installing Python dependencies")
run([str(PYTHON), "-m", "pip", "install", "-q", "-r", str(BACKEND / "requirements.txt")])
ok("Python dependencies installed")


# ── 4. Node dependencies ─────────────────────────────────────────────────────
step("Installing Node dependencies")
if not NPM:
    die("npm not found. Install Node.js and try again.")
if not (FRONTEND / "node_modules").exists():
    run([NPM, "install"], cwd=FRONTEND)
    ok("Node dependencies installed")
else:
    ok("node_modules already exists")


# ── 5. Launch backend ────────────────────────────────────────────────────────
free_port(8004)
free_port(3004)
step("Starting FastAPI backend on http://localhost:8004")
backend_env = {**BASE_ENV, "PYTHONPATH": str(BACKEND)}
backend_proc = subprocess.Popen(
    [str(UVICORN), "app.main:app", "--reload", "--port", "8004"],
    cwd=BACKEND,
    env=backend_env,
)
time.sleep(3)
if backend_proc.poll() is not None:
    die("Backend failed to start — check logs above.")
ok(f"Backend running (PID {backend_proc.pid})")


# ── 6. Launch frontend ───────────────────────────────────────────────────────
step("Starting Next.js frontend on http://localhost:3004")
frontend_proc = subprocess.Popen([NPM, "run", "dev"], cwd=FRONTEND, env=BASE_ENV)
time.sleep(3)
if frontend_proc.poll() is not None:
    backend_proc.terminate()
    die("Frontend failed to start — check logs above.")
ok(f"Frontend running (PID {frontend_proc.pid})")


# ── 7. Summary ───────────────────────────────────────────────────────────────
print("\n" + "─" * 50)
print("\033[1;32m🏈 NCAA Football Analytics Platform is running!\033[0m")
print("─" * 50)
print(f"  Frontend  →  http://localhost:3004")
print(f"  Backend   →  http://localhost:8004")
print(f"  API docs  →  http://localhost:8004/docs")
print("─" * 50)
print("  First run? POST /admin/ingest (or just restart) once CFBD_API_KEY is set.")
print("  Press Ctrl+C to stop all services.\n")

import webbrowser
webbrowser.open("http://localhost:3004")

try:
    backend_proc.wait()
except KeyboardInterrupt:
    print("\n\033[1;33mShutting down…\033[0m")
    backend_proc.terminate()
    frontend_proc.terminate()
    backend_proc.wait()
    frontend_proc.wait()
    print("\033[1;32mStopped.\033[0m")
