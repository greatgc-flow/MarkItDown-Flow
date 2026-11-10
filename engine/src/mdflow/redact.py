"""PURE diagnostics redaction; environment and home are explicit inputs."""
import re

# Parts of an env name split on non-alphanumerics. Weak words count only as a whole part, so KEYBOARD, MONKEY_*
# and TOKENIZERS_* are not secrets; a part ending in a strong word is (PGPASSWORD, GHTOKEN, OPENAIKEY).
SECRET_WORDS = frozenset("KEY KEYS PASS AUTH PAT TOKENS SECRETS CREDENTIALS APIKEYS PASSWORDS".split())
SECRET_SUFFIXES = ("PASSWORD", "PASSWD", "PASSPHRASE", "TOKEN", "SECRET", "APIKEY", "AIKEY", "SECRETKEY", "ACCESSKEY",
                   "PRIVATEKEY", "CREDENTIAL")
NON_SECRET_PARTS = frozenset({"TIKTOKEN"})  # ends in TOKEN, but names tiktoken settings (TIKTOKEN_CACHE_DIR)
# Settings, not secrets: replacing them would garble ordinary text ("page 12" with a *_TOKEN=1 flag).
NON_SECRET_VALUES = frozenset("yes no true false on off".split())


def is_secret_name(name: str) -> bool:
    upper = name.upper()
    if upper == "AUTH_SOCK" or upper.endswith("_AUTH_SOCK"):  # agent sockets such as SSH_AUTH_SOCK
        return False
    return any(part not in NON_SECRET_PARTS and (part in SECRET_WORDS or part.endswith(SECRET_SUFFIXES))
               for part in re.split(r"[^A-Z0-9]+", upper))


def secret_values(env: dict) -> set:
    return {value for name, value in env.items() if is_secret_name(name) and isinstance(value, str) and value}


def redact(message: str, env: dict, home: str, *, authorization: str = "") -> str:
    secrets = {value for value in secret_values(env)
               if len(value) >= 4 and not value.isdigit() and value.lower() not in NON_SECRET_VALUES}
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
