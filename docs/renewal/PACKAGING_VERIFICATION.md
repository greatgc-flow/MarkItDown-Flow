# Step 11 packaging verification (2026-11-09)

The implementation prepares candidates and refuses incomplete release evidence.
No release, target installation, attestation, listing update or desktop rehearsal
has been executed by this workspace task. Pytest is reserved for the orchestrator.

## Dependency provenance and remaining lock work

`pip index versions markitdown-gc` was attempted with an explicit PyPI index and
Python 3.14 selection. It returned no matching distribution in this sandbox.
Direct HTTPS from Python failed with WinError 10061. Web retrieval of the fork's
[0.3.5 JSON](https://pypi.org/pypi/markitdown-gc/0.3.5/json) and version page
returned cache misses. These failures do not establish package nonexistence.

The local pip HTTP cache contains PEP 691 PyPI index snapshots and the actual
0.3.5 wheel. `engine.lock` records 41 distribution/version branches with actual
wheel SHA-256 values from those snapshots. `lock-inventory.json` preserves each
artifact URL/hash and license metadata, identifies this cached provenance, and
lists every unresolved check. Magika and its transitive closure, pandas 2.x's
pytz closure, and selected older-branch metadata remain unresolved. This is a
candidate snapshot, **not a complete release-installable lock**. The builder
refuses an inventory with any unresolved entries. Missing hashes are never
invented, and upstream markitdown is never substituted.

To finish the reviewed lock, run `python tools/lock_engine.py --report <file>
--runner <label>` in each real target interpreter/OS, then merge all fifteen
3.10-3.14 target reports with `--merge <files...>`. This is an explicit
maintainer update, not an installation/build-time upgrade. The merger requires
all advertised cells, exact Core 0.3.5, wheel-only resolution, public artifact
hashes and license metadata. `--wheel <path>` additionally freezes the local
2.0.0 engine wheel hash; the candidate builder checks it when present.

Test pins were updated from available registry snapshots. Public pages also
confirm [pypdf 7.0.0](https://pypi.org/project/pypdf/),
[Pillow 12.3.0 for Python 3.10](https://pypi.org/project/pillow/12.3.0/),
[Pillow 13.0.0 for Python 3.11+](https://pypi.org/project/pillow/),
[exceptiongroup 1.3.1](https://pypi.org/project/exceptiongroup/), and
[tomli 2.5.0](https://pypi.org/project/tomli/). Python markers keep the Python 3.10
branch compatible. Build/bootstrap tools have their own pins. Node 24.22.2 is
an exact 24.x patch found in the official
[Node release index](https://nodejs.org/dist/index.json).

## Candidate and execution gates

`build_engine.py --wheel-only` successfully builds mdflow 2.0.0 as a pure-Python
wheel. Repeated fixed-epoch builds are compared locally for determinism. The
complete engine ZIP is gated on the inventory above. Dependencies may contain
native wheels. The ZIP uses an explicit member list, includes bootstrap,
licenses and inventory, and shares its exact lock bytes with the release asset.

The current `shell/package.json` still has the step-10 build placeholder, and
production `main.js`/`styles.css` are absent. The candidate builder calls the
actual shell build and requires both outputs. It does not fabricate attachments
or reuse retired implementation assets. Trace registration currently reports
13 missing shell requirement/test registrations; its two matrix checks have no
coverage errors. These are independent upstream gates, not packaging successes.

CI is reusable and runs the required six engine cells, three experimental 3.15
cells, three shell cells, Core endpoints, and nine intermediate-Python smokes.
Packaged checks use hash-mode installs in new fixed-location environments and
run outside sources. The code-set rerun preserves the full Jest results.
Contract-max visibly deduplicates when the newest resolved Core is 0.3.5;
resolver errors remain fatal. Trace reports registration matrices separately
from executed automated results and named manual reviews. Missing evidence
currently yields SCORE 0/100; no sign-off or score has been fabricated.

All external action identities match the candidate SHAs in 25_PACKAGING.
Ownership/implementation/transitive dependency security review still requires
an independently supplied `actions-review.json`, bound to the candidate commit;
SHA identity alone does not complete that review. GitHub CLI version/verification
flags, attestation eligibility, real target installs and the minimum/current
Obsidian versions remain release gates.

## Manual inputs and publication

A tag must equal 2.0.0 without a v prefix and match every manifest/package/engine
version. A release dispatch must select that tag. Supply a
`named-release-evidence` artifact from the indicated evidence run containing
MAN-01..04 records (filenames in `tools/trace.py`), `oracles.json`,
`actions-review.json`, `pkg04_core_artifacts.json`, and `listing-review.json`.
Each review binds the actual commit and names its reviewer; MAN-01 also names a
different implementer. Receipts preserve command, exit code, stdout and commit.
They never substitute for test execution or the human review itself.

The release workflow reuses one candidate, verifies transfer hashes, separates
attestation privileges from contents-write privileges, retains six individual
Sigstore bundles, and constrains verification to repository/workflow/source SHA.
It creates a draft with explicit assets, downloads the attachments, and compares
the remote hashes before returning. It does not overwrite an existing release
or publish automatically. The acceptance report is release-candidate.json and
the CI evidence artifacts. Manual publication, community-listing install/update,
post-deploy verification, rollback and the seven-day cleanup window remain the
release operator's documented procedure. No cleanup of user data is performed.
