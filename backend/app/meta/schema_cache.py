"""
Meta Layer: Schema Cache
========================
Hash-based persistent cache for generated Pydantic write/read schemas.

At startup ``load_all_entities()`` builds a Pydantic model per entity via
``create_model()``.  With 100+ entities this adds ~0.5–1 s to cold-start.
This module stores the generated models as pickle blobs keyed by the MD5
hash of the entity's JSON file, so unchanged entities skip ``create_model()``
on subsequent restarts.

Cache layout (on disk)::

    backend/.schema_cache/
        <entity_name>_write_<md5>.pkl    ← pickled write BaseModel class
        <entity_name>_read_<md5>.pkl     ← pickled read  BaseModel class

Invalidation is automatic: the hash is derived from the file content, so
editing the JSON silently produces a different key and the old file is ignored
(and cleaned up lazily).

Usage (called from app.entities.__init__.py)::

    from app.meta.schema_cache import load_or_build_schemas

    write_cls, read_cls = load_or_build_schemas(entity_meta, json_path)
"""
from __future__ import annotations

import hashlib
import logging
import pickle
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Cache directory relative to this file: backend/app/meta/ → backend/.schema_cache/
_CACHE_DIR = Path(__file__).parent.parent.parent / ".schema_cache"
_CACHE_VERSION = "v1"  # bump to invalidate all cached schemas on breaking changes


def _file_md5(path: Path) -> str:
    """Return the MD5 hex-digest of a file's contents."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def _cache_path(entity_name: str, kind: str, file_hash: str) -> Path:
    return _CACHE_DIR / f"{entity_name}_{kind}_{_CACHE_VERSION}_{file_hash}.pkl"


def _try_load(path: Path) -> Optional[type[BaseModel]]:
    """Return the pickled class from *path*, or ``None`` on any error."""
    try:
        with path.open("rb") as fh:
            cls = pickle.load(fh)
        # Sanity check: must be a Pydantic BaseModel subclass
        if isinstance(cls, type) and issubclass(cls, BaseModel):
            return cls
    except Exception as exc:
        logger.debug("Schema cache miss (load error) for %s: %s", path.name, exc)
    return None


def _try_save(path: Path, cls: type[BaseModel]) -> None:
    """Pickle *cls* to *path*, silently ignoring errors."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(cls, fh, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as exc:
        logger.debug("Schema cache write failed for %s: %s", path.name, exc)


def _evict_stale(entity_name: str, current_hash: str) -> None:
    """Remove .pkl files for *entity_name* that do NOT match *current_hash*."""
    if not _CACHE_DIR.exists():
        return
    pattern = f"{entity_name}_*_{_CACHE_VERSION}_*.pkl"
    for stale in _CACHE_DIR.glob(pattern):
        if current_hash not in stale.name:
            try:
                stale.unlink()
            except OSError:
                pass


def load_or_build_schemas(
    entity_meta,
    json_path: Path,
) -> tuple[type[BaseModel], type[BaseModel]]:
    """
    Return ``(write_schema, read_schema)`` for *entity_meta*.

    1. Compute MD5 of *json_path*.
    2. If both ``.pkl`` files exist and load cleanly → return cached schemas.
    3. Otherwise build fresh schemas, persist them, and return.

    Falls back gracefully to building without caching if the cache directory
    is not writable (e.g. read-only container filesystem).
    """
    from app.meta.schema_factory import build_write_schema, build_read_schema

    # Fast path: no JSON file → can't hash, build directly
    if not json_path or not json_path.exists():
        return build_write_schema(entity_meta), build_read_schema(entity_meta)

    file_hash = _file_md5(json_path)
    _evict_stale(entity_meta.name, file_hash)

    write_path = _cache_path(entity_meta.name, "write", file_hash)
    read_path = _cache_path(entity_meta.name, "read", file_hash)

    write_cls = _try_load(write_path)
    read_cls = _try_load(read_path)

    if write_cls is not None and read_cls is not None:
        logger.debug("Schema cache hit: %s", entity_meta.name)
        return write_cls, read_cls

    # Cache miss — build and persist
    write_cls = build_write_schema(entity_meta)
    read_cls = build_read_schema(entity_meta)

    _try_save(write_path, write_cls)
    _try_save(read_path, read_cls)

    return write_cls, read_cls
