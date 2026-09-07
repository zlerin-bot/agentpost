from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path


def test_server_package_metadata_import_does_not_require_sdk(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository_root / "src")

    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import agentpost; print(agentpost.__version__)",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0.1.61"


def test_server_sdk_and_mcp_versions_match_release() -> None:
    import agentpost_mcp
    import agentpost_sdk

    import agentpost

    assert {agentpost.__version__, agentpost_sdk.__version__, agentpost_mcp.__version__} == {
        "0.1.61"
    }
    root = Path(__file__).resolve().parents[2]
    for filename in (
        "sdk/typescript/package.json",
        "integrations/openclaw/package.json",
        "integrations/openclaw/openclaw.plugin.json",
        "plugins/agentpost/.codex-plugin/plugin.json",
    ):
        assert (
            json.loads((root / filename).read_text())["version"].split("+")[0]
            == agentpost.__version__
        )
    lock = tomllib.loads((root / "uv.lock").read_text())
    assert (
        next(item for item in lock["package"] if item["name"] == "agentpost")["version"]
        == agentpost.__version__
    )


def test_sdist_carries_the_forced_wheel_bootstrap_source() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    configuration = tomllib.loads((repository_root / "pyproject.toml").read_text())
    forced_sources = configuration["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    sdist_includes = configuration["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]

    assert set(forced_sources).issubset(sdist_includes)


def test_task_is_the_only_active_collaboration_model() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    runtime_roots = [
        "src",
        "sdk",
        "integrations",
        "plugins",
        ".agents",
        "scripts",
    ]
    active_docs = [
        "AGENTS.md",
        "README.md",
        "ARCHITECTURE.md",
        "PROTOCOL.md",
        "SECURITY.md",
        "ROADMAP.md",
        "AGENT_ONBOARDING_PLAN.md",
        "PROJECT_STATUS.md",
        "PROJECT_HANDOFF.md",
        "docs/TASK_CORE_MODEL.md",
        "docs/HUMAN_CONTROL_PLANE.md",
        "docs/AGENT_INTEGRATION_CONTRACT.md",
        "docs/RECIPIENT_RESOLUTION.md",
    ]
    removed_markers = (
        "organization-channel",
        "organization_channel",
        "/organizations/",
        "enterprise_oidc",
        "OrganizationMembership",
    )

    scanned_files = [
        path
        for root in runtime_roots
        for path in (repository_root / root).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]
    scanned_files.extend(repository_root / path for path in active_docs)
    violations = {
        str(path.relative_to(repository_root)): marker
        for path in scanned_files
        for marker in removed_markers
        if marker in path.read_text(encoding="utf-8", errors="ignore")
    }

    assert violations == {}
    assert not list((repository_root / "src/agentpost/organizations").glob("*.py"))
    assert not list((repository_root / "src/agentpost/sso").glob("*.py"))
