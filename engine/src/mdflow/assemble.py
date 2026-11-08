"""PURE assembly, provider-text normalization and exit decisions."""


def assemble(base_body: str, units: list, ledger_entries: dict,
             meta: dict) -> tuple[str, dict]:
    raise NotImplementedError


def output_path(logical_path: str) -> str:
    raise NotImplementedError


def media_issues(base_body: str, units: list) -> list[dict]:
    """PURE warning derivation; assembly inputs are never mutated."""
    raise NotImplementedError


def esc_text(text: str) -> str:
    raise NotImplementedError


def esc_attr(text: str) -> str:
    raise NotImplementedError


def esc_head(text: str) -> str:
    raise NotImplementedError


def postprocess_text(text: str) -> tuple[str, list]:
    raise NotImplementedError


def publication_decision(existing: str, new: str, *, force: bool = False) -> dict:
    """Return {write, issues}; caller owns filesystem access."""
    raise NotImplementedError


def exit_code(codes: list[str], *, startup: bool = False,
              cancelled: bool = False) -> int:
    raise NotImplementedError
