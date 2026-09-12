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


def test_word_preview_preserves_text_tables_and_escapes_untrusted_content():
    from agentpost.attachments.word_preview import DOCX, word_preview

    source = io.BytesIO()
    with ZipFile(source, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
<w:r><w:t>中文报告 &lt;script&gt;</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格内容</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>""",
        )
    source.seek(0)
    result = word_preview(source, "<report>.docx", DOCX).decode()
    assert "<h1>中文报告 &lt;script&gt;</h1>" in result
    assert "<td><p>表格内容</p></td>" in result
    assert "&lt;report&gt;.docx" in result
    assert source.closed
    assert preview_content_type("application/octet-stream", "报告.DOCX") == DOCX
    assert preview_content_type("application/octet-stream", "旧.doc") == "application/msword"
    assert preview_content_type("application/octet-stream", "报告.pdf") == "application/pdf"


def test_word_preview_handles_corruption_and_rejects_xml_entities():
    from agentpost.attachments.word_preview import DOC, DOCX, word_preview

    for kind in [DOC, DOCX]:
        assert "暂时无法预览" in word_preview(io.BytesIO(b"bad"), "test", kind).decode()
    for encoding in ["utf-8", "utf-16"]:
        source = io.BytesIO()
        with ZipFile(source, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<!DOCTYPE x [<!ENTITY a "unsafe">]><x>&a;</x>'.encode(encoding),
            )
        source.seek(0)
        result = word_preview(source, "file.docx", DOCX).decode()
        assert "不支持的 XML 声明" in result
        assert "unsafe" not in result


def test_word_preview_bounds_expanded_xml_before_reading(monkeypatch):
    from agentpost.attachments import word_preview as module

    monkeypatch.setattr(module, "LIMIT", 32)
    source = io.BytesIO()
    with ZipFile(source, "w") as archive:
        archive.writestr("word/document.xml", "x" * 1000)
    source.seek(0)
    result = module.word_preview(source, "large.docx", module.DOCX).decode()
    assert "文档过大" in result
    assert "x" * 100 not in result
    assert source.closed
