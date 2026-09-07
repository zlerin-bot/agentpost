"""Verified, host-isolated upgrades at an MCP process boundary.

Never rewrites credentials or an existing environment. Existing MCP sessions keep
running; the next host connection starts the selected release.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path

from agentpost_sdk import __version__

HOSTS = {"codex", "workbuddy", "doubao_work", "openclaw", "hermes", "manus"}


def host_name() -> str | None:
    host = os.environ.get("AGENTPOST_HOST", "")
    if not host:
        host = os.environ.get("AGENTPOST_PROFILE", "").split(":", 1)[0]
    return host if host in HOSTS else None


def _install_lock(path: Path):
    """OS releases the advisory lock on crashes; never leave a stale PID lock."""
    stream = path.open("a+b")
    path.chmod(0o600)
    try:
        if os.name == "nt":
            import msvcrt

            if path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return stream
    except OSError:
        stream.close()
        return None


def prepare_upgrade(*, fetch=None, install=None, home: Path | None = None) -> dict:
    host = host_name()
    if os.environ.get("AGENTPOST_AUTO_UPGRADE", "1") == "0":
        return {"status": "disabled", "runtime_version": __version__}
    if not host:
        return {"status": "host_unknown", "runtime_version": __version__}
    if os.environ.get("AGENTPOST_SERVER", "").rstrip("/") != "https://agentpost.me":
        return {"status": "custom_server_requires_release_policy", "runtime_version": __version__}
    if fetch is None or install is None:
        from agentpost.onboarding_bootstrap import current_platform, ensure_runtime, fetch_release

        fetch = fetch or (lambda: fetch_release(host_name=host, platform_name=current_platform()))
        install = install or ensure_runtime
    release = fetch()
    current = tuple(int(n) for n in __version__.split("."))
    target = tuple(int(n) for n in release.version.split("."))
    if target <= current:
        return {"status": "current", "runtime_version": __version__}
    root = (home or Path.home() / ".agentpost") / "runtimes" / host
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime = root / release.version
    lock = root / f".{release.version}.install.lock"
    guard = _install_lock(lock)
    if guard is None:
        return {"status": "upgrade_in_progress", "target_version": release.version}
    try:
        suffix = "Scripts" if os.name == "nt" else "bin"
        executable = (
            runtime / suffix / ("agentpost-mcp.exe" if os.name == "nt" else "agentpost-mcp")
        )
        marker = runtime / ".agentpost-verified.json"
        if runtime.exists():
            # Never pip-install into a directory another process may be using.
            if not marker.is_file() or not executable.is_file():
                return {"status": "existing_runtime_unverified", "target_version": release.version}
            metadata = json.loads(marker.read_text())
            if metadata != {"version": release.version, "sha256": release.wheel_sha256}:
                return {"status": "runtime_digest_changed", "target_version": release.version}
        else:
            install(release, runtime=runtime)
            if not executable.is_file():
                raise RuntimeError("missing_mcp_executable")
            probe = subprocess.run(
                [
                    str(runtime / suffix / ("python.exe" if os.name == "nt" else "python")),
                    "-I",
                    "-c",
                    "import agentpost_mcp.server, agentpost_sdk",
                ],
                capture_output=True,
                timeout=20,
                check=False,
            )
            if probe.returncode:
                raise RuntimeError("runtime_import_failed")
            marker.write_text(
                json.dumps({"version": release.version, "sha256": release.wheel_sha256})
            )
            marker.chmod(0o600)
        return {"status": "ready", "target_version": release.version, "executable": str(executable)}
    finally:
        guard.close()


UPGRADE_STATE: dict = {"status": "not_checked", "runtime_version": __version__}


def _background_prepare() -> None:
    UPGRADE_STATE["last_checked_at"] = datetime.now(UTC).isoformat()
    UPGRADE_STATE.pop("reason", None)
    UPGRADE_STATE.pop("target_version", None)
    try:
        result = prepare_upgrade()
        UPGRADE_STATE.update(result)
        if result["status"] == "ready":
            pointer = Path(result["executable"]).parent.parent.parent / "current.json"
            temporary = pointer.with_name(f".current-{os.getpid()}.json")
            temporary.write_text(json.dumps({"version": result["target_version"]}))
            temporary.chmod(0o600)
            os.replace(temporary, pointer)
            UPGRADE_STATE["status"] = "prepared_reconnect_required"
    except Exception as exc:
        sys.stderr.write(f"AgentPost auto-upgrade deferred ({type(exc).__name__}).\n")
        UPGRADE_STATE["status"] = "upgrade_deferred"
        UPGRADE_STATE["reason"] = type(exc).__name__


def _watch_releases() -> None:
    while True:
        _background_prepare()
        threading.Event().wait(3600)


def start_latest() -> dict:
    """Start cached verified release immediately; stage future updates off the RPC path."""
    host = host_name()
    enabled = os.environ.get("AGENTPOST_AUTO_UPGRADE", "1") != "0"
    official = os.environ.get("AGENTPOST_SERVER", "").rstrip("/") == "https://agentpost.me"
    if enabled and official and host:
        root = Path.home() / ".agentpost" / "runtimes" / host
        try:
            version = json.loads((root / "current.json").read_text())["version"]
            import re

            if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
                raise ValueError("invalid_cached_version")
            if tuple(map(int, version.split("."))) > tuple(map(int, __version__.split("."))):
                runtime = root / version
                marker = json.loads((runtime / ".agentpost-verified.json").read_text())
                if marker["version"] != version or len(marker["sha256"]) != 64:
                    raise ValueError("invalid_verified_marker")
                executable = runtime / (
                    "Scripts/agentpost-mcp.exe" if os.name == "nt" else "bin/agentpost-mcp"
                )
                os.execve(str(executable), [str(executable)], os.environ.copy())
        except (OSError, ValueError, KeyError, TypeError):
            pass  # The original runtime remains the rollback/fallback entrypoint.
        UPGRADE_STATE["status"] = "checking_in_background"
        threading.Thread(target=_watch_releases, name="agentpost-upgrade", daemon=True).start()
    else:
        UPGRADE_STATE["status"] = "disabled" if not enabled else "release_policy_required"
    return UPGRADE_STATE.copy()
