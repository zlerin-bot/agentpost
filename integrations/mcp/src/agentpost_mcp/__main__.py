"""Stdio entrypoint. Standard output is reserved exclusively for MCP JSON-RPC."""

from __future__ import annotations

import logging
import sys
from threading import Event, Thread

from agentpost_sdk import ConfigurationError


def _configure_stderr_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def main() -> None:
    try:
        from agentpost_sdk.auto_upgrade import start_latest

        from agentpost_mcp.config import Settings

        start_latest()
        settings = Settings.from_env()
        _configure_stderr_logging(settings.log_level)

        # Importing the MCP runtime is intentionally delayed so the base AgentPost
        # package remains usable when the optional MCP extra is not installed.
        from agentpost_sdk import __version__
        from agentpost_sdk.auto_upgrade import UPGRADE_STATE

        from agentpost_mcp.server import create_server
        from agentpost_mcp.tools import client_factory

        stopped = Event()

        def report_runtime():
            while not stopped.is_set():
                try:
                    with client_factory(settings)() as client:
                        target = (
                            UPGRADE_STATE.get("target_version", __version__)
                            if UPGRADE_STATE.get("status") == "prepared_reconnect_required"
                            else __version__
                        )
                        client.connector.heartbeat(
                            runtime_version=__version__,
                            installed_version=target,
                            configured_version=(
                                target
                                if UPGRADE_STATE.get("status") == "prepared_reconnect_required"
                                else __version__
                            ),
                        )
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        "Connector heartbeat unavailable type=%s", type(exc).__name__
                    )
                stopped.wait(30)

        health = Thread(target=report_runtime, name="agentpost-runtime-health", daemon=True)
        health.start()
        try:
            create_server(settings).run("stdio")
        finally:
            stopped.set()
    except ImportError as exc:
        sys.stderr.write(
            "AgentPost MCP dependencies are unavailable; install with `agentpost[mcp]`.\n"
        )
        raise SystemExit(2) from exc
    except Exception as exc:
        if isinstance(exc, ConfigurationError):
            sys.stderr.write(f"AgentPost MCP configuration error: {exc}\n")
            raise SystemExit(2) from exc
        logging.getLogger(__name__).error(
            "AgentPost MCP server failed to start type=%s", type(exc).__name__
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
