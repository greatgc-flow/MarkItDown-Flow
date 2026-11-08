"""PURE diagnostics redaction; environment and home are explicit inputs."""


def redact(message: str, env: dict, home: str, *, authorization: str = "") -> str:
    raise NotImplementedError
