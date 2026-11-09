"""PURE consent and pre-send byte comparison boundaries."""
from .hashing import sha256


class ApprovalRequired(ValueError):
    code = "E_APPROVAL_REQUIRED"


class ApprovalDenied(ValueError):
    code = "E_APPROVAL_DENIED"


def approve(plan: dict, flags: dict, now: str) -> dict | None:
    approved = plan["approved"]
    if not approved["provider"]["egress"] or plan["status"]["requests_to_send"] == 0:
        return None
    explicit = plan["plan_hash"] in flags.get("yes_hashes", ())
    bare = (flags.get("yes", False) and not approved["threshold_exceeded"]
            and not approved["sensitive_hits"] and approved["cost_known"])
    if not (explicit or bare):
        raise ApprovalRequired("This file requires explicit approval of its Plan.")
    return dict(plan_hash=plan["plan_hash"], approved_at=now, by=flags.get("approved_by") or "cli:--yes")


def parse_yes_lines(text: str) -> list[str]:
    """The CLI owns reading --yes-file; this helper only parses its contents."""
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def verify_raster(unit: dict, raster: bytes) -> None:
    if sha256(raster) != unit["raster_sha256"]:
        raise ApprovalDenied("Raster bytes differ from the approved Plan.")
