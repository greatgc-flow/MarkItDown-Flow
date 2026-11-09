# R7 ratification (Fable): TDD kickoff vote + execution-plan vote

Reviewer: cc.fable. Date: 2026-11-09. Read: R7_cx_ratify.md, 30_TESTPLAN.md (DRAFT-2), 90_ACCEPTANCE.md (DRAFT-2), 20_SHELL.md, 25_PACKAGING.md; cross-checked against 10_SPEC.md DRAFT-3 (REQ list, §4, §5.1, §8.4, §10, §11) and 01_DECISIONS R19-R25. Repo tree inspected (v1 `src/`, `engine/src/`, `scripts/`, root TS build files still present). No commands run beyond read-only listing; `pip show markitdown-gc` was blocked in this sandbox (F-06).

Blocker test used: "can a correct red test with an unambiguous oracle be written from the docs for TDD steps 0-4 (TESTPLAN §6) today?" Only a NO blocks kickoff.

---

## 1. Doc-set ratification

Checks that pass (evidence):
- REQ closure: SPEC defines 111 REQ ids (GEN 10, SNF 10, TRI 5, CLS 6, SEL 2, PLN 8, CNV 5, RND 6, LKP 5, APR 7, TRX 6, ASM 14, WRT 2, RPT 3, CTR 4, MAP 8, SEC 10), SHELL 21, PKG 21 = 153; every id appears in TESTPLAN §4 (SEC-05 -> T-WRT-01, SEC-07 -> T-TRX-04 by marker). TESTPLAN names no undefined REQ.
- Stage axis: TESTPLAN S1..S13 == SPEC §4 (Select stage 4, Plan stage 8, Write stage 12). ACC gates reference only TESTPLAN ids; weights 93+7=100; no partial rubric (R21).
- Protocol: SHELL REQ-SHL-11 incorporates SPEC §7.3/8.4/10 by reference (R19); PKG has no handshake/staging/runtime pointer. R10/R15 honoured (REQ-SHL-01, REQ-SHL-10, REQ-PKG-05).
- Fixtures: expectations sourced from Core-generated goldens (R22); FX-11 `f1..f3`, FX-40 zero-byte -> E_CORRUPT, FX-49 reserved names, FX-17 duplicate ids, FX-44 case-fold collision all match SPEC DRAFT-3 corrections (R23).
- Code set: SHELL §6 = 28 E_ + 22 W_ = SPEC §7.5 (50) by inspection; JT-SHL-19-01 is the authority.
- Runner labels in ACC §1 == PKG REQ-PKG-07 (`windows-2022`, `ubuntu-24.04`, `macos-15-intel`).

Findings (none blocks step 0-2; owner and latest step given):

| ID | Sev | Location | Defect | Fix | Before step |
|---|---|---|---|---|---|
| F-01 | MAJOR | SPEC §1 glossary "Provider fingerprint" vs §5.1 Key (l.315: `raster_sha256, provider, model, destination, prompt_version, dpi`); TESTPLAN T-LKP-06 ("Key covers ... env names") | Key omits `command_env_names`; T-LKP-06 would test a non-normative claim (= cx T02). | SPEC §5.1: `Key = {raster_sha256, provider_fingerprint, dpi}`, `key_id = sha256(canonical_json(Key))`; ledger entry keeps `provider/model/destination/prompt_version/command_env_names` as informational fields. Rewrite T-LKP-06 oracle: changing `--command-env` set = miss; script body change = hit. Owner Fable (SPEC), cc (TESTPLAN). | 3 |
| F-02 | MINOR | TESTPLAN §1 `engine/mdflow/` vs plan P3 `engine/src/mdflow/` | Layout mismatch; `engine/src/` currently holds v1 wrapper + `__pycache__`. | Adopt src layout; edit TESTPLAN §1; pytest `--import-mode=importlib`, no `sys.path` hacks. | 0 |
| F-03 | MAJOR | SHELL REQ-SHL-15, PKG REQ-PKG-08 | `--yes-file` (SPEC APR-02/8.4/10.2) absent; both still say repeated `--yes HASH` (= cx T01). Valid syntax, but modal with 50 files should write a private `--yes-file`. | SHL-15: "write accepted hashes to an owned temp file, pass `--yes-file`, delete on exit"; PKG-08 oracle likewise. Owner cc. | 8 |
| F-04 | MAJOR | TESTPLAN FX-71, open item 2; ACC §6.1 | Shell process-layer tests (JT-11..17, PT-06/08) need streams recorded from the real engine; none exists yet. | Orchestrator records FX-71 with `tools/record_protocol.py` after engine step 7 is green; shell steps 9-10 wait for it; shell step 8 (pure) does not. | 9 |
| F-05 | MINOR | `docs/renewal/20_PACKAGING_RELEASE.md` | One-line SUPERSEDED stub remains; R22 layout lists 5 docs. | Delete in the v1-removal commit (C2). | 0 |
| F-06 | MAJOR | TESTPLAN step 1 (goldens, CT-01..14) | Needs `markitdown-gc` 0.3.5 importable in the orchestrator's Python. Earlier PKG draft reported local metadata 0.3.5; not re-verified here (pip blocked). Public artifacts remain TODO-VERIFY (REQ-PKG-04). | Orchestrator runs `python -c "import markitdown, markitdown.ocr_triage"` + version before step 1; if absent, step 1 blocks (step 0 and PURE steps 2-4 can proceed on mutated hand-reviewed goldens only if marked `golden-pending`; never commit them as goldens). | 1 |
| F-07 | MINOR | TESTPLAN T-SEC-02 (no FX), T-RPT-03 (no FX) | Oracle exists in SPEC §11 but no fixture named. | Add FX-61 (hostile text) / FX-67 to T-SEC-02; `all` to T-RPT-03. | 4 |
| F-08 | MINOR | ACC G-06 selector vs oracle | Selector lists 10 tests; oracle `-k` runs 4. Gate PASS requires all selector tests PASS anyway (rule §1 bullet 3), so no hole; but oracle output alone under-reports. | `-k` expression = full selector, or state "oracle = trace.py report filtered by selector". | 7 |
| F-09 | MINOR | TESTPLAN §0 `plat` rule vs ACC G-02 `skipped=0` | Consistent only if plat-excluded tests are *not collected* (deselected), not `skip`ped. | conftest: `pytest_collection_modifyitems` removes them; never `pytest.skip`. | 0 |

No finding makes a step 0-2 red test unwritable. cx R7 T03-T08 are accepted as MAJOR-during-TDD (T03 conversion read bounds: write CT test against installed Core first; T04 counters: SPEC 7.4 equations are already testable; T05-T07 have oracles in SPEC §11).

Readiness: 90/100 (F-01 and F-03/F-04 are scheduled work, not design gaps; F-06 is an environment check).

**VOTE-DOCS: APPROVE-TDD**

---

## 2. Execution-plan vote

| Item | Vote | Reasons / required change |
|---|---|---|
| P1 worktrees | CHANGE | **C1** A step-0 commit on `renewal/v2-zero-base` must precede the three engine/shell forks: `engine/src/mdflow/contracts.py` (TypedDicts: SniffResult, Classification, Unit, SelectedUnits, Plan, LedgerEntry, ProviderMeta, UnitResult; `CODES` from SPEC §7.5; `canonical_json`, `key_id`, exit map), `engine/tests/conftest.py` (req/cov/fx/plat markers -> junit, socket guard, fake clock, plat deselection per F-09), `tools/trace.py check` (minimal: registry + unknown/uncovered REQ), `pyproject.toml`, CI skeleton with T-META-01..04 red. Owner cx. Without it three worktrees invent three type sets and no marker discipline exists on day 1 (TESTPLAN §6 step 0, R20). **C3** Ledger must live in one worktree: wt-engine-core owns `ledger.py` entirely (Key, entry validation, store read/write, `--force`); wt-engine-io owns render/convert/transcribe/providers only. "ledger key" in core + "cache" in io splits one module across two branches. **C4** wt-pkg is not "then": trace.py/meta-tests/CI skeleton move into C1; only release workflow, attestations, lock build, PT-* stay last. **C9** wt-shell starts with step 8 (pure: migration, history, framing, i18n, redaction) only; steps 9-10 wait for FX-71 (F-04). |
| P2 red-green | CHANGE | **C5** Tighten: (a) red commit must *collect* (`pytest --collect-only` exit 0; stubs may `raise NotImplementedError`) and fail by assertion/NotImplementedError, never ImportError/SyntaxError; (b) `git diff <red> <green> -- engine/tests shell/test` is empty except added fixtures/goldens (tests are not edited to go green); (c) `trace.py check` green for the step's REQs at the green commit (TESTPLAN §6 rule); (d) orchestrator stores both run logs under `build/trace/redgreen/<step>-<peer>.log`. **C6** Goldens are generated only by the orchestrator (`tools/golden.py gen` against installed Core) in a `golden-update` commit; peers never hand-write `golden/<FX>/triage.json` (R22). Commit-message convention `test(red):`/`feat(green):` approved. |
| P3 package layout | CHANGE | **C7** `engine/src/mdflow/` + hatchling approved; update TESTPLAN §1 (F-02). Runtime dep `markitdown-gc>=0.3.5,<0.4` (REQ-GEN-02/REQ-PKG-03), lock exact 0.3.5. Test-only deps (`pytest`, `python-docx`, `python-pptx`, `openpyxl`, `pypdf`) in a separately pinned `engine/requirements-test.txt` with hashes (REQ-PKG-02), never in runtime deps. **C2** Delete v1 in the *first* commit of the branch, before wt-shell exists: `src/`, `engine/src/`, `engine/tests/`, `scripts/`, `main.ts`, `styles.css`, `esbuild.config.mjs`, `jest.config.js`, `tsconfig.json`, `version-bump.mjs`, `manifest-beta.json`, `plugin/`, `.eslintrc`, `.eslintignore`, root `package.json`/`package-lock.json` (new ones under `shell/`), `docs/0[1-5]_*` (v1 process docs), `docs/renewal/20_PACKAGING_RELEASE.md`. Keep `manifest.json`, `versions.json`, `LICENSE`, `README.md` (rewrite later per REQ-PKG-16), `CHANGELOG.md`, `.github/` (workflows rewritten in wt-pkg), `.editorconfig`, `.npmrc`. Reason: R15 requires that the clean-room worktree never contains v1 shell code; "same PR" is too late. Tag 1.0.8 is the archive (REQ-PKG-17); no new tag. |
| P4 recursive MECE | CHANGE | **C8** Matrices are generated (R20); auditors must therefore attack the only gameable surface: every `matrix.toml` N/A declaration (reason valid? cell truly unreachable?) plus docs<->code drift and oracle strength (does the assertion test the REQ or just run the code?). Define the peer-loop exit honestly: automated gates runnable by the orchestrator on one OS = G-01..G-08, G-10..G-12, G-16, G-17; G-09/G-13/G-14/G-15 need real 3-OS CI and M-01..04 need named humans. Peers may not claim 100/100; the loop target is "all orchestrator-runnable gates PASS + N/A list reviewed". |
| P5 quotas | APPROVE | Independent final reviewer (argon) receives: `SCORE.json`, `TRACE.md`, both `MATRIX_*.md`, the N/A list with reasons, red/green logs, SPEC §13 objections. One addition: F-01 SPEC amendment is Fable's, due before step 3. |

**VOTE-PLAN: CHANGE(C1 step-0 contracts+trace before fork; C2 delete v1 first commit; C3 ledger in one worktree; C5 red-green collect/no-test-edit rule; C7 src layout+pinned test deps; C8 honest loop exit + N/A audit)**
