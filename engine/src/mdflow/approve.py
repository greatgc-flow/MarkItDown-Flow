"""PURE consent and pre-send byte comparison boundaries."""


class ApprovalRequired(ValueError):
    code = "E_APPROVAL_REQUIRED"


class ApprovalDenied(ValueError):
    code = "E_APPROVAL_DENIED"


def approve(plan: dict, flags: dict, now: str) -> dict | None:
    raise NotImplementedError


def parse_yes_lines(text: str) -> list[str]:
    """The CLI owns reading --yes-file; this helper only parses its contents."""
    raise NotImplementedError


def verify_raster(unit: dict, raster: bytes) -> None:
    raise NotImplementedError
