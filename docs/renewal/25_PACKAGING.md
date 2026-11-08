# Distribution, CI and release: v2.0.0

Status: R5 revision, 2026-11-09. Binding: [decisions R1-R25](01_DECISIONS.md). Shell: [20_SHELL](20_SHELL.md). Engine authority: [SPEC](10_SPEC.md). `SYNC-AFTER-DRAFT-3` marks dependencies on its concurrent revision. External availability checks remain distinct from executed target evidence; no CI/release success is claimed.

## 1. Engine distribution

REQ-PKG-01 MUST: Build `mdflow` as a pure-Python wheel with a module entry point supporting SPEC section 10. Core/transitive dependencies may contain native wheels; do not advertise the complete environment as pure Python. Distribute `engine.zip` containing the 2.0.0 wheel, `engine.lock`, `BOOTSTRAP.md`, license notices and package inventory. Never ship a relocated venv, cache, credentials, old wrapper or peerhub runtime. Oracle: ZIP inventory and wheel metadata checks; import/run from an empty environment outside the source tree; forbidden-content scan.

REQ-PKG-02 MUST: Release one exact hash-checked `engine.lock`: `mdflow==2.0.0` via its local wheel path, `markitdown-gc==0.3.5`, every transitive distribution/version and allowed wheel SHA-256. Use environment markers where required; include hashes for every advertised Python/OS/architecture target. Renderer/Pillow versions are exact lock entries, not values copied from SPEC examples. Keep bootstrap/build/test tool dependencies separately pinned. No editable/VCS/sdist requirements, `[all]`, optional audio/YouTube/Azure extras or unpinned upgrades. Oracle: fresh wheel-only hash-mode installs in every required target pass `pip check`; a changed wheel, unhashed dependency or missing target wheel fails. [pip secure-install rules](https://pip.pypa.io/en/stable/topics/secure-installs/).

The pinned [GUIDE install section](ref/markitdown-gc_GUIDE_0.3.5.md#install) says document converters, including HWP/HWPX, are default dependencies. The triage source's suggested `[hwp]` install hint is an error-message fallback, not proof that an extra is necessary. Require HWP classification/conversion contract evidence from the locked environment; do not add a guessed extra.

REQ-PKG-03 MUST: Runtime compatibility follows SPEC: engine `>=2.0.0,<2.1.0`, Core `>=0.3.5,<0.4`; the release's reproducible installation is exactly engine 2.0.0/Core 0.3.5. Contract CI separately tests 0.3.5 and the newest publicly available Core `<0.4`, deduplicating equal versions. A successful range check does not certify an arbitrary lock. Pin triage schema 1 and rules vocabulary using R18 golden reports and installed-Core contract tests. Oracle: incompatible versions fail; schema !=1 fails loudly; installed Core reports match golden fixtures; range-endpoint jobs have visible results. Candidate resolver/network failure is a failed gate, not an empty successful matrix.

REQ-PKG-04 MUST: Verify public retrieval, licenses and target wheels for every lock entry before release; do not substitute upstream `markitdown` if the fork is unavailable. Oracle: recorded artifact URL/hash/license and isolated install logs for every required target. **TODO-VERIFY:** public `markitdown-gc` 0.3.5 metadata/artifacts and complete lock hashes/wheel coverage. PyPI [version page](https://pypi.org/project/markitdown-gc/0.3.5/) and JSON endpoint returned web cache misses in this session; shell REST access was blocked. These are retrieval failures, not evidence of nonexistence. No package was installed here.

## 2. User-terminal bootstrap and version check

REQ-PKG-05 MUST: `BOOTSTRAP.md` and SetupModal show these commands, rendered for the user's chosen paths and shell, for execution **in the user's own terminal**. The plugin never downloads, installs or updates Python, engine or dependencies (R10). Download/verify the release assets, extract `engine.zip`, then change directory to its extracted root before installing. `engine.lock` uses `./wheels/mdflow-2.0.0-py3-none-any.whl` with its hash for the engine and exact named requirements/hashes for dependencies. `wheels/` may supply additional matching wheels; missing ones are retrieved from the documented Python package index. Show index/network use before setup. Oracle: command examples run unchanged after placeholder substitution on each OS; plugin spawn/network mocks show diagnostics only. [Obsidian policy](https://docs.obsidian.md/community-directory/developer-policies).

For optional remote OCR, document a tested environment launch on each desktop OS: fully quit Obsidian, set `MDFLOW_API_KEY` in the user's terminal and launch the actual installed Obsidian executable from that process. Do not assume Dock/Finder/shortcut launches inherit shell profiles or that activating the engine venv updates an already running Obsidian. The UI reports key presence only and links these instructions; no credential-entry/storage mode. Oracle: isolated terminal-launch smoke sees a test sentinel in the child environment while diagnostics/persisted data never contain its value. Exact installed-app launch paths/commands and OS results are TODO-VERIFY; missing-key behavior remains locally usable with provider `none`.

Windows PowerShell example (quoted paths are examples to replace; `py -3.14` is an installed bootstrap Python):

```powershell
Set-Location -LiteralPath 'C:\Downloads\mdflow-2.0.0-engine'
py -3.14 -m venv 'C:\mdflow-venvs\2.0.0'
& 'C:\mdflow-venvs\2.0.0\Scripts\python.exe' -m pip install --require-hashes --only-binary=:all: --find-links './wheels' -r './engine.lock'
& 'C:\mdflow-venvs\2.0.0\Scripts\python.exe' -m pip check
& 'C:\mdflow-venvs\2.0.0\Scripts\python.exe' -m mdflow version
```

Ubuntu/macOS POSIX shell example (`python3.14` is already installed):

```sh
cd '/path/to/mdflow-2.0.0-engine'
python3.14 -m venv '/path/to/mdflow-venvs/2.0.0'
'/path/to/mdflow-venvs/2.0.0/bin/python' -m pip install --require-hashes --only-binary=:all: --find-links './wheels' -r './engine.lock'
'/path/to/mdflow-venvs/2.0.0/bin/python' -m pip check
'/path/to/mdflow-venvs/2.0.0/bin/python' -m mdflow version
```

Use a tested Python 3.10-3.14 interpreter; 3.15 is experimental. OS Python/venv prerequisites and download links must be documented per target, never installed by the plugin. Set `enginePython` to the resulting absolute `Scripts/python.exe` or `bin/python`. Activation is unnecessary. Keep that venv at its creation path; recreate it after moves or base-interpreter removal. For upgrade, create a different venv with the new lock and change the setting after external checks; retain the old interpreter for rollback. No automatic runtime pointer or global-package fallback. [Python venv guidance](https://docs.python.org/3/library/venv.html).

REQ-PKG-06 MUST: Before jobs, use the selected interpreter's existing `version` command and the complete response defined by SPEC section 10.1. Check required-field types, `protocol=1`, `triage_schema=1`, Python/engine/Core policy and exact release-tested pypdfium2/Pillow versions; validate/display `platform` per SPEC. Missing/bad fields, timeout or mismatched versions block conversions and link diagnostics. Ignore optional unknown fields; never add a separate handshake command, capabilities API or invented lock-digest field. Package identity/lock hashes are installation evidence; returned schema/version fields also undergo runtime validation. Oracle: actual packaged response and fixtures missing/mismatching every required field fail/pass the same gate; protocol 2, schema 2 and wrong Pillow/renderer block before conversion. `SYNC-AFTER-DRAFT-3`: regenerate required-field/version fixtures from SPEC section 10.1; the former four-field gate/rejection is withdrawn (R5-N11).

## 3. CI matrix and reproducibility

REQ-PKG-07 MUST: Run the following nine engine matrix cells with `fail-fast:false`; only Python 3.15 cells allow failure. Set Python explicitly via setup-python; record resolved patch, architecture, runner image release and action SHAs in logs. These are real labels verified against the official [runner image inventory](https://github.com/actions/runner-images#available-images) on 2026-11-09. Availability of the label is verified; successful Python/dependency installation is TODO-VERIFY until CI executes.

| Runner label | Architecture | Required Python | Allowed-failure Python |
|---|---|---|---|
| `windows-2022` | x64 | 3.10, 3.14 | 3.15 |
| `ubuntu-24.04` | x64 | 3.10, 3.14 | 3.15 |
| `macos-15-intel` | x64 | 3.10, 3.14 | 3.15 |

The inventory reports macOS 14 retired from GitHub Actions on 2026-11-02; do not use `macos-14`. This baseline claims x64 only. macOS arm64 and other architectures require additional install/contract evidence before being advertised. Oracle: workflow expansion contains six required and three experimental cells with those labels; release dependencies include all six required results and cannot be made green by experimental failures.

REQ-PKG-08 MUST: Required cells run pytest, Core contract tests, security/offline mocks and packaged integration against the exact lock. Test classification, malformed/encrypted/oversize, partial failures, frame/Office occurrence accounting, cache invalidation and cancellation. Core reports generate factual evidence/candidate IDs; independently reviewed mdflow route/need/action expectations supply classification oracles. Validate raw triage codes separately from mdflow section 7.5 fields (R5-N08). Test warm-success content preservation and explicit audit-report exceptions per SPEC section 10.4, with retry/force/crash uncertainty separate. Use fresh environments, spaces/Korean paths and no source-tree imports/global Core. Cover nested-directory/multi-root `plan` then same-roots `run`, repeatable file hashes in one approval/run, cache-independent hash stability and actual SPEC cost/status display. Large full Plans use `plan` stdout; progress remains bounded summaries, never truncated authorization. Oracle: original input argv/cwd/roots and destinations are unchanged; approved hashes remain stable after cache warming; changed approved bytes require fresh consent; displayed fields equal Plans; OS cancellation tests leave no owned process. Preserve fixtures/digests/dependency/report/mtime/call evidence; missing fixtures fail. `SYNC-AFTER-DRAFT-3`: final sections 7.1/7.3/7.4/7.5/8.4/10 shapes, authorization and cancellation oracles.

REQ-PKG-09 MUST: On all three runner labels run `npm ci`, typecheck, production build and Jest against freshly authored shell tests. Cover all migration keys and failure notices, secret removal, desktop guard/manifest, six commands, framing, batch/root replay, modal invalidation, diagnostic-only setup and cancellation. Run `JT-SHL-19-01`: shell table and en/ko engine-key sets equal the active Code-column set in SPEC section 7.5, excluding deleted prose and raw Core codes; fail on missing/extra/duplicate keys. Pin an exact supported Node patch (24.x proposed; patch TODO-VERIFY); no runner default. Add install/version/classify smokes for 3.11/3.12/3.13 on all OSes before advertising the full range. Oracle: logs record versions and commands; all advertised smokes and the diagnostic-set assertion pass. Test Obsidian's Electron runtime separately. Final code/version fixtures are `SYNC-AFTER-DRAFT-3`.

REQ-PKG-10 MUST: Implement R20 traceability with actual `@req("REQ-...")` registrations and Jest/release-check equivalents. Generate stage x failure-mode and file-class x stage matrices from markers + fixture manifest; N/A cells have reasons. Fail if any machine-checkable requirement in 10/20/25 lacks registered assertions, any marker is unknown or any required cell lacks executable coverage. Keep named R15 authorship, bilingual meaning and R16 README sign-offs as independent manual release gates under REQ-PKG-15/16, outside automated coverage/pass totals. A test of evidence-file existence is not proof of authorship, meaning or disclosure accuracy. Oracle: marker/fixture mutations fail traceability; missing human sign-off independently blocks publication; generated results distinguish automated and manual status, with no score or fake Jest policy pass (SHL-REV-07).

## 4. Action pinning and attestations

REQ-PKG-11 MUST: Every external `uses:` reference, including reusable workflows and nested composite actions, resolves to a reviewed full 40-hex commit SHA with a readable version comment. Check ownership and the action's actual implementation/dependencies before use; a tag-to-commit lookup proves identity only. Refresh through reviewed changes, never floating tags/branches. The following identities were verified by opening official release pages and their commit links; they are candidate pins, not a claim of a completed security review or current-version suitability.

| Action / observed version | Verified commit SHA / evidence |
|---|---|
| `actions/checkout`, v4.2.2 | [`11bd71901bbe5b1630ceea73d27597364c9af683`](https://github.com/actions/checkout/commit/11bd71901bbe5b1630ceea73d27597364c9af683) |
| `actions/setup-python`, v5.6.0 | [`a26af69be951a213d495a4c3e4e4022e16d87065`](https://github.com/actions/setup-python/commit/a26af69be951a213d495a4c3e4e4022e16d87065) |
| `actions/setup-node`, v4.4.0 | [`49933ea5288caeca8642d1e84afbd3f7d6820020`](https://github.com/actions/setup-node/commit/49933ea5288caeca8642d1e84afbd3f7d6820020) |
| `actions/upload-artifact`, v4.6.2 | [`ea165f8d65b6e75b540449e92b4886f43607fa02`](https://github.com/actions/upload-artifact/commit/ea165f8d65b6e75b540449e92b4886f43607fa02) |
| `actions/download-artifact`, v4.3.0 | [`d3f86a106a0bac45b974a628896c90dbdf5c8093`](https://github.com/actions/download-artifact/commit/d3f86a106a0bac45b974a628896c90dbdf5c8093) |
| `actions/attest`, v4 at verification | [`1e69f48acb82d1966a394da916b4c1698aa569d6`](https://github.com/actions/attest/commit/1e69f48acb82d1966a394da916b4c1698aa569d6) |

Oracle: recursive workflow/action audit rejects every floating external reference; an evidence record links each selected SHA to review. **TODO-VERIFY:** final selected action versions, their runner-runtime requirements, transitive pins and security review. Avoid another release-helper action by using reviewed GitHub CLI commands; record CLI version. [GitHub action security guidance](https://docs.github.com/en/actions/reference/security/secure-use).

REQ-PKG-12 MUST: Default CI permissions are `contents:read`; untrusted PRs get no publication secrets or write token. Build/test the candidate before granting release rights. Attestation alone receives `id-token:write` and `attestations:write`; publication alone receives `contents:write`. Never build untrusted PR code under privileged `pull_request_target`. Oracle: parsed permissions/job-dependency checks and a fork-PR run demonstrate required tests without secrets; release cannot run on untrusted PR context.

REQ-PKG-13 MUST: Attest the exact tested release subjects: `main.js`, `manifest.json`, `styles.css`, `engine.zip`, `engine.lock`, `SHA256SUMS`. Keep generated attestation bundles as release assets. Verify each subject with `gh attestation verify <asset> --repo <owner/repo>`, additionally constrain expected signer workflow and source commit using the chosen CLI's supported verification options. Record verifier version/output and subject digest before publication. Do not attest rebuilt replacements after tests. Oracle: all subjects verify against the expected repository/workflow/commit; changing one byte or repository fails. Repository-plan eligibility and exact CLI flags are TODO-VERIFY until exercised. [Official attestation generation/verification](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

## 5. Release assets and Obsidian checklist

REQ-PKG-14 MUST: Publish these assets from one candidate; compare their hashes after every transfer. `engine.lock` attached separately is byte-identical to the one inside `engine.zip`. ZIP includes a package/license inventory; `SHA256SUMS` covers the three plugin assets, ZIP and lock (not itself). Attest SHA256SUMS separately; bundle files are additional assets, with their own digest index if needed. Oracle: asset inventory/digest test and ZIP inspection; package scan finds no settings/cache/keys/venv/source-tree fallback.

| Asset | Purpose |
|---|---|
| `main.js`, `manifest.json`, `styles.css` | Individual community-install attachments. |
| `engine.zip`, `engine.lock` | Manual engine setup; ZIP contents per section 1. |
| `SHA256SUMS` | Exact subject hashes. |
| Attestation bundles | Retained provenance verification material, linked to subjects. |
| Acceptance report | CI run/commit, trace report, fixture digests, named manual reviews and release checks. |

Community installs download standard plugin assets, not the extra engine package; initial directory submission and later releases differ. [Official release/submission guide](https://docs.obsidian.md/Plugins/Releasing/Submit%20your%20plugin).

REQ-PKG-15 MUST: Validate the community-release checklist below. Oracle: machine checks for manifest/version/assets/commands/sample removal plus named policy/desktop review evidence for human checks. Unchecked rows block publication. [Submission requirements](https://docs.obsidian.md/community-directory/submission-requirements-for-plugins).

| Check | Required result |
|---|---|
| Identity/version | Preserve `id=markitdown-flow`; manifest/package/engine/tag all `2.0.0` (no `v` prefix on tag). |
| Compatibility | `isDesktopOnly:true`; `minAppVersion` equals tested minimum; append matching `versions.json` entry, preserve prior entries. |
| Description | <=250 characters, ends with period, correct capitalization, no emoji/special-character slogans or removed feature promises. Candidate: `Convert local documents to Markdown with OCR planning and selective transcription.` |
| Commands/source | Six frozen local IDs, no embedded plugin prefix; remove sample/retired inherited code. Machine input/import checks and separate named implementer/reviewer R15 clean-room attestation; historical MIT credit in README/LICENSE. |
| Bilingual review | Machine en/ko key/parity/interpolation checks plus a separate named bilingual meaning review; neither substitutes for the other. |
| Public files | README, LICENSE, required notices, reviewable implementation source and version metadata available. |
| Dependency behavior | SetupModal diagnoses only; external commands tested; no self/dependency installation or update. |
| Listing | Existing listing receives 2.0.0 update; no duplicate initial submission. Verify owner access and default-branch manifest/listing state. |

REQ-PKG-16 MUST: README includes all R16 disclosures below in plain language before release; link them from setup/provider UI. Oracle: named reviewer cites exact README sections and matches configured behavior; tests assert no telemetry endpoints and no unplanned provider sockets. A missing heading/content or a false claim fails review. [Disclosure policy](https://docs.obsidian.md/community-directory/developer-policies).

| README disclosure | Required content |
|---|---|
| Network services/purpose | Default local conversion/provider `none` sends no document data. Optional OCR sends selected page/image rasters and prompt to the configured OpenAI-compatible endpoint; identify actually documented OpenAI/Azure OpenAI/Gemini-compatible/Anthropic-compatible/Ollama configurations and actual endpoint/purpose. CLI-only commands may send data according to their declaration; the shell does not configure/run them. External bootstrap downloads from the release host and Python package index. |
| Outside-vault access | Engine executable/venv, selected external sources, OS temporary rasters and cache may be outside the vault. Explain why each is accessed; output selected through the shell stays inside the vault. Name CLI `~/.mdflow/cache` and plugin `<plugin-dir>/cache`; cache contains transcriptions and can be cleared explicitly. |
| Telemetry | No client telemetry. Do not equate this with provider retention/privacy; link configured providers' policies where applicable. |
| Account/key/cost | Optional remote OCR may need an account/API key and incur charges; environment-only credentials and tested launch-time environment guidance; provider `none` needs neither. CLI commands run with user privileges. Explain the per-file request budget and estimated maximum cost/unknown cost, interruption/retry/concurrent-cache charges and forced-cancel limits; do not promise a billing cap, exactly-once requests or an interruption counter absent from SPEC. `SYNC-AFTER-DRAFT-3`: fields follow sections 7.1/8.4. |
| Migration/operation | External venv setup/upgrade; six command aliases; Azure/router/URL/audio removals; command provider CLI-only; fixed output/media names; dropped settings; sanitized rollback snapshot and old backups potentially retaining credentials. Failed migration may leave the original secret-bearing disk file; block jobs and instruct manual removal before sync, without claiming failed writes sanitized it. |

## 6. 2.0.0 release, rollback and cleanup

REQ-PKG-17 MUST: Freeze one candidate only after required CI/traceability and [90_ACCEPTANCE](90_ACCEPTANCE.md) gates pass with evidence. Resolve R23 engine-contract blockers and conflicting acceptance text in their owning files first. Require 100% classification on labelled fixtures, zero lost/duplicated units and successful committed warm-rerun zero calls/rewrites; retry/force/crash cases have separate assertions. Keep 1.0.8 artifacts/tag for rollback. Oracle: candidate manifest points to exact commit, lock, required job runs and binary acceptance results; unresolved blockers prevent release creation/publication. No live API key/quota is needed for mandatory mock tests; optional live smoke remains separately authorized.

REQ-PKG-18 MUST: Build/package once, run packaged checks, calculate hashes, attest and create a draft 2.0.0 release with the same bytes. Release notes explain major-version migration/removals, external setup and rollback. Before publication, test fresh install and 1.0.8-settings upgrade in isolated vaults on all three desktop OSes, at both tested minimum and current stable Obsidian. Check commands, en/ko, consent dismissal/approval, mixed-document mock OCR placement, warm rerun, cancellation/restart and rollback. Oracle: signed checklist records OS/app/runtime versions, downloads/digests and outcomes; version fields/tag/versions.json agree. Minimum/current Obsidian versions, real-app results and listing owner access are TODO-VERIFY.

REQ-PKG-19 MUST: Publish tested assets/tag and corresponding default-branch metadata using the normal release process. Then install/update through the actual community listing in clean/upgrade vaults on Windows/macOS/Linux; compare downloaded hashes; perform external setup, version check, sanitized migration, local conversion and offline/mock OCR smoke. Observe zero unexpected egress and verify restart, known pending/failure display and warm rerun. Oracle: post-deploy report records listing/version, installed asset digests, platform/app/Python versions and concrete pass/fail evidence. A failed critical check triggers rollback/hotfix procedure; uploaded artifacts alone are not deployment verification.

REQ-PKG-20 MUST: Runtime rollback is user selection of the retained compatible venv followed by the normal version check. Plugin rollback: disable plugin; preserve current settings/cache; restore verified 1.0.8 standard assets and sanitized `data.v1.json`, then re-enable after reviewing v1's dependency/network behavior. Never feed schema-2 data to v1 or restore removed secrets automatically. For a public defect keep published artifacts immutable and ship a higher corrected patch; do not retag 2.0.0 or promise community auto-downgrade. Oracle: isolated rollback rehearsal recovers v1 preferences/commands without exposing secrets and records any manual credential reconfiguration; v2 runtime rollback rejects incompatible interpreters.

REQ-PKG-21 MUST: Cleanup follows successful post-deploy verification and a seven-day rollback window. Remove only confirmed owned stale transport/temp files and retired generated wrapper artifacts after their processes exit; verify resolved paths before recursive operations. Retain previous venv/sanitized snapshot through that window; user explicitly chooses later removal. Cache stays by default; explicit clear explains retranscription cost. Preserve user sources/outputs, historical logs, external backups and released locks/hashes/attestations/evidence. Oracle: cleanup dry-run lists exact owned paths; executing in a test vault leaves protected sentinels unchanged; completion log records what was removed/retained. This is a future release procedure, not authorization to delete files during this document task.

## 7. Review disposition and outstanding verification

| Finding | Disposition |
|---|---|
| Fable X-01/X-02/X-03/X-10/X-11 | Fixed by split: behavior/settings/protocol in 20_SHELL; no reuse audit, installer, alternate protocol, runtime pointer or output staging here. |
| Fable X-15/X-16 | Fixed: SPEC Core range and complete current version command; exact installation lock remains distinct. Former rejection of now-defined fields is withdrawn. |
| Fable X-17 | Missing-dependency test accepted; asserted mandatory HWP extra rejected below. |
| Fable X-27/X-34/X-35 | Fixed for packaging: diagnostics-only setup, verified runner labels, R15/R16/17/18 and full release asset/checklist requirements. Acceptance-file edits remain open. |
| ag orphan AC-023; cx R3-26 | Packaging requirements/oracles now explicit; generated marker coverage required. Existing engine/acceptance gaps remain open, not declared covered by these tables. |
| R5-N07 / SHL-REV-06 | Cooperative versus forced cancellation tests gate release. Shell command provider cut; no Job Object/taskkill subsystem or synthetic exit 130. Engine alignment is `SYNC-AFTER-DRAFT-3`. |
| R5-N08/N09 | Separate Core/mdflow collectors; cut full-Plan progress payload, use bounded summaries plus full `plan` stdout. Final envelope is `SYNC-AFTER-DRAFT-3`. |
| R5-N10 / SHL-REV-05 | Same-root batch replay and one modal; repeatable per-file hashes, no run hash/barrier or custom manifest. Final option/schema checks are `SYNC-AFTER-DRAFT-3`. |
| R5-N11 / cc mismatch | Complete SPEC version response and active code-set equality required; stale rejection withdrawn. Final fixture generation is `SYNC-AFTER-DRAFT-3`. |
| SHL-REV-01/02 | `isDesktopOnly:true` belongs to REQ-PKG-15; R16 README disclosures to REQ-PKG-16; 20_SHELL explicitly cites both. |
| SHL-REV-03/04/07 | Failure-state disclosure, env launch guidance and separate human evidence gates added; no destructive placeholder, secret-storage UI or fake automated policy proof. |
| R5 engine-only N01..06/N12 and remaining R3 partials | Fable owns SPEC corrections. Package tests wait for the final contracts (`SYNC-AFTER-DRAFT-3`); old blanket-open R3 claims are replaced by the R5 disposition. |

## Objections / Rejected findings

- Fable X-17's assumption that HWP needs `[hwp]` is rejected: pinned GUIDE explicitly includes HWP/HWPX by default. Its valid concern is met by actual locked-install HWP contract checks; public metadata/wheels remain TODO-VERIFY.
- Former Fable X-16 field rejection is withdrawn: SPEC now defines protocol/schema/Pillow/platform fields and `selftest`. Require the defined runtime fields; reject only a separate handshake API or undefined lock/capability fields.
- Fable X-34's universal `latest` labels are rejected as unnecessary drift: explicit documented labels above are valid and log image versions. macOS 14 is retired despite a stale table row in the inventory. Label availability never substitutes for actual matrix runs.
- Fable section 6's in-place upgrade simplification is rejected for the documented recommended procedure: a second user-created venv preserves rollback without plugin dependency management. No runtime pointer is introduced.
- Old PKG-O01 is resolved by amended R10; it is not an outstanding objection to the binding decisions.
- SHL-REV-03's recovery placeholder and SHL-REV-04's extra credential UI/keychain modes are not adopted: failed writes cannot guarantee sanitized replacement, and one tested environment-launch path avoids another credential mode. SPEC allows memory-to-env input but does not require it. Preserve recovery state, block jobs and document terminal launch.
- SHL-REV-06's prescribed Windows process-tree machinery is not adopted: shell command-provider support is cut, lifecycle follows SPEC and native interruption is reported honestly. Actual no-live-owned-process tests remain mandatory; a TODO or documented limitation cannot pass that release gate.
- SHL-REV-07's concern about fake policy tests is accepted. Removing R15/R16/bilingual human gates is rejected under R21: retain named manual checklist outcomes separately from automated tests.

## 8. R5 changelog (including every cut)

| Finding / cut | Change |
|---|---|
| N10 / cut root-changing per-file jobs | Package regression replays identical ordered inputs/cwd/output/cache under existing SPEC authorization. |
| SHL-REV-05 / cut repeated consent dialogs | One engine-scoped batch modal; no shell manifest/hash protocol or token estimator. |
| SHL-REV-06 / cut shell command-provider mode | Engine CLI retains R7 `command`; README/CI reflect shell `none|openai-compatible` only, without a process-tree helper subsystem. |
| N11 / cut four-field version gate | Validate full SPEC response, protocol/schema and Pillow/renderer compatibility. |
| N11 / cut duplicate health-test implementation | Shell consumes existing engine selftest; package owns its fixtures. |
| cc/N11 / cut independent diagnostic inventory | Generate from SPEC; JT-SHL-19-01 asserts SPEC/table/en/ko set-equality, excludes Core/deleted prose. Remove `W_TRIAGE_COVERAGE`, `E_PROVIDER_INTERRUPTED`, `W_STALE_TEMP`; add `W_APPROVAL_UNUSED`. |
| N07 / cut universal cancel/report promise | Forced/native exit remains interrupted; real platform/recovery tests gate release. |
| SHL-REV-03/04 / cut new recovery and credential modes | One atomic migration, explicit failure warning, environment launch guidance. |
| SHL-REV-07 / cut policy-file-as-proof assertions | Automated code checks and named manual sign-offs have separate outcomes. |
| N09 / cut full Plan progress payload | Bounded summary events and full `plan` stdout, no chunk/reference format or truncation. |
| N03/N11 / cut run hash, cache-bound approval and extra counters/cost modes | Repeated file hashes on the same batch; only SPEC's approved maximum cost/status; no shell cache lock or engine in-flight recovery mode. |
| Earlier cuts retained | No runtime pointer, global fallback, plugin installer, inherited code, `[all]`/optional network extras or relocated venv. |

Open `SYNC-AFTER-DRAFT-3`: SPEC sections 7.1/7.3/7.4/7.5/8.4/10 same-root batch/per-file authorization, approved versus informational status, summary/full-Plan framing, pending/cost fields, complete version/code fixtures and cooperative/forced cancellation. Re-run code-set equality and package contract fixtures after the concurrent edit; no engine changes are made here.

Remaining TODO-VERIFY items block the relevant release claim: public Core/wheel/lock availability; nine target installs (six mandatory); intermediate-version/advertised-architecture support; action/runtime/CLI/security review; attestations; actual Windows/blocked-request process cleanup; terminal environment-launch instructions; tested Obsidian minimum/current versions; listing ownership/update behavior; named clean-room/bilingual/README attestations; actual release/post-deploy/rollback/cleanup evidence. Documentation checks do not satisfy runtime or manual gates.
