import json
from types import SimpleNamespace

import pytest
from agentpost_sdk import auto_upgrade as upgrade


@pytest.fixture
def release(monkeypatch):
    monkeypatch.setenv("AGENTPOST_SERVER", "https://agentpost.me")
    monkeypatch.setenv("AGENTPOST_PROFILE", "codex:existing-identity")
    monkeypatch.delenv("AGENTPOST_HOST", raising=False)
    monkeypatch.delenv("AGENTPOST_AUTO_UPGRADE", raising=False)
    return SimpleNamespace(version="0.9.0", wheel_sha256="a" * 64)


def test_verified_runtime_reused_without_install(tmp_path, release):
    runtime = tmp_path / "runtimes/codex/0.9.0"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "bin/agentpost-mcp").touch()
    (runtime / ".agentpost-verified.json").write_text(
        json.dumps({"version": release.version, "sha256": release.wheel_sha256})
    )
    result = upgrade.prepare_upgrade(
        fetch=lambda: release,
        install=lambda *a, **k: pytest.fail("must not reinstall"),
        home=tmp_path,
    )
    assert result["status"] == "ready"
    assert result["executable"].endswith("/codex/0.9.0/bin/agentpost-mcp")


def test_existing_unverified_runtime_never_overwritten(tmp_path, release):
    runtime = tmp_path / "runtimes/codex/0.9.0"
    runtime.mkdir(parents=True)
    sentinel = runtime / "running-environment"
    sentinel.write_text("keep")
    result = upgrade.prepare_upgrade(
        fetch=lambda: release, install=lambda *a, **k: pytest.fail("must not mutate"), home=tmp_path
    )
    assert result["status"] == "existing_runtime_unverified"
    assert sentinel.read_text() == "keep"


def test_no_downgrade_or_identity_repair(tmp_path, release):
    release.version = "0.0.1"
    result = upgrade.prepare_upgrade(fetch=lambda: release, install=lambda: None, home=tmp_path)
    assert result["status"] == "current"
    assert list(tmp_path.iterdir()) == []


def test_custom_origin_not_used_for_automatic_code_install(monkeypatch, release):
    monkeypatch.setenv("AGENTPOST_SERVER", "https://untrusted.example")
    result = upgrade.prepare_upgrade(fetch=lambda: pytest.fail("no network"), install=lambda: None)
    assert result["status"] == "custom_server_requires_release_policy"


def test_active_install_lock_does_not_interrupt_existing_process(tmp_path, release):
    root = tmp_path / "runtimes/codex"
    root.mkdir(parents=True)
    lock = root / ".0.9.0.install.lock"
    guard = upgrade._install_lock(lock)
    assert guard is not None
    result = upgrade.prepare_upgrade(fetch=lambda: release, install=lambda: None, home=tmp_path)
    assert result["status"] == "upgrade_in_progress"
    assert lock.exists()
    guard.close()


def test_fresh_install_verified_before_publication(tmp_path, release, monkeypatch):
    monkeypatch.setattr(
        upgrade.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="0.9.0")
    )

    def install(release, *, runtime):
        (runtime / "bin").mkdir(parents=True)
        (runtime / "bin/agentpost-mcp").touch()
        (runtime / "bin/python").touch()

    result = upgrade.prepare_upgrade(fetch=lambda: release, install=install, home=tmp_path)
    assert result["status"] == "ready"
    marker = tmp_path / "runtimes/codex/0.9.0/.agentpost-verified.json"
    assert json.loads(marker.read_text())["sha256"] == release.wheel_sha256


def test_failed_import_never_marks_runtime_verified(tmp_path, release, monkeypatch):
    monkeypatch.setattr(upgrade.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))

    def install(release, *, runtime):
        (runtime / "bin").mkdir(parents=True)
        (runtime / "bin/agentpost-mcp").touch()

    with pytest.raises(RuntimeError, match="runtime_import_failed"):
        upgrade.prepare_upgrade(fetch=lambda: release, install=install, home=tmp_path)
    assert not list(tmp_path.rglob(".agentpost-verified.json"))


def test_background_preparation_publishes_pointer_not_process_switch(tmp_path, monkeypatch):
    executable = tmp_path / "runtimes/codex/0.9.0/bin/agentpost-mcp"
    executable.parent.mkdir(parents=True)
    monkeypatch.setattr(
        upgrade,
        "prepare_upgrade",
        lambda: {"status": "ready", "target_version": "0.9.0", "executable": str(executable)},
    )
    monkeypatch.setattr(upgrade.os, "execve", lambda *a: pytest.fail("do not kill current session"))
    upgrade._background_prepare()
    assert upgrade.UPGRADE_STATE["status"] == "prepared_reconnect_required"
    assert json.loads((tmp_path / "runtimes/codex/current.json").read_text()) == {
        "version": "0.9.0"
    }


def test_failed_fresh_install_can_retry_without_touching_existing_runtime(tmp_path, release):
    def interrupted(release, *, runtime):
        runtime.mkdir(parents=True)
        (runtime / "partial-install").write_text("failure evidence")
        raise RuntimeError("network failed")

    for _ in range(2):
        with pytest.raises(RuntimeError, match="network failed"):
            upgrade.prepare_upgrade(fetch=lambda: release, install=interrupted, home=tmp_path)
    root = tmp_path / "runtimes/codex"
    assert not (root / release.version).exists()
    assert len(list(root.glob(".failed-*/partial-install"))) == 2
