"""PURE diagnostics redaction; environment and home are explicit inputs."""
import re


def redact(message: str, env: dict, home: str, *, authorization: str = "") -> str:
    secrets = {value for name, value in env.items()
               if any(part in name.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
               and isinstance(value, str) and value}
    if authorization:
        secrets.add(authorization)
    replacements = dict.fromkeys(secrets, "***")
    if home and home not in replacements:
        replacements[home] = "~"
    if replacements:
        pattern = "|".join(re.escape(value) for value in sorted(replacements, key=len, reverse=True))
        message = re.sub(pattern, lambda match: replacements[match[0]], message)
    message = re.sub(r"(?i)(Authorization\s*:\s*)[^\r\n]+", r"\1***", message)
    return message[:500]
