"""
connection.py - Centralized Milvus/pymilvus connection setup for vdbbench.

Every vdbbench module that opens a Milvus connection must go through
``open_connection`` so the gRPC message-size limits are applied consistently.

Background (issue #572)
-----------------------
pymilvus' gRPC client defaults ``max_receive_message_length`` to 256 MiB
(268435456 bytes). For wide vectors (e.g. 1M x 1536-dim float32) the FLAT
ground-truth copy path can make Milvus return a single response larger than
that limit, raising::

    StatusCode.RESOURCE_EXHAUSTED, grpc: trying to send message larger than
    max (393631413 vs. 268435456)

``load_vdb`` and ``compact_and_watch`` already raised the ceiling to
``514_983_574`` (~491 MiB), but ``simple_bench``, ``enhanced_bench``,
``collection_mgr``, ``list_collections`` and ``mpi_wrapper`` were still on the
256 MiB default. Routing all of them through this single helper removes that
inconsistency and prevents the limit from silently regressing again.

The configs (e.g. ``configs/1m_diskann.yaml``) declare
``max_receive_message_length: 514_983_574``; ``MAX_GRPC_MESSAGE_LENGTH`` here is
the single source of truth those literals should match.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pymilvus import connections

# Single source of truth for the gRPC message-size ceiling (~491 MiB). Matches
# the value used in load_vdb.py, compact_and_watch.py, the Milvus backend, and
# the max_receive_message_length / max_send_message_length keys in configs/*.yaml.
MAX_GRPC_MESSAGE_LENGTH = 514_983_574


def _looks_like_local_db_path(value: object) -> bool:
    """Return whether *value* names a local Milvus Lite database file."""
    if value is None:
        return False

    text = str(value)
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "tcp://", "grpc://", "unix://")):
        return False

    # Only infer a local path from host when it has path syntax. A remote
    # hostname such as ``milvus.db`` is still a valid host and must continue
    # through the host/port connection path. Explicit ``uri=`` values are
    # handled separately below and may use a bare filename.
    return lowered.endswith(".db") and (
        Path(text).is_absolute() or "/" in text or "\\" in text
    )


def _normalize_local_db_path(value: str) -> str:
    """Resolve a local database path and create its parent directory."""
    path = Path(value).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def open_connection(
    alias: str = "default",
    host: str = "127.0.0.1",
    port: str = "19530",
    *,
    uri: Optional[str] = None,
    max_message_length: int = MAX_GRPC_MESSAGE_LENGTH,
) -> None:
    """
    Open a Milvus connection with raised gRPC send/receive message limits.

    This is a thin wrapper around ``pymilvus.connections.connect`` that always
    supplies ``max_receive_message_length`` and ``max_send_message_length`` so
    large FLAT ground-truth responses do not trip the 256 MiB client default
    (see issue #572).

    Parameters
    ----------
    alias:
        Connection alias to register (e.g. ``"default"``, ``"flat_setup"``).
    host, port:
        Milvus server address.  For backwards compatibility, a local path
        ending in ``.db`` passed as ``host`` is treated as a Milvus Lite URI
        when it has path syntax (for example ``./runtime/milvus.db``).
        Hostnames such as ``milvus.db`` remain remote hostnames.
    uri:
        Explicit Milvus URI.  A local ``.db`` path starts Milvus Lite through
        PyMilvus; an HTTP/TCP URI connects to a remote Milvus server.
    max_message_length:
        Override for the gRPC message-size ceiling in bytes. Defaults to
        ``MAX_GRPC_MESSAGE_LENGTH``.
    """
    local_uri = uri
    if local_uri is None and _looks_like_local_db_path(host):
        local_uri = str(host)

    message_options = {
        "max_receive_message_length": max_message_length,
        "max_send_message_length": max_message_length,
    }

    if local_uri is not None:
        explicit_local_path = (
            str(local_uri).lower().endswith(".db")
            and not str(local_uri).lower().startswith(
                ("http://", "https://", "tcp://", "grpc://", "unix://")
            )
        )
        if explicit_local_path or _looks_like_local_db_path(local_uri):
            local_uri = _normalize_local_db_path(local_uri)

        connections.connect(alias=alias, uri=local_uri, **message_options)
        return

    connections.connect(
        alias=alias,
        host=host,
        port=str(port),
        **message_options,
    )
