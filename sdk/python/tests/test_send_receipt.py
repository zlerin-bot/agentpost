import pytest
from agentpost_sdk.errors import ConfigurationError
from agentpost_sdk.send_receipt import prepared_attachments


def test_retry_reuses_upload_ids_and_rejects_changed_bytes(tmp_path):
    source = tmp_path / "report.txt"
    source.write_text("original")
    calls = []

    def upload(paths):
        calls.append(paths)
        return ["attachment-one"]

    args = dict(
        scope="server|profile",
        key="same-key",
        task_id="task",
        subject="s",
        body="b",
        paths=[source],
        upload=upload,
        home=tmp_path / "receipts",
    )
    assert prepared_attachments(**args) == ["attachment-one"]
    assert prepared_attachments(**args) == ["attachment-one"]
    assert len(calls) == 1
    source.write_text("changed")
    with pytest.raises(ConfigurationError, match="different content"):
        prepared_attachments(**args)
    assert len(calls) == 1
    receipt = next((tmp_path / "receipts").glob("*.json"))
    assert "original" not in receipt.read_text()
    assert receipt.stat().st_mode & 0o777 == 0o600
