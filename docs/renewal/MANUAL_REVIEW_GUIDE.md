# Manual review and release guide (2.0.0)

**한국어 요약.** 2.0.0 릴리스는 사람이 직접 하는 검토 4건(MAN-01~04)이 모두 통과해야 100/100이 됩니다.
(1) `2.0.0` 태그를 푸시하면 `release.yml`이 후보를 동결·증명·검증한 뒤 `accept-release`에서 멈춥니다. 이때 `frozen-candidate`
아티팩트를 내려받아 검토합니다. (2) `docs/renewal/manual-templates/`의 템플릿 4개를 `release-evidence/2.0.0/`에 복사해
`<…>` 자리표시자와 `TODO`를 모두 실제 값으로 채웁니다(MAN-01은 구현자와 검토자가 서로 달라야 합니다). 데스크톱 리허설은
3개 OS × Obsidian 최소/최신 = 6회입니다. (3) 그 브랜치에서 `evidence.yml`을 실행해 4개 파일을 검증하고
`named-release-evidence` 아티팩트를 만듭니다. (4) `gh workflow run release.yml -f evidence-run=<실행 ID>`로 게시합니다.
검증기는 형식과 후보 커밋 일치만 확인합니다. 내용이 사실인지는 검토자의 책임입니다.

---

## What this does and does not do

Four named human reviews are part of the 100/100 score (weights 3 + 2 + 1 + 1 = 7). `tools/trace.py attest`
checks that each review file is complete, names a reviewer, binds the **candidate commit**, and has every check
and the verdict at `PASS`. It cannot tell whether the claims are true. You (and the other named people) are the
evidence. A file that is filled in carelessly will pass validation and still be wrong.

| Gate | File (artifact root) | What the reviewer confirms |
|---|---|---|
| MAN-01 | `R15_cleanroom.yml` | The v2 shell was written from the spec and public Obsidian APIs only. v1 `src/`, `styles.css` and tests were not read. MIT credit is in README and LICENSE. **The implementer and the reviewer must be different named people.** |
| MAN-02 | `R16_readme_review.yml` | The README discloses network use, outside-vault access, no telemetry, account/key/cost and migration. Each is matched to an exact README heading and to the plugin's real behavior. |
| MAN-03 | `shell_i18n_review.yml` | A bilingual reviewer read every message row in English and Korean and the meanings are correct and equivalent. |
| MAN-04 | `release_rehearsal.yml` | The release-candidate assets were installed and exercised on real desktops: 3 OS x Obsidian minimum/current, six runs. |

## Step by step

1. **Get the release candidate.** Push the tag from the commit you intend to release:
   `git tag 2.0.0 <commit>` then `git push origin 2.0.0`. `release.yml` runs CI, freezes the candidate
   (`frozen-candidate` artifact), attests every subject, verifies on six targets, then **stops at `accept-release`**
   because no evidence exists yet. That stop is expected. The tag's commit is the *candidate commit*; copy its full
   40-hex SHA (`git rev-parse 2.0.0^{commit}`). Every review file must carry exactly this SHA, so do not move the tag.
   If you change anything, make a new commit, a new candidate and redo every review.
2. **Download the candidate.** From the release run: Actions > the `v2 release` run > Artifacts >
   `frozen-candidate`, or `gh run download <run-id> -n frozen-candidate -D candidate/`. It holds the nine release
   subjects: `main.js`, `manifest.json`, `styles.css`, `mdflow-2.0.0-py3-none-any.whl`, `reference-requirements.txt`,
   `BOOTSTRAP.md`, `NOTICE.txt`, `LICENSE`, `SHA256SUMS`. Digests: `sha256sum` (macOS/Linux) or
   `Get-FileHash -Algorithm SHA256` (Windows).
3. **Copy the templates** from `docs/renewal/manual-templates/` to `release-evidence/2.0.0/` on a new branch
   (for example `evidence/2.0.0`). Keep the four file names. Fill the `reviewer`, `date` (`YYYY-MM-DD`) and `commit`
   fields, replace every `<...>` placeholder, and change every `TODO` to `PASS` (only for checks that really passed;
   write `FAIL` if one did not and fix the problem before releasing). The evidence workflow rejects any remaining
   placeholder or `TODO`.
4. **MAN-04: run the rehearsal six times** (Windows, macOS, Linux; each with Obsidian's *minimum* supported version
   from `manifest.json` `minAppVersion` and the *current* release). On each, install from the downloaded assets (not
   from a build of your own) and perform the eleven checks listed in `release_rehearsal.yml`:
   `fresh_install`, `upgrade_from_1_0_8`, `rollback`, `consent_dismiss`, `consent_approve`, `mixed_document_mock_ocr`,
   `warm_rerun`, `cancel_restart` (real Windows cancellation on the Windows runs), `terminal_env_launch`, `commands`,
   `en_ko`. Record the Obsidian version, the Python version, and the SHA-256 of every downloaded asset. Engine must
   be `2.0.0` and Core `0.3.7`. Quote versions and digests in YAML so they stay text. `candidate_tag`,
   `manifest_version` and `versions_json_entry` must all be `2.0.0`.
5. **Run the other reviews.** MAN-01 (clean room: implementer and reviewer are two people), MAN-02 (read the README
   against the running plugin and cite headings), MAN-03 (read every en/ko row). Put the people's names in the files.
6. **Check locally (optional).** For each identity, from the repository root:
   `python tools/trace.py attest MAN-01 --attest-dir release-evidence/2.0.0 --commit <candidate-sha>` (repeat MAN-02,
   MAN-03, MAN-04). `python tools/release_evidence.py rehearsal release-evidence/2.0.0/release_rehearsal.yml` checks
   the MAN-04 structure alone. PyYAML is needed for `.yml` files (`pip install -r engine/requirements-build.txt`).
7. **Run `evidence.yml`.** Commit and push the branch, then run the workflow from it:
   `gh workflow run evidence.yml --ref evidence/2.0.0 -f path=release-evidence/2.0.0 -f candidate=2.0.0`
   (`candidate` accepts the tag or a full SHA). It resolves the candidate commit, validates all four files with
   `tools/trace.py attest`, and only if all four pass uploads artifact `named-release-evidence` with the four files at
   its root. Any failure fails the run and uploads nothing. Note the run ID from `gh run list --workflow evidence.yml`.
8. **Publish.** `gh workflow run release.yml --ref 2.0.0 -f evidence-run=<evidence run id>`. `release.yml` must run
   on the tag ref so that it scores the exact candidate; it downloads `named-release-evidence` from that run into
   `build/manual/`, scores 100/100, and publishes the draft release with the tested bytes.

## Known gap: other files in `build/manual/`

`tools/release_gate.py` also reads `oracles.json`, `actions-review.json`, `pkg04_core_artifacts.json` and
`listing-review.json` from the same evidence folder (see 90_ACCEPTANCE E-15). `evidence.yml` stages and uploads **only
the four MAN files**, so without a separate source for those four JSON records `accept-release` will stop on a missing
file. Producing them is outside this procedure.
