"""Content-addressed transcription identity and atomic ledger storage."""
from itertools import count
from datetime import datetime
import json
import os
from pathlib import Path
from .hashing import canonical_json, key_id

_SEQUENCE = count(1)


def provider_fingerprint(provider: dict, prompt_version: str) -> str:
    fields = {k: provider[k] for k in ("name", "model", "destination", "egress")}
    fields.update(prompt_version=prompt_version, command_env_names=sorted(set(provider.get("command_env_names", []))))
    return key_id(fields)


def make_key(unit: dict, provider: dict, prompt_version: str) -> dict:
    return dict(raster_sha256=unit["raster_sha256"],
                provider_fingerprint=provider_fingerprint(provider, prompt_version), dpi=unit["dpi"])


def key_id(key: dict) -> str:
    from .hashing import key_id as hash_key
    return hash_key(key)


def validate_entry(entry: object, requested_key: dict, stem: str) -> bool:
    if not isinstance(entry, dict) or type(entry.get("v")) is not int or entry["v"] != 1:
        return False
    try:
        created = datetime.fromisoformat(entry['created'])
        if created.tzinfo is None or created.microsecond:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    key = entry.get("key")
    if not isinstance(key, dict) or key.keys() != requested_key.keys():
        return False
    if any(type(key[k]) is not type(v) or key[k] != v for k, v in requested_key.items()):
        return False
    try:
        if entry.get("key_id") != stem or key_id(key) != stem:
            return False
    except (TypeError, ValueError):
        return False
    if entry.get("status") == "ok":
        return isinstance(entry.get("text"), str) and entry.get("error") is None
    if entry.get("status") == "failed":
        return entry.get("text") is None and isinstance(entry.get("error"), dict)
    return False


class Ledger:
    def __init__(self, cache: Path):
        self.cache = Path(cache)

    def _path(self, key: dict) -> Path:
        identity = key_id(key)
        return self.cache / "units" / identity[:2] / (identity + ".json")

    def lookup(self, key: dict, *, force: bool = False) -> dict:
        """Return {hit, entry, issues}; failed/corrupt/forced entries miss."""
        if force:
            return dict(hit=False, entry=None, issues=[])
        path = self._path(key)
        try:
            entry = json.loads(path.read_bytes())
        except FileNotFoundError:
            return dict(hit=False, entry=None, issues=[])
        except (OSError, ValueError, UnicodeError):
            return dict(hit=False, entry=None, issues=[dict(code="W_CACHE_CORRUPT", message="Cache entry could not be read as JSON.")])
        if not validate_entry(entry, key, path.stem):
            return dict(hit=False, entry=None, issues=[dict(code="W_CACHE_CORRUPT", message="Cache entry failed validation.")])
        return dict(hit=entry["status"] == "ok", entry=entry, issues=[])

    def write(self, entry: dict) -> list[dict]:
        """Publish atomically; return issues without discarding caller's result."""
        temporary = None
        owns_temporary = False
        try:
            key = entry["key"]
            target = self._path(key)
            if not validate_entry(entry, key, target.stem):
                raise ValueError("Invalid ledger entry")
            data = canonical_json(entry) + b"\n"
            for directory in (self.cache, self.cache / "units", target.parent):
                directory.mkdir(mode=0o700 if os.name == "posix" else 0o777, parents=True, exist_ok=True)
                if os.name == "posix":
                    directory.chmod(0o700)
            # O_EXCL also protects concurrent writers and leftovers from older runs.
            while True:
                temporary = target.with_name(target.name + f".tmp-{os.getpid()}-{next(_SEQUENCE)}")
                try:
                    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    owns_temporary = True
                    break
                except FileExistsError:
                    continue
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                identical = target.read_bytes() == data
            except FileNotFoundError:
                identical = False
            if identical:
                temporary.unlink()
            else:
                os.replace(temporary, target)
            return []
        except (OSError, ValueError, TypeError, KeyError):
            return [dict(code="E_CACHE_IO", message="Ledger entry could not be published.")]
        finally:
            if owns_temporary:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
