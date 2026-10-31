"""Durable files for archive copies: private partials, sidecars and directory flushes."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def open_private_partial(target: Path):
    """A partial next to `target`, private to this copy (concurrent copies never share one)."""
    descriptor, name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".partial", dir=target.parent
    )
    os.fchmod(descriptor, 0o644)  # like other archive files: mkstemp creates 0600
    return os.fdopen(descriptor, "wb"), Path(name)


def write_sidecar(target: Path, metadata: dict[str, Any]) -> None:
    """Atomically write `<target>.json`."""
    sidecar = target.with_suffix(f"{target.suffix}.json")
    temporary = sidecar.with_name(f".{sidecar.name}.partial")
    temporary.unlink(missing_ok=True)
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(sidecar)


def ensure_sidecar(target: Path, metadata: dict[str, Any]) -> None:
    """Write the sidecar of an existing copy only when it is missing."""
    if not target.with_suffix(f"{target.suffix}.json").exists():
        write_sidecar(target, metadata)


def fsync_directory(directory: Path) -> None:
    """Make the renames in `directory` durable before a source copy is deleted."""
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
