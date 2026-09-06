"""Non-secret upload receipts keep CLI retries bound to the same attachments."""

import hashlib
import json
import os
from pathlib import Path

from agentpost_sdk.auto_upgrade import _install_lock
from agentpost_sdk.errors import ConfigurationError


def prepared_attachments(
    *,
    scope: str,
    key: str,
    task_id: str,
    subject: str,
    body: str,
    paths: list[Path],
    upload,
    home: Path | None = None,
) -> list[str]:
    fingerprint = hashlib.sha256(
        json.dumps([scope, task_id, subject, body], ensure_ascii=False).encode()
    )
    for path in paths:
        with path.open("rb") as source:
            file_digest = hashlib.file_digest(source, "sha256").hexdigest()
        fingerprint.update(json.dumps([path.name, file_digest]).encode())
    digest = fingerprint.hexdigest()
    root = home or Path.home() / ".agentpost" / "send-receipts"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = hashlib.sha256((scope + "\0" + key).encode()).hexdigest()
    path = root / f"{name}.json"
    guard = _install_lock(root / f"{name}.lock")
    if guard is None:
        raise ConfigurationError("send retry is already preparing attachments")
    try:
        if path.exists():
            saved = json.loads(path.read_text())
            if saved["fingerprint"] != digest:
                raise ConfigurationError("idempotency key already used for different content")
            return saved["attachment_ids"]
        ids = upload(paths)
        temporary = path.with_suffix(".tmp")
        with temporary.open("w") as output:
            os.chmod(temporary, 0o600)
            json.dump({"fingerprint": digest, "attachment_ids": ids}, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        return ids
    finally:
        guard.close()
