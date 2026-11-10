"""Shared stage contracts from SPEC sections 2, 5, 7 and 8.

TypedDicts describe data; runtime validation belongs to the owning stages.
Key construction stays in ledger.py (DRAFT-3.1).
"""

import re
from typing import Literal, TypedDict

Route = Literal["NATIVE", "CONTAINER", "LEGACY", "PROTECTED", "UNSUPPORTED"]
Need = Literal["NONE", "PARTIAL", "FULL", "UNKNOWN"]
Action = Literal["convert_only", "convert_and_ocr", "recurse", "report_only"]
UnitStatus = Literal[
    "eligible", "cached", "skipped_low_priority", "oversize", "render_failed",
    "unsupported_media_format",
]


class Issue(TypedDict):
    code: str
    message: str


class SniffResult(TypedDict):
    path: str
    root: str
    bytes: int
    sha256: str
    ext: str
    magic: str
    format: str
    route: Route
    reasons: list[str]
    issues: list[Issue]


class Candidate(TypedDict):
    id: str
    kind: str
    page: int | None
    priority: Literal["normal", "low"]
    priority_core: Literal["high", "low"]
    refs: int


class Classification(TypedDict):
    route: Route
    need: Need
    label: Literal["T", "S", "M", "U", "C", "L", "P", "X"]
    action: Action
    decision: str
    coverage_state: str
    candidates_unique: list[Candidate]
    uninspected_pages: int
    reasons: list[str]
    issues: list[Issue]


class _UnitRequired(TypedDict):
    kind: Literal["page", "media"]
    source_id: str
    page: int | None
    status: UnitStatus
    raster_sha256: str | None
    dpi: int
    mime: str | None
    bytes: int | None
    priority: Literal["normal", "low"]
    priority_core: Literal["high", "low"]


class Unit(_UnitRequired, total=False):
    also: list[str]
    media_file: str | None


class SelectedUnits(TypedDict):
    units: list[Unit]
    oversize: bool


class ProviderMeta(TypedDict):
    name: str
    model: str
    egress: bool
    cost_hint: str | None
    max_batch: int
    retries: int
    destination: str | None
    command_env_names: list[str]
    accepts: list[str]


class ApprovedProvider(TypedDict):
    name: str
    model: str
    egress: bool
    cost_hint: str | None
    max_batch: int
    retries: int
    destination: str | None
    proxy: str | None
    command_env_names: list[str]


class FileIdentity(TypedDict):
    path: str
    sha256: str
    bytes: int
    format: str


class PlanClassification(TypedDict):
    route: Route
    need: Need
    label: Literal["T", "S", "M", "U", "C", "L", "P", "X"]
    action: Action
    decision: str
    coverage_state: str


class Preconversion(TypedDict):
    original_sha256: str
    derived_sha256: str
    derived_format: Literal['markdown']
    fidelity: Literal['DERIVED']
    tool: str
    version: str


class _ApprovedPlanRequired(TypedDict):
    file: FileIdentity
    classification: PlanClassification
    provider: ApprovedProvider
    provider_fingerprint: str
    prompt_version: str
    dpi: int
    units: list[Unit]
    units_total: int
    keys_unique: int
    max_requests: int
    est_max_cost: str | None
    cost_known: bool
    approve_threshold: int
    threshold_exceeded: bool
    sensitive_hits: list[str]
    oversize: bool


class ApprovedPlan(_ApprovedPlanRequired, total=False):
    preconversion: Preconversion


class UnitCounts(TypedDict):
    eligible: int
    cached: int
    skipped_low_priority: int
    oversize: int
    render_failed: int
    unsupported_media_format: int


class PlanStatus(TypedDict):
    units: UnitCounts
    requests_to_send: int
    uninspected_pages: int
    frames_total: int | None


class Plan(TypedDict):
    v: Literal[1]
    approved: ApprovedPlan
    status: PlanStatus
    plan_hash: str


class ProviderError(Issue):
    exit: int | None


class UnitResult(TypedDict):
    status: Literal["ok", "failed"]
    text: str | None
    error: ProviderError | None
    duration_ms: int


class Consent(TypedDict):
    plan_hash: str
    approved_at: str
    by: str


class LedgerUnit(TypedDict):
    kind: Literal["page", "media"]
    dpi: int
    mime: str
    bytes: int


class LedgerEntry(UnitResult):
    v: Literal[1]
    key_id: str
    key: dict[str, object]  # The normative Key is owned by ledger.py (F-01).
    provider: dict[str, object]
    unit: LedgerUnit
    consent: Consent | None
    tools: dict[str, str]
    created: str


# SPEC 7.5: E_PROVIDER_CONFIG contributes 4 at runtime, 1 at startup.
EXIT_CODE_MAP = {
    **dict.fromkeys("E_USAGE E_CORE_VERSION E_CORE_CONFLICT".split(), 1),
    **dict.fromkeys((
        "E_SNIFF_IO E_TOO_LARGE E_ENCRYPTED E_CORRUPT E_UNSUPPORTED "
        "E_MEDIA_OUT_OF_SCOPE E_LEGACY E_ZIP_PATH E_ZIP_DEPTH E_ZIP_ENTRIES "
        "E_ZIP_TOTAL E_ZIP_BOMB E_TRIAGE_FAIL E_TRIAGE_SCHEMA E_CONVERT_FAIL "
        "E_RENDER_FAIL E_PLAN_OVERSIZE E_OUTPUT_IO E_OUTPUT_COLLISION E_CACHE_IO E_PRECONVERT"
    ).split(), 2),
    **dict.fromkeys("E_APPROVAL_REQUIRED E_APPROVAL_DENIED".split(), 3),
    **dict.fromkeys((
        "E_PROVIDER_HTTP E_PROVIDER_TIMEOUT E_PROVIDER_OUTPUT E_PROVIDER_CONFIG"
    ).split(), 4),
    **dict.fromkeys((
        "W_SKIPPED_HIDDEN W_SKIPPED_SYMLINK W_DUPLICATE_INPUT W_EXT_MISMATCH "
        "W_MEDIA_NOT_INSPECTED W_TRIAGE_UNSUPPORTED W_TRIAGE_UNKNOWN "
        "W_TRIAGE_INCONSISTENT W_TRIAGE_UNKNOWN_VALUE W_TRIAGE_PARTIAL "
        "W_CORE_DEPENDENCY W_EXTERNAL_MEDIA W_UNRESOLVED_EMBED W_IMAGE_PROBE "
        "W_REVIEW_PRIORITY W_MEDIA_UNMAPPED W_MEDIA_FORMAT W_MEDIA_MULTIFRAME "
        "W_CACHE_CORRUPT W_OUTPUT_TRUNCATED W_OUTPUT_EDITED W_APPROVAL_UNUSED W_PRECONVERTED "
        "W_EXIFTOOL_UNUSABLE"
    ).split(), 0),
}
CODES = frozenset(EXIT_CODE_MAP)
STARTUP_EXIT_CODE_MAP = {"E_USAGE": 1, "E_CORE_VERSION": 1, "E_CORE_CONFLICT": 1, "E_PROVIDER_CONFIG": 1}
# Highest precedence first; numerical max() would give the wrong answer.
EXIT_PRECEDENCE = (130, 1, 2, 4, 3, 0)
# Standalone raster frame ids (`f1`, `f2`, ...): validated by classify, selected and rendered by id.
FRAME_ID = re.compile(r"f([1-9]\d*)")
