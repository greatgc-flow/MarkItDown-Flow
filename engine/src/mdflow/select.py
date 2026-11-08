"""PURE candidate-to-unit selection boundary."""
import re


def select(classification: dict, options: dict) -> dict:
    units, groups = [], {}
    for c in classification.get("candidates_unique", []):
        identity = c["id"]
        page_unit = c["kind"] == "page" or identity == "image" or bool(re.fullmatch(r"f[1-9]\d*", identity))
        if page_unit:
            page = c["page"] if c["kind"] == "page" else 1 if identity == "image" else int(identity[1:])
            group = ("page", identity)
        else:
            page = None
            h12 = media_identity(identity, options.get("file", {}).get("format", ""),
                                 options.get("media_hashes", {}), options.get("triage_media", []))
            group = ("media", h12 or identity)
        if group in groups:
            u = groups[group]
            if not page_unit and identity != u["source_id"]:
                ids = sorted(set([u["source_id"], *u["also"], identity]))
                u["source_id"], u["also"] = ids[0], ids[1:]
            if c["priority"] == "normal":
                u.update(priority="normal", priority_core="high")
            continue
        u = dict(kind="page" if page_unit else "media", source_id=identity, page=page,
                 status="eligible", raster_sha256=None, dpi=options.get("dpi", 200) if c["kind"] == "page" else 0,
                 mime=None, bytes=None, priority=c["priority"], priority_core=c["priority_core"])
        if not page_unit:
            u.update(also=[], media_file=None)
        groups[group] = u
        units.append(u)
    units.sort(key=lambda u: (0, u["page"], u["source_id"]) if u["kind"] == "page" else (1, u["source_id"]))
    oversize = len(units) > options.get("max_units", 200)
    for u in units:
        if oversize:
            u["status"] = "oversize"
        elif options.get("min_priority", "low") == "normal" and u["priority"] == "low":
            u["status"] = "skipped_low_priority"
    return dict(units=units, oversize=oversize)


def media_identity(candidate_id: str, format: str, member_hashes: dict,
                   triage_media: list) -> str | None:
    """Resolve h12 from supplied evidence; HWP5 never opens a ZIP."""
    if format == "hwp":
        for media in triage_media:
            if media.get("id") == candidate_id:
                digest = media.get("payload_sha256")
                return digest[:12] if isinstance(digest, str) else None
        return None
    digest = member_hashes.get(candidate_id)
    return digest[:12] if isinstance(digest, str) else None
