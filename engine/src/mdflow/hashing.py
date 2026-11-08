"""PURE serialization and hashing boundary (RED phase)."""
from typing import Mapping


def canonical_json(value: object) -> bytes:
    raise NotImplementedError


def sha256(data: bytes) -> str:
    raise NotImplementedError


def key_id(key: Mapping[str, object]) -> str:
    raise NotImplementedError


def core_version_supported(version: str) -> bool:
    raise NotImplementedError
