# Distribution, CI and release: v2.0.0

Status: implementation/release specification, 2026-11-09. Binding: [R1-R23](01_DECISIONS.md). Shell: [20_SHELL](20_SHELL.md). Engine interface: [SPEC](10_SPEC.md), unchanged. External checks below distinguish documented availability from executed target evidence. No CI/release success is claimed.

## 1. Engine distribution

REQ-PKG-01 MUST: Build `mdflow` as a pure-Python wheel with a module entry point supporting SPEC section 10. Core/transitive dependencies may contain native wheels; do not advertise the complete environment as pure Python. Distribute `engine.zip` containing the 2.0.0 wheel, `engine.lock`, `BOOTSTRAP.md`, license notices and package inventory. Never ship a relocated venv, cache, credentials, old wrapper or peerhub runtime. Oracle: ZIP inventory and wheel metadata checks; import/run from an empty environment outside the source tree; forbidden-content scan.

REQ-PKG-02 MUST: Release one exact hash-checked `engine.lock`: `mdflow==2.0.0` via its local wheel path, `markitdown-gc==0.3.5`, every transitive distribution/version and allowed wheel SHA-256. Use environment markers where required; include hashes for every advertised Python/OS/architecture target. Renderer/Pillow versions are exact lock entries, not values copied from SPEC examples. Keep bootstrap/build/test tool dependencies separately pinned. No editable/VCS/sdist requirements, `[all]`, optional audio/YouTube/Azure extras or unpinned upgrades. Oracle: fresh wheel-only hash-mode installs in every required target pass `pip check`; a changed wheel, unhashed dependency or missing target wheel fails. [pip secure-install rules](https://pip.pypa.io/en/stable/topics/secure-installs/).

The pinned [GUIDE install section](ref/markitdown-gc_GUIDE_0.3.5.md#install) says document converters, including HWP/HWPX, are default dependencies. The triage source's suggested `[hwp]` install hint is an error-message fallback, not proof that an extra is necessary. Require HWP classification/conversion contract evidence from the locked environment; do not add a guessed extra.

REQ-PKG-03 MUST: Runtime compatibility follows SPEC: engine `>=2.0.0,<2.1.0`, Core `>=0.3.5,<0.4`; the release's reproducible installation is exactly engine 2.0.0/Core 0.3.5. Contract CI separately tests 0.3.5 and the newest publicly available Core `<0.4`, deduplicating equal versions. A successful range check does not certify an arbitrary lock. Pin triage schema 1 and rules vocabulary using R18 golden reports and installed-Core contract tests. Oracle: incompatible versions fail; schema !=1 fails loudly; installed Core reports match golden fixtures; range-endpoint jobs have visible results. Candidate resolver/network failure is a failed gate, not an empty successful matrix.

REQ-PKG-04 MUST: Verify public retrieval, licenses and target wheels for every lock entry before release; do not substitute upstream `markitdown` if the fork is unavailable. Oracle: recorded artifact URL/hash/license and isolated install logs for every required target. **TODO-VERIFY:** public `markitdown-gc` 0.3.5 metadata/artifacts and complete lock hashes/wheel coverage. PyPI [version page](https://pypi.org/project/markitdown-gc/0.3.5/) and JSON endpoint returned web cache misses in this session; shell REST access was blocked. These are retrieval failures, not evidence of nonexistence. No package was installed here.

## 2. User-terminal bootstrap and version check

REQ-PKG-05 MUST: `BOOTSTRAP.md` and SetupModal show these commands, rendered for the user's chosen paths and shell, for execution **in the user's own terminal**. The plugin never downloads, installs or updates Python, engine or dependencies (R10). Download/verify the release assets, extract `engine.zip`, then change directory to its extracted root before installing. `engine.lock` uses `./wheels/mdflow-2.0.0-py3-none-any.whl` with its hash for the engine and exact named requirements/hashes for dependencies. `wheels/` may supply additional matching wheels; missing ones are retrieved from the documented Python package index. Show index/network use before setup. Oracle: command examples run unchanged after placeholder substitution on each OS; plugin spawn/network mocks show diagnostics only. [Obsidian policy](https://docs.obsidian.md/community-directory/developer-policies).

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

REQ-PKG-06 MUST: Before jobs, run the selected interpreter's SPEC `version` command as the handshake. Validate only the response fields SPEC defines (`mdflow`, `markitdown-gc`, `pypdfium2`, `python`), their parseability and version policy in section 1. Initially require the renderer version tested for this release's lock. Missing/bad JSON, timeout or incompatible versions blocks jobs and opens diagnostics; never invoke an invented `--handshake` or require an engine-reported lock digest/capabilities/protocol extension. The interpreter's package identity/lock hashes and triage schema are verified by install/contract evidence, not fabricated response fields. Oracle: version-fixture tests and actual packaged-engine responses agree with the shell gate; mismatched engine/Core/renderer blocks before conversion.

## 3. CI matrix and reproducibility

REQ-PKG-07 MUST: Run the following nine engine matrix cells with `fail-fast:false`; only Python 3.15 cells allow failure. Set Python explicitly via setup-python; record resolved patch, architecture, runner image release and action SHAs in logs. These are real labels verified against the official [runner image inventory](https://github.com/actions/runner-images#available-images) on 2026-11-09. Availability of the label is verified; successful Python/dependency installation is TODO-VERIFY until CI executes.

| Runner label | Architecture | Required Python | Allowed-failure Python |
|---|---|---|---|
| `windows-2022` | x64 | 3.10, 3.14 | 3.15 |
| `ubuntu-24.04` | x64 | 3.10, 3.14 | 3.15 |
| `macos-15-intel` | x64 | 3.10, 3.14 | 3.15 |

The inventory reports macOS 14 retired from GitHub Actions on 2026-11-02; do not use `macos-14`. This baseline claims x64 only. macOS arm64 and other architectures require additional install/contract evidence before being advertised. Oracle: workflow expansion contains six required and three experimental cells with those labels; release dependencies include all six required results and cannot be made green by experimental failures.

REQ-PKG-08 MUST: Required cells run pytest, Core contract tests, security/offline mocks and packaged integration against the exact release lock. Test real small/generated fixtures for classification, malformed/encrypted/oversize, partial failures, frame/Office occurrence accounting, cache invalidation and cancellation. Golden expectations originate from pinned Core reports, never hand-written candidate IDs. Cover successful warm rerun (0 provider calls, 0 output rewrites), retry/force separately, report/exit semantics and forbidden-network probes. Package integration uses a fresh environment and paths with spaces/Korean characters, with no source-tree imports/global Core. Oracle: test artifacts include fixture manifest, golden digests, resolved dependencies, subprocess results and output/call/mtime assertions; missing artifacts/fixtures fail, not skip. cx R3-26 coverage gaps cannot be closed by counting green assertions against an erroneous table.

REQ-PKG-09 MUST: On all three runner labels run `npm ci`, typecheck, production build and Jest against freshly authored shell tests. Test every migration key, secret removal, six commands, framing, modal invalidation, setup noninstallation, localization and cancellation. Pin a supported Node release's exact patch in CI (24.x line proposed; exact patch TODO-VERIFY); do not rely on runner-default Node. Before claiming full Python 3.10-3.14 support, add install/version/classify smoke cells for 3.11/3.12/3.13 on all three OSes. Oracle: job logs list actual versions and commands; all advertised-version smokes pass. Obsidian's Electron runtime compatibility is a separate desktop test, not inferred from build Node.

REQ-PKG-10 MUST: Implement R20 traceability across engine/shell/packaging requirements using actual `@req("REQ-...")` registrations and a Jest/release-check equivalent. Generate stage x failure-mode and file-class x stage matrices from markers + fixture manifest; declared N/A cells have reasons. Fail if any requirement in 10/20/25 has zero registered tests, any marker is unknown, or any required cell lacks executable coverage. Record named R15/R16 manual attestations separately; the checking tests verify their evidence exists, not that source hashes prove policy compliance. Oracle: deliberately delete a marker, invent an ID and remove a fixture; each mutation fails the traceability job. Acceptance evidence is binary and links test results; no self-assigned score or partial rubric.

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
| Commands/source | Six frozen local IDs, no embedded plugin prefix; remove sample/retired inherited code; clean-room R15 attestation; historical MIT credit in README/LICENSE. |
| Public files | README, LICENSE, required notices, reviewable implementation source and version metadata available. |
| Dependency behavior | SetupModal diagnoses only; external commands tested; no self/dependency installation or update. |
| Listing | Existing listing receives 2.0.0 update; no duplicate initial submission. Verify owner access and default-branch manifest/listing state. |

REQ-PKG-16 MUST: README includes all R16 disclosures below in plain language before release; link them from setup/provider UI. Oracle: named reviewer cites exact README sections and matches configured behavior; tests assert no telemetry endpoints and no unplanned provider sockets. A missing heading/content or a false claim fails review. [Disclosure policy](https://docs.obsidian.md/community-directory/developer-policies).

| README disclosure | Required content |
|---|---|
| Network services/purpose | Default local conversion/provider `none` sends no document data. Optional OCR sends selected page/image rasters and prompt to the configured OpenAI-compatible endpoint; identify OpenAI/Azure OpenAI/Gemini-compatible/Anthropic-compatible/Ollama configurations actually documented and show actual base URL. Commands may send data according to their explicit declaration. External bootstrap downloads from the release host and Python package index. |
| Outside-vault access | Engine executable/venv, selected external sources, OS temporary rasters and cache may be outside the vault. Explain why each is accessed; output selected through the shell stays inside the vault. Name CLI `~/.mdflow/cache` and plugin `<plugin-dir>/cache`; cache contains transcriptions and can be cleared explicitly. |
| Telemetry | No client telemetry. Do not equate this with provider retention/privacy; link configured providers' policies where applicable. |
| Account/key/cost | Optional remote OCR may need an account/API key and incur charges; environment-only credentials; provider `none` needs neither. Local commands run with user privileges. Explain estimates/unknown costs, consent, cancellation limits and possible retry charges. |
| Migration/operation | External venv setup/upgrade; six command aliases; Azure/router/URL/audio removals; fixed output/media names; dropped settings; sanitized rollback snapshot and old backups potentially retaining credentials. |

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
| Fable X-15/X-16 | Fixed: SPEC Core compatibility range and existing version command; exact installation lock remains distinct. Extra handshake fields rejected below. |
| Fable X-17 | Missing-dependency test accepted; asserted mandatory HWP extra rejected below. |
| Fable X-27/X-34/X-35 | Fixed for packaging: diagnostics-only setup, verified runner labels, R15/R16/17/18 and full release asset/checklist requirements. Acceptance-file edits remain open. |
| ag orphan AC-023; cx R3-26 | Packaging requirements/oracles now explicit; generated marker coverage required. Existing engine/acceptance gaps remain open, not declared covered by these tables. |
| cx R3-01..10 | Open engine vocabulary/classification/inventory defects; require corrected SPEC and pinned-Core fixture evidence before release. |
| cx R3-11..25; Fable X-20..33/X-40..48 | Engine/acceptance corrections remain in their owning files. Package tests gate them; no protocol/engine changes are invented here. |

## Objections / Rejected findings

- Fable X-17's assumption that HWP needs `[hwp]` is rejected: pinned GUIDE explicitly includes HWP/HWPX by default. Its valid concern is met by actual locked-install HWP contract checks; public metadata/wheels remain TODO-VERIFY.
- Fable X-16's new handshake fields are rejected under R19: SPEC section 10 is incorporated unchanged. Version checks cannot certify an installed lock digest or triage schema absent from that response; install and Core contract tests supply those checks.
- Fable X-34's universal `latest` labels are rejected as unnecessary drift: explicit documented labels above are valid and log image versions. macOS 14 is retired despite a stale table row in the inventory. Label availability never substitutes for actual matrix runs.
- Fable section 6's in-place upgrade simplification is rejected for the documented recommended procedure: a second user-created venv preserves rollback without plugin dependency management. No runtime pointer is introduced.
- Old PKG-O01 is resolved by amended R10; it is not an outstanding objection to the binding decisions.

All remaining TODO-VERIFY items block the relevant release claim: public Core/wheel/lock availability; nine target installs (six mandatory); intermediate-version and advertised-architecture support; final action/runtime/CLI/security review; attestation eligibility and verification; Windows signal/descendant behavior; tested Obsidian minimum/current versions; directory ownership/update behavior; clean-room/README manual attestations; actual draft/release/post-deploy/rollback/cleanup evidence. Documentation checks completed in this session verify sources and requirement structure only.
