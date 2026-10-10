# Copyright 2025-2026 mrveiss
# SPDX-License-Identifier: Apache-2.0
# AutoBot - AI-Powered Automation Platform
# Author: mrveiss
"""Atomic in-place text rewrite that preserves the file's mode (#14546, #15580)."""

import os
import tempfile
from pathlib import Path


def write_atomically(file_path: Path, content: str) -> None:
    """Replace ``file_path``'s contents with ``content`` via temp-then-rename.

    A write that fails or is interrupted partway through would otherwise leave a truncated
    file on disk. The new content goes to a sibling temp file first and is renamed into place
    only once fully written; the rename is atomic on one filesystem, and a crash before it
    leaves the original untouched. The original permission bits are kept.
    """
    original_mode = file_path.stat().st_mode
    fd, tmp_name = tempfile.mkstemp(dir=file_path.parent, prefix=f".{file_path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
        os.chmod(tmp_name, original_mode)
        os.replace(tmp_name, file_path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
