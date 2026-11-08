"""PURE candidate-to-unit selection boundary."""


def select(classification: dict, options: dict) -> dict:
    raise NotImplementedError


def media_identity(candidate_id: str, format: str, member_hashes: dict,
                   triage_media: list) -> str | None:
    """Resolve h12 from supplied evidence; HWP5 never opens a ZIP."""
    raise NotImplementedError
