# Shell implementation inputs for the 2.1 candidate

Codex primary implemented the strict workflow on the maintained 2.0.2 baseline at b9cc63551e79e8ee0038fbadcdadd610f3206a65. The behavioral inputs were the product owner's instructions and the [English specification](PRE_TDD_SPEC_EN.md). The Obsidian integration used the current v2 TypeScript shell, its mock and contract tests, and the public Obsidian API types installed by the project. The engine integration used the maintained Flow and Core sources, their test fixtures, and the versioned CLI and Python interfaces.

I did not consult v1 plugin implementation files, v1 styles or v1 tests to implement the 2.1 shell. Checking project history, release metadata, attribution notices and the 2.0.2 README served the compatibility and licensing review. The earlier v2 clean-room access record is at [MAN01_access_record.md](../renewal/review/MAN01_access_record.md). This declaration covers my work on the 2.1 change. The independent reviewer records their own findings separately.

Implementer identity: codex-primary/codex/GPT-6.
