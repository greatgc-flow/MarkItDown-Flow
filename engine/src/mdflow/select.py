"""PURE candidate-to-unit selection boundary."""
import re


def select(classification: dict, options: dict) -> dict:
    units, groups = [], {}
    if classification.get('action') not in {None, 'convert_and_ocr'}:
        return dict(units=[], oversize=False)
    for c in classification.get("candidates_unique", []):
        identity = c["id"]
        fmt = options.get('file', {}).get('format', '')
        evidence = next((m for m in options.get('triage_media', []) if m['id'] == identity), {})
        payload_kind = evidence.get('payload_kind') if fmt == 'hwp' else None
        unsupported = payload_kind == 'stored_ole_stream' or (
            'core:unsupported_media' in classification.get('reasons', []) and
            evidence.get('ext', '').lower() in {'wmf', 'emf', 'wmz', 'emz'})
        page_unit = c["kind"] == "page" or identity == "image" or bool(re.fullmatch(r"f[1-9]\d*", identity))
        if page_unit:
            page = c["page"] if c["kind"] == "page" else 1 if identity == "image" else int(identity[1:])
            group = ("page", identity)
        else:
            page = None
            digest = media_digest(identity, options.get("file", {}).get("format", ""),
                                 options.get("media_hashes", {}), options.get("triage_media", []))
            # Equal content does not erase a different rendering/refusal policy.
            group = ("media", digest or identity, unsupported)
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
            if fmt == 'hwp':
                u['_payload_kind'] = payload_kind
            if unsupported:
                u['_unsupported_media'] = True
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
    digest = media_digest(candidate_id, format, member_hashes, triage_media)
    return digest[:12] if digest else None


def media_digest(candidate_id: str, format: str, member_hashes: dict,
                 triage_media: list) -> str | None:
    """Full digest is unit identity; h12 is only a collision-checked filename."""
    if format == "hwp":
        for media in triage_media:
            if media.get("id") == candidate_id:
                digest = media.get("payload_sha256")
                return digest if isinstance(digest, str) else None
        return None
    digest = member_hashes.get(candidate_id)
    return digest if isinstance(digest, str) else None
