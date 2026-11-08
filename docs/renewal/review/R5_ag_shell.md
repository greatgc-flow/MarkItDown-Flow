### Adversarial Review: Obsidian Shell Specification (20_SHELL.md)

---

#### Finding 1
- **ID:** SHL-REV-01
- **Severity:** BLOCKER
- **Location:** REQ-SHL-02, REQ-SHL-12, Section 1
- **Issue:** Mobile compatibility violation. Spawning `enginePython` via Node `child_process` crashes on mobile (iOS/Android). The spec does not mandate setting `"isDesktopOnly": true` in `manifest.json` or guarding registration with `Platform.isDesktop`. Submitting without this violates Obsidian Community Plugin distribution standards.
- **Fix:** Explicitly mandate `"isDesktopOnly": true` in the manifest specification and wrap all lifecycle and command registrations with `Platform.isDesktop` guards.

#### Finding 2
- **ID:** SHL-REV-02
- **Severity:** BLOCKER
- **Location:** REQ-SHL-02, REQ-SHL-04, REQ-SHL-09, Section 1
- **Issue:** Policy disclosure omissions. The spec permits selecting files/folders outside the vault and egressing data to external endpoints (`api.openai.com`). Obsidian Developer Policy strictly requires clear README disclosures for (1) accessing files outside Obsidian vaults with rationale, and (2) all remote network endpoints and reasons. The spec mandates no such README clauses.
- **Fix:** Add a requirement mandating explicit README disclosure sections specifying out-of-vault read access justification and listing all supported remote LLM provider endpoints with data-handling statements.

#### Finding 3
- **ID:** SHL-REV-03
- **Severity:** MAJOR
- **Location:** REQ-SHL-05
- **Issue:** Secret exposure on migration failure. REQ-SHL-05 dictates that if migration or save fails, the shell must "leave original settings readable". This leaves v1 plaintext API keys (`llmApiKey`, `docintelCredential`) sitting exposed in `data.json` inside the vault, risking unintended sync via Obsidian Sync or Git.
- **Fix:** On migration error, immediately redact raw credentials in memory and replace failed disk state with an isolated, sanitized recovery placeholder rather than persisting raw secrets.

#### Finding 4
- **ID:** SHL-REV-04
- **Severity:** MAJOR
- **Location:** REQ-SHL-06
- **Issue:** Desktop GUI environment variable barrier. Relying solely on `process.env` for API keys breaks standard desktop UX: macOS and Windows applications launched via desktop shortcuts or Dock/Finder do not inherit user shell profiles (`.zshrc`, `.bashrc`). Users will encounter repeated `E_PROVIDER_CONFIG` failures.
- **Fix:** Support session-scoped, in-memory credential entry in the UI or integrate with the Obsidian SecretStorage API / OS keychain, preserving the zero-disk-persistence rule.

#### Finding 5
- **ID:** SHL-REV-05
- **Severity:** MAJOR
- **Location:** REQ-SHL-14, REQ-SHL-15
- **Issue:** Severe consent UX bottleneck. REQ-SHL-15 enforces that batch plans are approved and replayed one file at a time. Converting a folder with 50 files forces 50 consecutive blocking modal approvals.
- **Fix:** Add an aggregated batch consent modal displaying aggregate token/cost estimates and unit counts, allowing single-click authorization of the complete batch execution manifest.

#### Finding 6
- **ID:** SHL-REV-06
- **Severity:** MAJOR
- **Location:** REQ-SHL-16
- **Issue:** Windows descendant process leaks and untestable cancellation. `REQ-SHL-16` marks Windows signal/exit behavior and descendant cleanup as `TODO-VERIFY`. Node `process.kill()` on Windows does not propagate POSIX signals and regularly leaves orphaned Python worker processes locking files.
- **Fix:** Resolve `TODO-VERIFY` prior to freezing the spec: mandate Windows Job Objects (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) or `taskkill /F /T /PID` to guarantee tree termination within the 5-second deadline.

#### Finding 7
- **ID:** SHL-REV-07
- **Severity:** MAJOR
- **Location:** REQ-SHL-01, REQ-SHL-19, REQ-SHL-21
- **Issue:** Untestable requirements disguised as automated requirements. REQ-SHL-01 (clean-room compliance by "attestation") and REQ-SHL-19 (bilingual meaning verified by "named review") are governance declarations, not programmatically verifiable oracles. Marking them as `req("REQ-SHL-xx")` in Jest causes test suites to fake or bypass assertion logic.
- **Fix:** Move manual/legal attestations to governance verification checklists outside the automated test harness. Restrict `REQ-SHL-*` automated assertions strictly to machine-verifiable code behavior (e.g., schema validation, dictionary key parity).

#### Finding 8
- **ID:** SHL-REV-08
- **Severity:** MINOR
- **Location:** REQ-SHL-02
- **Issue:** Command palette pollution. Keeping `convert-url` permanently registered merely to display a static error notice ("URL import is unavailable") violates Obsidian UX norms by permanently cluttering the command palette with a dead command.
- **Fix:** Remove `convert-url` from active command registration. Deliver the legacy notice once during v1->v2 settings migration.

---

### Verdict
**APPROVE-WITH-CHANGES**

### Score
**68 / 100**
