"""
Cross-platform Developer Experience (DX) runner for the Jus Digital FullStack app.

Usage:
    python scripts/dev.py             # Start Postgres + Alembic + Backend + Frontend
    python scripts/dev.py --backend   # Start Postgres + Alembic + Backend only
    python scripts/dev.py --frontend  # Start Frontend only
    python scripts/dev.py --test      # Run backend pytest suite
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
IS_WINDOWS = os.name == "nt"


def get_venv_binary(name: str) -> Path:
    scripts_dir = BACKEND_DIR / ".venv" / ("Scripts" if IS_WINDOWS else "bin")
    exe_name = f"{name}.exe" if IS_WINDOWS else name
    return scripts_dir / exe_name


def ensure_venv_exists() -> None:
    venv_python = get_venv_binary("python")
    if not venv_python.exists():
        pip_cmd = (
            "backend\\.venv\\Scripts\\pip"
            if IS_WINDOWS
            else "backend/.venv/bin/pip"
        )
        py_cmd = "python" if IS_WINDOWS else "python3"
        print(
            "[ERROR] Virtual environment not found at backend/.venv.\n"
            "Create it first:\n"
            f"  {py_cmd} -m venv backend/.venv\n"
            f"  {pip_cmd} install -r backend/requirements.txt"
        )
        sys.exit(1)


def ensure_frontend_deps() -> None:
    if not (FRONTEND_DIR / "node_modules").exists():
        print(
            "[ERROR] Front-end dependencies not found at frontend/node_modules.\n"
            "Install them first:\n"
            "  cd frontend && npm install"
        )
        sys.exit(1)


def stop_conflicting_containers(services: list[str]) -> None:
    """Stop containerized backend/frontend if running so local ports 8000/5173 are free."""
    if not services or not shutil.which("docker"):
        return
    subprocess.run(
        ["docker", "compose", "stop", *services],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def start_postgres_and_migrate() -> None:
    if not shutil.which("docker"):
        print("[ERROR] Docker CLI not found in PATH. Start Docker Desktop first.")
        sys.exit(1)

    print("[DB] Ensuring PostgreSQL container is running...")
    res = subprocess.run(
        ["docker", "compose", "up", "-d", "postgres"],
        cwd=ROOT_DIR,
        check=False,
    )
    if res.returncode != 0:
        print("[ERROR] Failed to start PostgreSQL. Is Docker Desktop running?")
        sys.exit(res.returncode)

    # Wait until PostgreSQL reports ready inside the container
    print("[DB] Waiting for PostgreSQL healthcheck...")
    for _ in range(30):
        health = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                "pg_isready -U ${POSTGRES_USER:-jusdigital} -d ${POSTGRES_DB:-jusdigital_db}",
            ],
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if health.returncode == 0:
            break
        time.sleep(1)
    else:
        print("[ERROR] PostgreSQL did not become ready in time.")
        sys.exit(1)

    python_bin = get_venv_binary("python")
    print("[DB] Running Alembic migrations (upgrade head)...")
    mig = subprocess.run(
        [str(python_bin), "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=False,
    )
    if mig.returncode != 0:
        print("[ERROR] Alembic migration failed.")
        sys.exit(mig.returncode)


def get_frontend_cmd() -> list[str]:
    """
    Invoke Vite directly via Node when available so Windows does not spawn
    npm.cmd (which prints a spurious 'Terminate batch job (Y/N)?' on Ctrl+C).
    """
    node_bin = shutil.which("node")
    vite_js = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
    if node_bin and vite_js.exists():
        return [node_bin, str(vite_js), "--port", "5173"]

    npm = shutil.which("npm.cmd" if IS_WINDOWS else "npm") or shutil.which("npm")
    if not npm:
        print("[ERROR] 'node'/'npm' not found in PATH. Install Node.js 20+ first.")
        sys.exit(1)
    return [npm, "run", "dev"]


def terminate_process_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except OSError:
            proc.terminate()


def stream_output(proc: subprocess.Popen[str], prefix: str) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"{prefix} {line}", end="", flush=True)


def run_tests() -> int:
    ensure_venv_exists()
    python_bin = get_venv_binary("python")
    print("[TEST] Running backend pytest suite...")
    try:
        res = subprocess.run(
            [str(python_bin), "-m", "pytest", "-v"],
            cwd=BACKEND_DIR,
            check=False,
        )
        return res.returncode
    except KeyboardInterrupt:
        return 0


def run_backend_only() -> int:
    ensure_venv_exists()
    stop_conflicting_containers(["backend"])
    start_postgres_and_migrate()

    python_bin = get_venv_binary("python")
    print("\n[BACKEND] Starting FastAPI at http://localhost:8000 (Docs: http://localhost:8000/docs)\n")
    try:
        res = subprocess.run(
            [str(python_bin), "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
            cwd=BACKEND_DIR,
            check=False,
        )
        return res.returncode
    except KeyboardInterrupt:
        print("\n[BACKEND] Stopped.")
        return 0


def run_frontend_only() -> int:
    ensure_frontend_deps()
    frontend_cmd = get_frontend_cmd()
    stop_conflicting_containers(["frontend"])
    print("\n[FRONTEND] Starting React + Vite at http://localhost:5173\n")
    try:
        res = subprocess.run(frontend_cmd, cwd=FRONTEND_DIR, check=False)
        return res.returncode
    except KeyboardInterrupt:
        print("\n[FRONTEND] Stopped.")
        return 0


def run_all() -> int:
    ensure_venv_exists()
    ensure_frontend_deps()
    frontend_cmd = get_frontend_cmd()
    stop_conflicting_containers(["backend", "frontend"])
    start_postgres_and_migrate()

    python_bin = get_venv_binary("python")
    popen_kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
    }
    if not IS_WINDOWS:
        popen_kwargs["start_new_session"] = True

    print("\n============================================================")
    print("  Jus Digital Dev Server Ready")
    print("  Front-end : http://localhost:5173")
    print("  Back-end  : http://localhost:8000")
    print("  Swagger   : http://localhost:8000/docs")
    print("  Press Ctrl+C to stop both services cleanly.")
    print("============================================================\n")

    backend_proc = subprocess.Popen(
        [str(python_bin), "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND_DIR,
        **popen_kwargs,
    )
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND_DIR,
        **popen_kwargs,
    )

    t_back = threading.Thread(
        target=stream_output, args=(backend_proc, "[BACKEND] "), daemon=True
    )
    t_front = threading.Thread(
        target=stream_output, args=(frontend_proc, "[FRONTEND]"), daemon=True
    )
    t_back.start()
    t_front.start()

    try:
        while True:
            if backend_proc.poll() is not None:
                print("\n[DEV] Back-end process exited. Stopping front-end...")
                return backend_proc.returncode or 0
            if frontend_proc.poll() is not None:
                print("\n[DEV] Front-end process exited. Stopping back-end...")
                return frontend_proc.returncode or 0
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n[DEV] Stopping back-end and front-end...")
        return 0
    finally:
        terminate_process_tree(backend_proc)
        terminate_process_tree(frontend_proc)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Run Jus Digital local development services."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--backend", action="store_true", help="Run only FastAPI + Postgres")
    group.add_argument("--frontend", action="store_true", help="Run only React + Vite")
    group.add_argument("--test", action="store_true", help="Run backend pytest suite")
    args = parser.parse_args()

    if args.test:
        return run_tests()
    if args.backend:
        return run_backend_only()
    if args.frontend:
        return run_frontend_only()
    return run_all()


if __name__ == "__main__":
    raise SystemExit(main())
