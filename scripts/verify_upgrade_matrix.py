"""Opt-in offline wheel installation proof for six host-specific runtime directories.

Uses temporary directories, synthetic old version and shared local test dependencies.
Does not read credentials, update host configurations, or prove native host registration.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import sysconfig
import tempfile
import venv
import zipfile
from pathlib import Path
from types import SimpleNamespace

from agentpost_sdk import auto_upgrade

root = Path(tempfile.mkdtemp(prefix="agentpost-real-upgrade-"))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--wheel", type=Path, required=True)
args = parser.parse_args()
wheel = args.wheel.resolve()
version = wheel.name.split("-")[1]
sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
with zipfile.ZipFile(wheel) as z:
    bootstrap_path = root / "bootstrap.py"
    bootstrap_path.write_bytes(z.read("agentpost/onboarding_bootstrap.py"))
spec = importlib.util.spec_from_file_location("candidate_bootstrap", bootstrap_path)
bootstrap = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bootstrap
spec.loader.exec_module(bootstrap)
release = SimpleNamespace(version=version, wheel_url=wheel.as_uri(), wheel_sha256=sha)
site = Path(sysconfig.get_path("purelib"))
relative_site = f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"


def create(runtime):
    venv.EnvBuilder(with_pip=True).create(runtime)
    (runtime / relative_site / "test-dependencies.pth").write_text(str(site) + "\n")


def runner(args, **kwargs):
    if "install" in args:
        args = [
            *args[: args.index("install") + 1],
            "--no-deps",
            "--no-index",
            *args[args.index("install") + 1 :],
        ]
    return subprocess.run(args, **kwargs)


def install(release, *, runtime):
    bootstrap.ensure_runtime(release, runtime=runtime, runner=runner, create_venv=create)


os.environ["AGENTPOST_SERVER"] = "https://agentpost.me"
auto_upgrade.__version__ = "0.0.0"  # Simulated old launcher; real wheel version remains intact.
for host in sorted(auto_upgrade.HOSTS):
    os.environ["AGENTPOST_HOST"] = host
    result = auto_upgrade.prepare_upgrade(fetch=lambda: release, install=install, home=root)
    assert result["status"] == "ready", result
    executable = Path(result["executable"])
    probe = subprocess.run(
        [
            str(executable.with_name("python")),
            "-I",
            "-c",
            "import agentpost_sdk, agentpost_mcp.server; print(agentpost_sdk.__version__)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert probe.stdout.strip() == version
    print(
        json.dumps(
            {
                "host": host,
                "status": "isolated_wheel_installed_and_imported",
                "runtime_version": probe.stdout.strip(),
                "sha256": sha,
            }
        ),
        flush=True,
    )
print("EVIDENCE_ROOT=" + str(root))
