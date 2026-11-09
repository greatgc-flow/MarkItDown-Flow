"""Sequential discovery-to-publication pipeline (SPEC sections 4 and 7).

Stages retain ownership of their contracts. Invocation state here is limited to
discovery, consent flags, progress, and results needed to assemble the report.
"""

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
from typing import Sequence

from . import __version__, approve, assemble, classify, convert, ledger, plan, providers
from . import render, report, select, sniff_io, transcribe, triage, write
from . import core_guard, runtime_temp

DEFAULTS = dict(provider="none", model=None, dpi=200, min_priority="low", max_units=200,
                approve_threshold=20, force=False, prompt_version="p1", max_bytes=209715200,
                max_pixels=50000000, zip_depth=3, zip_entries=1000, zip_total_bytes=1073741824,
                sensitive=(), yes=False, yes_hashes=(), approved_by=None, progress="none",
                preconvert_legacy=False, preconvert_timeout_s=60)
_CLASS_FIELDS = ("route", "need", "label", "action", "decision", "coverage_state")


def tools() -> dict[str, str]:
    result = {"mdflow": __version__}
    for name in ("markitdown-gc", "pypdfium2", "pillow"):
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = "unavailable"
    return result


class Cancelled(BaseException):
    """Escapes stage Exception handlers and subprocess.run's child cleanup."""


@contextmanager
def cancellation():
    previous = {}
    interrupted = False

    def stop(signum, frame):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise Cancelled()

    if threading.current_thread() is threading.main_thread():
        signals = (signal.SIGBREAK,) if os.name == "nt" else (signal.SIGINT, signal.SIGTERM)
        for number in signals:
            previous[number] = signal.signal(number, stop)
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def _issue(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _source_bytes(path: Path | str, sniff: dict, maximum: int) -> bytes:
    """One bounded snapshot with the authoritative Sniff identity, never a new identity."""
    data = bytearray()
    with open(path, 'rb') as stream:
        while chunk := stream.read(65536):
            data.extend(chunk)
            if len(data) > maximum:
                raise OSError('Source changed after Sniff.')
    if len(data) != sniff['bytes'] or sha256(data).hexdigest() != sniff['sha256']:
        raise OSError('Source changed after Sniff.')
    return bytes(data)


def _empty_file(sniff: dict) -> dict:
    c = classify.classify(sniff, None)
    return dict(path=sniff["path"], root=sniff["root"], sha256=sniff["sha256"],
                bytes=sniff["bytes"], format=sniff["format"], **{k: c[k] for k in _CLASS_FIELDS},
                units=dict(total=0, eligible=0, cached=0, transcribed=0, pending=0, failed=0),
                requests=dict(to_send=0, sent=0, ok=0, failed=0), placements=0,
                issues=deepcopy(sniff["issues"]), outputs=[], plan_hash=None, consent=None, triage=None)


class _MeasuredProvider:
    """Count wire attempts, including the built-in HTTP provider's retries."""

    def __init__(self, provider: object):
        self.provider = provider
        self.meta = provider.meta
        self.calls = 0

    def transcribe(self, unit: dict, raster: bytes, prompt: object) -> dict:
        before = getattr(self.provider, 'requests_sent', None)
        try:
            return self.provider.transcribe(unit, raster, prompt)
        finally:
            self.calls += 1 if before is None else self.provider.requests_sent - before


class _Pipeline:
    def __init__(self, options: dict, provider: object, now: datetime | None):
        self.options = options
        self.provider = _MeasuredProvider(provider)
        self.fixed_now = now
        self.cache = Path(options["cache"])
        self.out = Path(options["out"]) if options.get("out") else None
        self.store = ledger.Ledger(self.cache)
        self.tools = tools()
        self.plan_only = bool(options.get("_plan_only"))
        self.plans = []
        self.memo = {}
        self.matched_hashes = set()
        self.deferred = []

    def now(self) -> datetime:
        return self.fixed_now or datetime.now(timezone.utc).replace(microsecond=0)

    def emit(self, ev: str, **fields) -> None:
        if self.options["progress"] == "jsonl":
            report.emit_progress(dict(v=1, ev=ev, ts=self.now().isoformat(timespec="seconds"), **fields), sys.stderr)

    def stage(self, file: str, name: str, function, *args, **kwargs):
        start = time.monotonic()
        value = function(*args, **kwargs)
        self.emit("stage", file=file, stage=name, state="end", ms=int((time.monotonic() - start) * 1000))
        return value

    def issues(self, entry: dict, issues: Sequence[dict]) -> None:
        for raw in issues:
            item = report.diagnostics(raw)
            if item not in entry["issues"]:
                entry["issues"].append(item)
                self.emit("warning" if item["code"].startswith("W_") else "error", file=entry["path"],
                          code=item["code"], message=item["message"])

    def discover(self, roots: Sequence[Path]) -> tuple[list[dict], list[dict]]:
        excluded = [self.cache]
        if self.out is not None:
            excluded.append(self.out)
        found = sniff_io.discover(roots, exclude=excluded)
        sources, outputs = [], set()
        for discovered in found["files"]:
            sn = sniff_io.sniff(discovered["path"], logical=discovered["logical"], root=discovered["root"],
                                **{k: self.options[k] for k in ("max_bytes", "zip_entries", "zip_total_bytes")})
            sn["issues"].extend(deepcopy(discovered["issues"]))
            source = dict(sniff=sn, runtime=discovered["path"])
            sources.append(source)
            if sn["route"] == "CONTAINER" and not any(i["code"].startswith("E_") for i in sn["issues"]):
                try:
                    source['data'] = _source_bytes(discovered['path'], sn, self.options['max_bytes'])
                except OSError:
                    sn['issues'].append(_issue('E_SNIFF_IO', 'Container changed or could not be read after Sniff.'))
                    continue
                expanded = sniff_io.expand_container(source['data'], logical=sn["path"], root=sn["root"],
                    **{k: self.options[k] for k in ("max_bytes", "zip_depth", "zip_entries", "zip_total_bytes")})
                sn["issues"].extend(expanded["issues"])
                sources.extend(dict(sniff=m["sniff"], data=m["data"]) for m in expanded["members"])
        # Use Assemble's reserved-name rules for the final collision check, and
        # complete it for members as well as roots before publishing anything.
        for source in sources:
            sn = source["sniff"]
            target = assemble.output_path(sn["path"]).casefold()
            if target in outputs and not any(i["code"] in {"E_OUTPUT_COLLISION", "E_ZIP_PATH"} for i in sn["issues"]):
                sn["issues"].append(_issue("E_OUTPUT_COLLISION", "Another source has the same output path."))
            outputs.add(target)
        return sources, found["skipped"]

    def _media_hashes(self, data: bytes, sn: dict, c: dict, triage_media: list) -> dict:
        hashes = {}
        if c['action'] not in {'convert_only', 'convert_and_ocr'} or not c['candidates_unique']:
            return hashes
        if sn['format'] == 'hwp':
            hashes = {m['id']: m['payload_sha256'] for m in triage_media}
        if sn["format"] not in {"docx", "pptx", "xlsx", "hwpx", 'hwp'}:
            return hashes
        remaining = self.options['zip_total_bytes']
        for candidate in c["candidates_unique"]:
            if sn['format'] == 'hwp':
                continue
            try:
                raw = sniff_io.read_member_bytes(data, candidate["id"], max_bytes=self.options["max_bytes"],
                                                 total_remaining=remaining)
                hashes[candidate["id"]] = sha256(raw).hexdigest()
                remaining -= len(raw)
            except KeyError:
                continue  # Missing media is an explicit Render pending status.
        prefixes = {}
        for digest in hashes.values():
            if digest[:12] in prefixes and prefixes[digest[:12]] != digest:
                raise sniff_io.ZipReadError('Distinct media share a filename prefix.', code='E_OUTPUT_COLLISION')
            prefixes[digest[:12]] = digest
        return hashes

    def summarize(self, entry: dict, units: list[dict], entries: dict, observations: dict,
                  *, emit: bool = False, denied: Sequence[str] = ()) -> None:
        """Keep partial results accurate too, if cancellation interrupts a later Key."""
        counts = dict(total=len(units), eligible=0, cached=0, transcribed=0, pending=0, failed=0)
        for unit in units:
            identity = ledger.key_id(ledger.make_key(unit, self.provider.meta, self.options["prompt_version"])) if unit["raster_sha256"] else None
            result = entries.get(identity) if unit["status"] in {"eligible", "cached"} else None
            if result and result["status"] == "ok":
                state = "cached" if observations.get(unit["source_id"], {}).get("hit") else "ok"
                counts["cached" if state == "cached" else "transcribed"] += 1
            elif result and result["status"] == "failed":
                state = "failed"
                counts["failed"] += 1
            else:
                state = "pending"
                counts["pending"] += 1
            if emit:
                code = result["error"]["code"] if state == "failed" else "E_APPROVAL_DENIED" if identity in denied else None
                self.emit("unit", file=entry["path"], unit=unit["source_id"], state=state, code=code)
        counts["eligible"] = counts["cached"] + counts["transcribed"] + counts["failed"]
        entry["units"] = counts

    def process(self, source: dict, entry: dict, directory: Path) -> None:
        sn, logical = source["sniff"], source["sniff"]["path"]
        original_sniff, provenance, prepared = sn, None, None
        self.emit("stage", file=logical, stage="sniff", state="end", ms=0)
        path = source.get("runtime")
        if convert.legacy_enabled(sn, self.options['preconvert_legacy']):
            try:
                raw = source['data'] if 'data' in source else _source_bytes(path, sn, self.options['max_bytes'])
                prepared = self.stage(logical, 'convert', convert.convert_legacy, raw, sn,
                    run_temp=directory, timeout_s=self.options['preconvert_timeout_s'], **{k: self.options[k] for k in
                    ('max_bytes', 'zip_entries', 'zip_total_bytes')})
                self.issues(entry, prepared['issues'])
                provenance = prepared['provenance']
                if provenance:
                    sn, path = prepared['sniff'], None
                    source = dict(sniff=sn, data=prepared['data'])
                else:
                    sn = dict(sn, issues=[*sn['issues'], *prepared['issues']])
            except OSError:
                sn = dict(sn, issues=[*sn['issues'], _issue('E_SNIFF_IO', 'Legacy source changed after Sniff.')])
        if sn['route'] == 'NATIVE' and not any(i['code'].startswith('E_') for i in sn['issues']):
            try:
                if 'data' not in source:
                    source['data'] = _source_bytes(path, sn, self.options['max_bytes'])
                if len(source['data']) != sn['bytes'] or sha256(source['data']).hexdigest() != sn['sha256']:
                    raise OSError('Source changed after Sniff.')
            except OSError:
                sn['issues'].append(_issue('E_SNIFF_IO', 'Source changed or could not be read after Sniff.'))
                source['data'] = b''
            else:
                path = None  # Core and Convert consume the same immutable owned snapshot.
        if path is None:
            # Core gets an opaque owned filename, never an archive member name.
            path = directory / ("source." + sn["format"])
            path.write_bytes(source["data"])
        outcome = prepared['outcome'] if provenance else self.stage(logical, "triage", triage.run_triage, path, sn)
        entry["triage"] = deepcopy(outcome["report"])
        if provenance and entry['triage'] is not None:
            entry['triage']['derived_media'] = [dict(id=a['id'], report=a['outcome']['report'])
                                                for a in outcome['derived_media']]
        classification_sniff = dict(sn, issues=[*sn["issues"], *outcome["issues"]])
        c = prepared['classification'] if provenance else self.stage(logical, "classify", classify.classify, classification_sniff, outcome["report"])
        entry.update({key: c[key] for key in _CLASS_FIELDS})
        self.issues(entry, [*outcome["issues"], *c["issues"]])
        self.emit("classified", file=logical, **{k: c[k] for k in ("route", "need", "label", "action")})
        data = source.get("data", b"")
        if c["action"] in {"convert_only", "convert_and_ocr"} and "data" not in source:
            try:
                data = Path(path).read_bytes()
            except OSError:
                self.issues(entry, [_issue("E_SNIFF_IO", "Source bytes could not be read.")])
                entry["action"] = c["action"] = "report_only"
        triage_media = (outcome['report'] or {}).get('media', [])
        try:
            media_hashes = prepared['media_hashes'] if provenance else self._media_hashes(data, sn, c, triage_media)
        except sniff_io.ZipReadError as exc:
            sn['issues'].append(_issue(exc.code, 'Media preparation exceeded a source bound or collided.'))
            c = classify.classify(dict(sn, issues=[*sn['issues'], *outcome['issues']]), outcome['report'])
            entry.update({key: c[key] for key in _CLASS_FIELDS})
            self.issues(entry, c['issues'])
            media_hashes = {}
        opts = dict(self.options, file={k: original_sniff[k] for k in ("path", "sha256", "bytes", "format")},
                    classification=c, triage_media=triage_media, media_hashes=media_hashes)
        if provenance:
            opts['preconversion'] = provenance
            # Derived assets have content ids; HWP5's stored-stream rules do not apply.
            opts['triage_media'] = [dict(id=identity, payload_sha256=digest)
                                   for identity, digest in media_hashes.items()]
        selected = self.stage(logical, "select", select.select, c, opts)
        self.summarize(entry, selected["units"], {}, {})
        if selected["oversize"]:
            self.issues(entry, [_issue("E_PLAN_OVERSIZE", "Source exceeds the unit bound.")])
        converted = prepared['converted'] if provenance else self.stage(logical, "convert", convert.convert_source, data, sniff=sn,
            action=c["action"], run_temp=directory, cache_dir=None if self.plan_only else self.cache)
        if provenance:
            for name in ('triage', 'classify', 'convert'):
                self.emit('stage', file=logical, stage=name, state='end', ms=0)
        self.issues(entry, converted["issues"])
        for unit in selected["units"]:
            if unit["kind"] == "media":
                digest = select.media_identity(unit["source_id"], sn["format"], opts["media_hashes"], opts["triage_media"])
                name = next((n for n in converted["media"] if Path(n).stem == digest), None)
                if name:
                    unit["media_file"] = "media/" + name
        eligible = [u for u in selected["units"] if u["status"] == "eligible"]
        if c['action'] in {'convert_only', 'convert_and_ocr'}:
            rendered = self.stage(logical, "render", render.render_units, data, sniff=sn, units=eligible,
                                 run_temp=directory, dpi=opts["dpi"], max_pixels=opts["max_pixels"],
                                 max_bytes=opts['max_bytes'], total_remaining=opts['zip_total_bytes'])
        else:
            rendered = dict(units=[], rasters={}, frames_total=None, issues=[])
        self.issues(entry, rendered["issues"])
        if any(i['code'] == 'E_ZIP_BOMB' for i in rendered['issues']):
            c.update(action='report_only', need='UNKNOWN', label='U', candidates_unique=[])
            entry.update({key: c[key] for key in _CLASS_FIELDS})
            selected = dict(units=[], oversize=False)
            rendered = dict(units=[], rasters={}, frames_total=None, issues=rendered['issues'])
        by_id = {u["source_id"]: u for u in rendered["units"]}
        units = [by_id.get(u["source_id"], u) for u in selected["units"]]
        selected = dict(selected, units=units)
        entries, observations, jobs = {}, {}, {}

        def lookup():
            for unit in units:
                if unit["status"] not in {"eligible", "cached"}:
                    continue
                key = ledger.make_key(unit, self.provider.meta, opts["prompt_version"])
                identity = ledger.key_id(key)
                if identity in self.memo:
                    result = dict(hit=True, entry=self.memo[identity], issues=[])
                else:
                    result = self.store.lookup(key, force=opts["force"])
                self.issues(entry, result["issues"])
                observations[unit["source_id"]] = result
                if result["hit"]:
                    entries[identity] = result["entry"]
                if identity not in jobs:
                    jobs[identity] = dict(key_id=identity, key=key, units=[], hit=result["hit"],
                                         raster_path=rendered["rasters"][unit["source_id"]])
                jobs[identity]["units"].append(unit)

        self.stage(logical, "lookup", lookup)
        self.summarize(entry, units, entries, observations)
        file_plan = self.stage(logical, "plan", plan.plan, selected, rendered, observations, self.provider.meta, opts)
        self.plans.append(file_plan)
        entry["plan_hash"] = file_plan["plan_hash"]
        if file_plan["plan_hash"] in opts["yes_hashes"]:
            self.matched_hashes.add(file_plan["plan_hash"])
        entry["requests"]["to_send"] = file_plan["status"]["requests_to_send"]
        pending_reason, authorized = "no_provider", True
        try:
            entry["consent"] = self.stage(logical, "approve", approve.approve, file_plan, opts,
                                          self.now().isoformat(timespec="seconds"))
        except approve.ApprovalRequired:
            authorized, pending_reason = False, "approval_required"
            self.issues(entry, [_issue("E_APPROVAL_REQUIRED", "This file requires approval of its Plan.")])
            approved = file_plan["approved"]
            self.emit("approve_required", file=logical, plan_hash=file_plan["plan_hash"],
                      destination=approved["provider"]["destination"], model=approved["provider"]["model"],
                      requests_to_send=file_plan["status"]["requests_to_send"],
                      **{k: approved[k] for k in ("keys_unique", "max_requests", "est_max_cost", "cost_known",
                                                 "threshold_exceeded", "sensitive_hits")})
        if self.plan_only:
            sink = opts.get("_on_plan")
            if sink is not None:
                sink(file_plan)
            return

        def publish(result):
            entries[result["key_id"]] = result
            entry["requests"]["ok" if result["status"] == "ok" else "failed"] += 1
            self.summarize(entry, units, entries, observations)
            if result["error"] is not None:
                self.issues(entry, [dict(code=result["error"]["code"], message=result["error"]["message"],
                                         key_id=result["key_id"])])
            self.issues(entry, self.store.write(result))
            if result["status"] == "ok":
                self.memo[result["key_id"]] = result

        before = self.provider.calls
        if authorized:
            try:
                result = self.stage(logical, "transcribe", transcribe.run_transcribe, list(jobs.values()), self.provider,
                    prompt=transcribe.load_prompt(opts["prompt_version"]), force=False,
                    max_requests=file_plan["approved"]["max_requests"], consent=entry["consent"], tools=self.tools,
                    now=self.now(), publish=publish, postprocess=assemble.postprocess_text)
            finally:
                entry["requests"]["sent"] = self.provider.calls - before
            entries.update(result["entries"])
            self.issues(entry, result["issues"])
            entry["requests"].update(sent=self.provider.calls - before, ok=result["ok"], failed=result["failed"])
            denied = set(result["denied"])
        else:
            denied = set()
        self.summarize(entry, units, entries, observations, emit=True, denied=denied)
        base = converted["body"]
        if sn["format"] == "pdf" and converted["pages"] is not None:
            base = "\n\n".join(f"<!-- mdflow:page {i} -->\n{page}" for i, page in enumerate(converted["pages"], 1))
        meta = dict(source=logical, sha256=original_sniff["sha256"], bytes=original_sniff["bytes"], format=sn["format"],
                    **{k: c[k] for k in ("route", "need", "label", "coverage_state")}, triage_decision=c["decision"],
                    provider=self.provider.meta["name"], model=self.provider.meta["model"], prompt_version=opts["prompt_version"],
                    dpi=opts["dpi"], tools={**self.tools, **converted.get("tools", {})},
                    now=self.now().isoformat(timespec="seconds"),
                    frames_total=rendered["frames_total"], pending_reason="approval_denied" if denied else pending_reason)
        if provenance:
            meta.update(provenance)
        if sn["format"] == "pdf":
            meta["pages_total"] = len(converted["pages"]) if converted["pages"] is not None else (
                ((outcome["report"] or {}).get("coverage") or {}).get("pages_total") or 0)
        if c["action"] == "recurse":
            self.deferred.append((entry, meta))
        elif c["action"] in {"convert_only", "convert_and_ocr"}:
            self.issues(entry, assemble.media_issues(base, units))
            text, placements = self.stage(logical, "assemble", assemble.assemble, base, units, entries, meta)
            entry["placements"] = sum(placements.values())
            self.stage(logical, "write", self.publish_output, entry, text, converted["media"])

    def publish_output(self, entry: dict, text: str, media: dict) -> None:
        relative = assemble.output_path(entry["path"])
        # Containment remains Write's responsibility, including on skipped writes.
        existing = self.out / relative
        decision = dict(write=True, issues=[])
        try:
            write._checked_target(os.fspath(self.out), relative)
            if existing.is_file():
                decision = assemble.publication_decision(existing.read_text(encoding="utf-8"), text,
                                                        force=self.options["force"])
        except (OSError, UnicodeError):
            decision = dict(write=False, issues=[_issue("E_OUTPUT_IO", "Existing output could not be read.")])
        self.issues(entry, decision["issues"])
        if any(i['code'] == 'E_OUTPUT_IO' for i in decision['issues']):
            entry['outputs'] = []
            return
        if not decision["write"]:
            result = write.publish_source(self.out, relative, None, media)
            self.issues(entry, result['issues'])
            entry["outputs"] = [relative] if result['ok'] else []
            return
        result = write.publish_source(self.out, relative, text.encode("utf-8"), media)
        self.issues(entry, result["issues"])
        entry["outputs"] = [p for p in [*result["written"], *result["unchanged"]] if p == relative]

    def finish_file(self, entry: dict) -> None:
        counts = entry["units"]
        self.emit("file_end", file=entry["path"], outputs=entry["outputs"],
                  units=dict(total=counts["total"], done=counts["cached"] + counts["transcribed"],
                             pending=counts["pending"], failed=counts["failed"]))


def run(roots: Sequence[Path], options: dict, *, provider=None,
        now: datetime | None = None) -> dict:
    """Run discovered sources; provider/now permit deterministic integration probes."""
    core_guard.check()
    opts = dict(DEFAULTS, cache=Path.home() / ".mdflow/cache")
    opts.update(options)
    opts["cache"] = Path(opts["cache"]).expanduser().absolute()
    if opts.get("out"):
        opts["out"] = Path(opts["out"]).expanduser().absolute()
    if provider is None:
        provider = providers.build_provider(opts["provider"], **{k: opts.get(k) for k in
            ("model", "cost_hint", "command", "command_egress", "trust_command")}, command_env=opts.get("command_env", ()))
    opts["proxy"] = getattr(provider, "proxy", None)
    pipeline = _Pipeline(opts, provider, now)
    started = pipeline.now().isoformat(timespec="seconds")
    public_options = {k: opts[k] for k in ("provider", "model", "dpi", "min_priority", "max_units", "approve_threshold", "force")}
    if opts['preconvert_legacy']:
        public_options.update(preconvert_legacy=True, preconvert_timeout_s=opts['preconvert_timeout_s'])
    for key in ("cache", "out"):
        if opts.get(key):
            path, home = str(opts[key]), str(Path.home())
            public_options[key] = "~" + path[len(home):] if path == home or path.startswith(home + os.sep) else path
    value = dict(v=1, mdflow=__version__, started=started, finished=started, options=public_options,
                 files=[], skipped=[], exit=0)
    cancelled = False
    with cancellation():
        try:
            sources, value["skipped"] = pipeline.discover(roots)
            value["files"] = [_empty_file(s["sniff"]) for s in sources]
            pipeline.emit("run_start", files=len(sources), provider=provider.meta["name"])
            with runtime_temp.run_directory() as run_directory:
                for index, (source, entry) in enumerate(zip(sources, value["files"]), 1):
                    directory = Path(run_directory) / str(index)
                    pipeline.emit("file_start", file=entry["path"], index=index, total=len(sources))
                    try:
                        directory.mkdir()
                        pipeline.process(source, entry, directory)
                    except OSError:
                        pipeline.issues(entry, [_issue("E_OUTPUT_IO", "Source working files could not be prepared.")])
                    finally:
                        if not any(item[0] is entry for item in pipeline.deferred):
                            pipeline.finish_file(entry)
                if not pipeline.plan_only:
                    for entry, meta in reversed(pipeline.deferred):
                        children = [f for f in value["files"] if f["path"].startswith(entry["path"] + "/")]
                        def cell(text):
                            return str(text).replace("|", "\\|").replace("\n", " ")
                        body = "| member | label | action | output |\n|---|---|---|---|\n" + "".join(
                            "| " + " | ".join(cell(v) for v in (f["path"][len(entry["path"]) + 1:], f["label"],
                                                   f["action"], ", ".join(f["outputs"]))) + " |\n" for f in children)
                        text, _ = assemble.assemble(body, [], {}, meta)
                        pipeline.publish_output(entry, text, {})
                        pipeline.finish_file(entry)
        except (Cancelled, KeyboardInterrupt):
            cancelled = True
        except OSError:
            problem = _issue('E_OUTPUT_IO', 'Run working files could not be prepared or removed.')
            if value["files"]:
                pipeline.issues(value["files"][0], [problem])
            else:
                value.setdefault('issues', []).append(problem)
                pipeline.emit('error', file=None, **problem)
        unused = set(opts["yes_hashes"]) - pipeline.matched_hashes
        if unused:
            warning = _issue("W_APPROVAL_UNUSED", "An approval hash matched no file in this invocation.")
            if value["files"]:
                pipeline.issues(value["files"][0], [warning])
            else:
                pipeline.emit("warning", file=None, **warning)
        codes = [issue["code"] for f in value["files"] for issue in f["issues"]]
        codes.extend(issue['code'] for issue in value.get('issues', []))
        value["exit"] = assemble.exit_code(codes, cancelled=cancelled)
        value["finished"] = pipeline.now().isoformat(timespec="seconds")
        failed = sum(bool(assemble.exit_code([i["code"] for i in f["issues"]])) for f in value["files"])
        terminal = dict(v=1, ev='run_end', ts=value['finished'], exit=value['exit'],
                        files_ok=len(value['files']) - failed, files_failed=failed,
                        provider_calls=pipeline.provider.calls)
        if opts.get('_on_run_end'):
            opts['_on_run_end'](terminal)
        else:
            pipeline.emit("run_end", **{k: terminal[k] for k in ('exit', 'files_ok', 'files_failed', 'provider_calls')})
    return value
