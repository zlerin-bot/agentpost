"""Safe preview type inference and ZIP directory inspection (no extraction)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import BinaryIO
from zipfile import BadZipFile, ZipFile

_PREVIEW_TYPES = {
    "text/markdown",
    "text/x-markdown",
    "application/markdown",
    "text/plain",
    "text/html",
    "application/json",
    "application/pdf",
    "application/zip",
}
_SUFFIX_TYPES = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".zip": "application/zip",
}


def preview_content_type(content_type: str, filename: str) -> str:
    declared = content_type.partition(";")[0].strip().lower()
    if declared == "application/x-zip-compressed":
        return "application/zip"
    if declared in _PREVIEW_TYPES and declared != "text/plain":
        return declared
    return _SUFFIX_TYPES.get(PurePosixPath(filename.lower()).suffix, declared)


def zip_directory(source: BinaryIO) -> str:
    """List metadata only: never decompress, extract, or follow member paths."""
    try:
        with ZipFile(source) as archive:
            entries = archive.infolist()
            lines = [f"压缩包目录：共 {len(entries)} 项", "仅展示目录，不解压或执行文件。", ""]
            for entry in entries[:200]:
                kind = "文件夹" if entry.is_dir() else "文件"
                encrypted = " · 已加密" if entry.flag_bits & 1 else ""
                lines.append(f"{entry.filename[:500]}  · {kind} · {entry.file_size:,} B{encrypted}")
            if len(entries) > 200:
                lines.append("\n仅显示前 200 项；下载压缩包可查看完整内容。")
            return "\n".join(lines)
    except (BadZipFile, OSError, ValueError, NotImplementedError):
        return "无法读取 ZIP 目录：文件可能损坏或不是 ZIP 格式。请下载原文件核对。"
    finally:
        source.close()
