"""Canonical UTF-8 serialization and content identity."""
import hashlib
import json
import re
from typing import Mapping


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def key_id(key: Mapping[str, object]) -> str:
    return sha256(canonical_json(dict(key)))


def core_version_supported(version: str) -> bool:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:(?:\.post\d+)?(?:\+[A-Za-z0-9.-]+)?)", version)
    return bool(match and (int(match[1]), int(match[2])) == (0, 3) and int(match[3]) >= 5)
