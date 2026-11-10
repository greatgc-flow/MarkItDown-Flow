"""PURE diagnostics redaction; environment and home are explicit inputs."""
import re

# Whole components of an env name (split on non-alphanumerics), so KEYBOARD or TOKENIZERS_* are not secrets.
SECRET_WORDS = frozenset("KEY KEYS APIKEY TOKEN TOKENS SECRET SECRETS PASSWORD PASSWD PASS AUTH CREDENTIAL "
                         "CREDENTIALS PAT".split())


def is_secret_name(name: str) -> bool:
    return any(part in SECRET_WORDS for part in re.split(r"[^A-Z0-9]+", name.upper()))


def secret_values(env: dict) -> set:
    return {value for name, value in env.items() if is_secret_name(name) and isinstance(value, str) and value}


def redact(message: str, env: dict, home: str, *, authorization: str = "") -> str:
    secrets = secret_values(env)
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
