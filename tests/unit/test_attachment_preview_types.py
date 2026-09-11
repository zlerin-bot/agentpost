import io
from zipfile import ZipFile

from agentpost.attachments.preview import preview_content_type, zip_directory


def test_filename_fallback_and_declared_safe_type():
    assert preview_content_type("application/octet-stream", "中文.MD") == "text/markdown"
    assert preview_content_type("text/plain; charset=UTF-8", "report.markdown") == "text/markdown"
    assert (
        preview_content_type("application/octet-stream", "report.md.exe")
        == "application/octet-stream"
    )
    assert preview_content_type("application/pdf", "report.md") == "application/pdf"
    assert preview_content_type("application/x-zip-compressed", "file") == "application/zip"


def test_zip_directory_never_extracts_and_limits_listing():
    source = io.BytesIO()
    with ZipFile(source, "w") as archive:
        archive.writestr("../<script>file.md", "never decompress this")
        for i in range(201):
            archive.writestr(f"folder/{i}.txt", "")
    source.seek(0)
    result = zip_directory(source)
    assert "共 202 项" in result
    assert "../<script>file.md" in result
    assert "never decompress this" not in result
    assert "仅显示前 200 项" in result
    assert source.closed
    invalid = io.BytesIO(b"not zip")
    assert "无法读取 ZIP" in zip_directory(invalid)
    assert invalid.closed
