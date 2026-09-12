"""Bounded, read-only Word previews. Never render macros or external relationships."""

from __future__ import annotations

import html
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOC = "application/msword"
WORD_TYPES = {DOCX, DOC}
LIMIT = 8 * 1024 * 1024
NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _paragraph(element: ET.Element) -> str:
    parts = []
    for node in element.iter():
        if node.tag == NS + "t":
            parts.append(html.escape(node.text or ""))
        elif node.tag == NS + "tab":
            parts.append("&#8195;")
        elif node.tag in {NS + "br", NS + "cr"}:
            parts.append("<br>")
    style = element.find(f"{NS}pPr/{NS}pStyle")
    name = style.get(NS + "val", "").lower() if style is not None else ""
    tag = "h" + name[-1] if name in {f"heading{i}" for i in range(1, 7)} else "p"
    return f"<{tag}>{''.join(parts)}</{tag}>"


def _docx(source: BinaryIO) -> str:
    with ZipFile(source) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > LIMIT or info.flag_bits & 1:
            raise ValueError("文档过大或已加密")
        raw = archive.read(info)
    declarations = raw.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
        raise ValueError("文档包含不支持的 XML 声明")
    root = ET.fromstring(raw)
    body = root.find(NS + "body")
    if body is None:
        raise ValueError("没有可读取的正文")
    blocks = []
    for node in body:
        if node.tag == NS + "p":
            blocks.append(_paragraph(node))
        elif node.tag == NS + "tbl":
            rows = []
            for row in node.findall(NS + "tr"):
                cells = [
                    "<td>" + "".join(_paragraph(p) for p in cell.iter(NS + "p")) + "</td>"
                    for cell in row.findall(NS + "tc")
                ]
                rows.append("<tr>" + "".join(cells) + "</tr>")
            blocks.append('<div class="table-scroll"><table>' + "".join(rows) + "</table></div>")
    if not blocks:
        raise ValueError("未找到可显示的文字；文件可能仅含图片")
    return "".join(blocks)


def _doc(source: BinaryIO) -> str:
    data = source.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError("文档超过 8 MB 文字预览限制")
    if not data.startswith(bytes.fromhex("d0cf11e0a1b11ae1")):
        raise ValueError("文件不是可识别的旧版 Word DOC")
    antiword = shutil.which("antiword")
    with tempfile.TemporaryDirectory(prefix="agentpost-word-") as directory:
        path = Path(directory) / "document.doc"
        path.write_bytes(data)
        if antiword:
            command = [antiword, "-m", "UTF-8.txt", "-w", "0", str(path)]
        elif sys.platform == "darwin" and Path("/usr/bin/textutil").is_file():
            command = [
                "/usr/bin/textutil",
                "-convert",
                "txt",
                "-encoding",
                "UTF-8",
                "-stdout",
                str(path),
            ]
        else:
            raise ValueError("服务器的 DOC 阅读组件暂不可用，请联系管理员启用")
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 10
                while process.poll() is None:
                    if time.monotonic() > deadline or output.tell() > LIMIT:
                        raise ValueError("文档解析超时或内容过大")
                    time.sleep(0.05)
                output.seek(0)
                result = output.read(LIMIT + 1)
                if process.returncode or not result.strip() or len(result) > LIMIT:
                    raise ValueError("无法读取正文，文件可能加密、损坏或使用不支持的格式")
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
    return "<pre>" + html.escape(result.decode("utf-8", errors="replace")) + "</pre>"


def word_preview(source: BinaryIO, filename: str, content_type: str) -> bytes:
    try:
        content = _docx(source) if content_type == DOCX else _doc(source)
        note = (
            "阅读预览：保留正文、标题和表格；图片、批注及复杂版式未展示，不显示修订标记。"
            if content_type == DOCX
            else "文字预览：便于直接阅读；图片及原始版式未展示。"
        )
    except (BadZipFile, KeyError, OSError, ValueError, RuntimeError, ET.ParseError) as error:
        content = (
            "<p>"
            + html.escape(str(error) if isinstance(error, ValueError) else "文件可能损坏或无法解析")
            + "。</p>"
        )
        note = "暂时无法预览此文档。原文件仍保留，可关闭后重试或下载。"
    finally:
        source.close()
    return (
        "<!doctype html><html lang=zh-CN><meta charset=utf-8>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<style>body{font:16px/1.7 system-ui;margin:0;padding:16px;"
        "color:#172033;background:#f5f8fc}"
        "h1{font-size:22px;overflow-wrap:anywhere}h2{font-size:20px}h3{font-size:18px}"
        "article{background:white;padding:16px;border:1px solid #c8d7ec;"
        "border-radius:12px;overflow-wrap:anywhere}"
        "pre{white-space:pre-wrap;font:inherit}.table-scroll{overflow-x:auto}table{border-collapse:collapse;min-width:100%}"
        "td{border:1px solid #bbc8d8;padding:8px;min-width:80px}td p{margin:0}.note{color:#526079}"
        "@media(max-width:500px){body{padding:10px}article{padding:12px}}</style>"
        f"<h1>{html.escape(filename)}</h1><p class=note>{note}</p>"
        f"<article>{content}</article></html>"
    ).encode()
