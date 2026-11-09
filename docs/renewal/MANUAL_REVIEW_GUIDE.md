# R35 release review guide

출시 전에는 자동 검사 93/93과 이름이 명시된 동료의 MAN-01..03 검토가 필요합니다.
reviewer에는 동료/프로필/모델을 기록합니다(예: `cx/cx.effort/gpt-6.1-sol`). MAN-01의 구현자와
검토자는 서로 달라야 합니다. 출시 점수는 99/100이며 MAN-04는 `deferred: post-release (R35)`로
명시합니다. 실제 Obsidian 검증(MAN-04)은 출시 후 소유자가 수행합니다. 통과하면 100/100,
실패하면 REQ-PKG-20 롤백 절차를 실행합니다. 파일 형식 검증은 검토 내용의 진실을 증명하지 않습니다.

## Before publication

1. Obtain the full 40-hex candidate commit and existing `2.0.0` tag. Keep the tag fixed. Required CI
   produces `acceptance-evidence`; release CI freezes tested bytes into `frozen-candidate` before
   attestation. An initial release run can stop for missing peer evidence. Keep its artifacts, or use a
   standalone CI run at the same commit. Record the run containing `acceptance-evidence` as `ci-run`.
2. Download `frozen-candidate` and `acceptance-evidence`. Review the exact candidate source and bytes.
   Subjects come from `tools/build_engine.py::SUBJECTS`; use SHA256SUMS and provenance bundles.
   Changing the candidate requires fresh CI/reviews. The evidence branch may add review files; the
   evidence workflow validates them with a separate checkout of the exact candidate commit.
3. Copy the three pre-publication YAML templates and four JSON templates from
   `docs/renewal/manual-templates/` to `release-evidence/2.0.0/`. Keep filenames. Leave
   `release_rehearsal.yml` out until the owner performs MAN-04 after release. Each peer writes a
   `reviewer` such as `cx/cx.effort/gpt-6.1-sol`, ISO `date`, exact candidate `commit`, reviewed inputs,
   checks, evidence references and verdict. Replace placeholders/TODO only after review.
4. Supply independent peer reviews:

   | ID | Exact template path | Review |
   |---|---|---|
   | MAN-01 | `docs/renewal/manual-templates/R15_cleanroom.yml` | Name `implementer`; reviewer must be a different peer even if profiles/models differ. Verify SPEC/public API inputs, no retired v1 source/style/test reuse, MIT credit. |
   | MAN-02 | `docs/renewal/manual-templates/R16_readme_review.yml` | Match README disclosures to candidate behavior; cite exact anchors. |
   | MAN-03 | `docs/renewal/manual-templates/shell_i18n_review.yml` | Review every en/ko row for meaning, equivalence and parameter preservation. |

5. Complete the peer portions of the four JSON files under the contracts below. Preserve actual command
   stdout and cite source evidence. Machine identity checks cannot establish action security, license
   suitability, disclosure accuracy or language meaning.
6. Validate MAN-01..03 locally with pinned build tools:

   ```sh
   python -m pip install -r engine/requirements-build.txt
   python tools/trace.py attest MAN-01 --attest-dir release-evidence/2.0.0 --commit <candidate-sha>
   python tools/trace.py attest MAN-02 --attest-dir release-evidence/2.0.0 --commit <candidate-sha>
   python tools/trace.py attest MAN-03 --attest-dir release-evidence/2.0.0 --commit <candidate-sha>
   ```

7. Run `evidence.yml` from the branch containing the filled records:

   ```sh
   gh workflow run evidence.yml --ref evidence/2.0.0 -f path=release-evidence/2.0.0 -f candidate=2.0.0 -f ci-run=<candidate-ci-run-id>
   ```

   It checks folder containment and CI-run commit, checks out candidate tooling separately, downloads
   `acceptance-evidence`, generates machine facts and validates all peer records/placeholders. Only
   then does it upload `named-release-evidence` with all seven mandatory files at artifact root.
   A supplied MAN-04 is validated/uploaded too. Absent MAN-04 never becomes PASS. The producer
   preserves peer identities, checks and verdicts; it never invents them.
8. Run the tagged release workflow:

   ```sh
   gh workflow run release.yml --ref 2.0.0 -f evidence-run=<evidence-run-id>
   ```

   It downloads into `build/manual/`, verifies six targets and seals
   `SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 deferred: post-release (R35)`.
   The publisher enforces the same structured policy before creating/verifying draft assets.
   Follow the repository's publication procedure once the draft bytes compare successfully.

## Extra evidence contracts

All four files are mandatory gate inputs and are uploaded by `evidence.yml`.
The workflow invokes this producer using the downloaded candidate CI artifact in `build/executions/`:

```sh
python tools/release_evidence.py produce --source release-evidence/2.0.0 --output build/evidence --executions build/executions --commit <candidate-sha>
```

`validate_extra` is the executable contract. Common peer fields: `reviewer` (peer/profile/model),
`date` (ISO date), exact candidate `commit`, nonempty `evidence[]` strings, `verdict: PASS`.
Unfilled placeholders, TODO, failed verdicts and stale commits are rejected.

| File / exact template path | Producer | Required contents |
|---|---|---|
| `oracles.json` / `docs/renewal/manual-templates/oracles.json` | Peer using actual receipts | Exactly G-01..G-17 object keys. Each receipt has common peer fields, actual nonempty `command`, unedited string `stdout`, integer `exit: 0`, nonempty `expected` from 90_ACCEPTANCE and peer `expected_output_review: PASS`. For matrix/multi-command oracles link every required run and review the complete output against Expected. One target never substitutes for all targets. |
| `actions-review.json` / `docs/renewal/manual-templates/actions-review.json` | Automatic identity + peer security review | Common peer fields and `actions[]`, exactly one row per section 4 action: `action`, exact table `sha`, nonempty `evidence[]`, peer PASS `checks` for `ownership`, `implementation`, `dependencies`, `runtime`, `transitive_pins`. The producer rejects workflow/table disagreement; `gh api repos/<action>/commits/<sha>` must return that SHA before it writes `verification: {command, stdout: {sha}, exit: 0}`. Identity lookup is not security review; inspect actual code/runtime/dependencies and nested uses at the SHA. |
| `pkg04_core_artifacts.json` / `docs/renewal/manual-templates/pkg04_core_artifacts.json` | Automatic PyPI/CI facts + peer license review | Common peer fields; `package: markitdown-gc`, `version: 0.3.7`, official versioned JSON `source`; `artifacts[]` contains every returned file's `filename`, HTTPS files.pythonhosted.org `url`, 64-hex `sha256`, positive integer `size`, `packagetype` (bdist_wheel/sdist), `yanked: false`; at least one wheel. Peer `checks.artifact_licenses` and six target-key checks must PASS. The producer copies actual pip reports into six `install_reports[]` rows: `target`, exact `commit`, `exit: 0`, `licenses_reviewed` derived from the peer check, and `report.install[]` metadata/download URLs/SHA256 hashes. Each target resolves one compatible markitdown-gc. PyPI metadata alone does not establish license suitability. |
| `listing-review.json` / `docs/renewal/manual-templates/listing-review.json` | Peer | Common peer fields, `listing: {id: markitdown-flow, version: 2.0.0}`, peer PASS `checks`: `identity`, `manifest_versions`, `description`, `commands`, `desktop_only`, `readme_disclosures`. Cite candidate manifest/versions/README and existing listing/owner access. Proposed update review precedes release; actual install-via-listing is post-release REQ-PKG-19. |

Six exact target keys: `windows-2022:x64:py3.10`, `windows-2022:x64:py3.14`,
`ubuntu-24.04:x64:py3.10`, `ubuntu-24.04:x64:py3.14`, `macos-26:arm64:py3.10`, `macos-26:arm64:py3.14`.
The producer consumes `runtime-<runner>-py<version>.json` (`installed: true`, exact commit) and
`install-<platform>-py<version>-compat-env.json` (`platform` = win32/linux/darwin). The gate separately
validates complete JUnit/collection/registry receipts. Automatic fields `verification`, `artifacts` and
`install_reports` start empty in the templates; APIs/CI fill them while peer fields remain unchanged.

API contracts: [PyPI JSON API](https://docs.pypi.org/api/json/), [GitHub CLI API](https://cli.github.com/manual/gh_api).

## After publication: owner MAN-04 and post-release validators

The owner copies `docs/renewal/manual-templates/release_rehearsal.yml` and installs published bytes on
real Windows/macOS/Linux × Obsidian **minimum**/**current**, six runs. Record actual app/Python/engine/Core
versions, subject SHA256 hashes, tag/manifest/versions.json agreement, inputs, evidence and named owner
verdict. The minimum app version must match candidate manifest.json `minAppVersion`.
Perform every template check: fresh install, 1.0.8 upgrade, rollback, consent dismiss/approve,
mixed-document mock OCR, warm rerun, cancel/restart (real Windows), terminal environment launch,
commands and en/ko. Peer code review cannot substitute for these observations.

Retain the completed `release_rehearsal.yml` with the original candidate evidence:

```sh
python tools/release_evidence.py rehearsal build/manual/release_rehearsal.yml
python tools/trace.py attest MAN-04 --attest-dir build/manual --commit <candidate-sha>
python tools/trace.py score --post-release --evidence build/trace --attest-dir build/manual --commit <candidate-sha>
python tools/release_evidence.py postdeploy <post-deploy-report.json>
python tools/release_evidence.py rollback <rollback-rehearsal.json>
```

Only valid MAN-04 awards the last point:
`SCORE 100/100 (automated 93/93, manual 7/7); MAN-04 PASS (post-release)`.
REQ-PKG-19 post-deploy and REQ-PKG-21 cleanup remain separately recorded, unscored validators.
Cleanup requires successful post-deploy verification plus the seven-day rollback window (`plan_cleanup`,
PT-21); retain the dry-run/removal log and protected files. Failed MAN-04 or critical post-deploy checks
require REQ-PKG-20 rollback: preserve 1.0.8 assets and sanitized v1 snapshot, never feed schema-2 settings
to v1, validate the rollback record. Missing/failed rehearsal cannot produce 100/100.
