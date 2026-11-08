"""PURE approved/status Plan boundary."""
from copy import deepcopy
from decimal import Decimal, localcontext
from fnmatch import fnmatchcase
from .hashing import key_id
from .ledger import make_key, provider_fingerprint

STATUSES = ("eligible", "cached", "skipped_low_priority", "oversize", "render_failed", "unsupported_media_format")
UNIT_FIELDS = frozenset("kind source_id page status raster_sha256 dpi mime bytes priority priority_core also media_file".split())


def plan(selected: dict, render_meta: dict, lookup: dict,
         provider_meta: dict, options: dict) -> dict:
    units = [{k: deepcopy(v) for k, v in unit.items() if k in UNIT_FIELDS} for unit in selected["units"]]
    rendering = render_meta.get("units", {})
    if isinstance(rendering, list):
        rendering = {u["source_id"]: u for u in rendering}
    counts = dict.fromkeys(STATUSES, 0)
    keys, hit_keys, unit_keys = set(), set(), {}
    prompt = options.get("prompt_version", "p1")
    oversize = bool(selected.get("oversize"))
    for unit in units:
        evidence = rendering.get(unit["source_id"], render_meta.get(unit["source_id"], {}))
        if isinstance(evidence, dict):
            unit.update({k: deepcopy(v) for k, v in evidence.items() if k in UNIT_FIELDS})
        status = "oversize" if oversize else unit["status"]
        observation = lookup.get(unit["source_id"])
        hit = bool(observation.get("hit")) if isinstance(observation, dict) else observation in ("hit", True)
        if status in {"eligible", "cached"}:
            key = key_id(make_key(unit, provider_meta, prompt))
            keys.add(key)
            unit_keys[unit["source_id"]] = key
            if hit:
                hit_keys.add(key)
            unit["status"] = "eligible"
        else:
            counts[status] += 1
            unit.update(status=status, raster_sha256=None, mime=None, bytes=None)
    # A hit for any occurrence of a Key applies to every occurrence of that Key.
    for key in unit_keys.values():
        counts["cached" if key in hit_keys else "eligible"] += 1
    misses = keys - hit_keys
    provider = {k: deepcopy(provider_meta[k]) for k in
                ("name", "model", "egress", "cost_hint", "max_batch", "retries", "destination")}
    provider.update(proxy=options.get("proxy"), command_env_names=sorted(set(provider_meta.get("command_env_names", []))))
    maximum = len(keys) * (1 + provider["retries"])
    cost = None
    if provider["cost_hint"] is not None:
        with localcontext() as context:
            context.prec = max(28, len(str(provider["cost_hint"])) + len(str(maximum)) + 10)
            cost = format(Decimal(provider["cost_hint"]) * maximum, ".6f")
    source = {k: deepcopy(options["file"][k]) for k in ("path", "sha256", "bytes", "format")}
    threshold = options.get("approve_threshold", 20)
    classification = {k: deepcopy(options["classification"][k]) for k in ("route", "need", "label", "action", "decision", "coverage_state")}
    approved = dict(file=source, classification=classification, provider=provider,
        provider_fingerprint=provider_fingerprint(provider_meta, prompt), prompt_version=prompt,
        dpi=options.get("dpi", 200), units=units, units_total=len(units), keys_unique=len(keys),
        max_requests=maximum, est_max_cost=cost, cost_known=cost is not None,
        approve_threshold=threshold, threshold_exceeded=len(keys) > threshold,
        sensitive_hits=[p for p in options.get("sensitive", []) if fnmatchcase(source["path"].casefold(), p.casefold())],
        oversize=oversize)
    status = dict(units=counts, requests_to_send=len(misses),
                  uninspected_pages=render_meta.get("uninspected_pages", selected.get("uninspected_pages", options["classification"].get("uninspected_pages", 0))),
                  frames_total=render_meta.get("frames_total") if source["format"] in {"png", "jpeg", "gif", "bmp", "tiff", "webp"} else None)
    return dict(v=1, approved=approved, status=status, plan_hash=key_id(approved))
