"""Key identity, validation and store boundary; owned entirely by core."""
from pathlib import Path


def provider_fingerprint(provider: dict, prompt_version: str) -> str:
    raise NotImplementedError


def make_key(unit: dict, provider: dict, prompt_version: str) -> dict:
    raise NotImplementedError


def key_id(key: dict) -> str:
    raise NotImplementedError


def validate_entry(entry: object, requested_key: dict, stem: str) -> bool:
    raise NotImplementedError


class Ledger:
    def __init__(self, cache: Path):
        raise NotImplementedError

    def lookup(self, key: dict, *, force: bool = False) -> dict:
        """Return {hit, entry, issues}; failed/corrupt/forced entries miss."""
        raise NotImplementedError

    def write(self, entry: dict) -> list[dict]:
        """Publish atomically; return issues without discarding caller's result."""
        raise NotImplementedError
