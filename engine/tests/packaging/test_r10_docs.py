"""Round-10 docs: handoff states the R35 release rule, round-9 changes are documented, counts and headers are current."""
import re

import pytest

from _support import REPO

DOCS = REPO / 'docs/renewal'


def read(relative):
    return (REPO / relative).read_text(encoding='utf-8')


@pytest.mark.req('REQ-PKG-10', 'REQ-PKG-16')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_93_handoff_changelog_readme_and_counts_match_round_9():
    handoff = read('docs/renewal/HANDOFF.md')
    assert '99/100' in handoff and 'deferred: post-release (R35)' in handoff and 'Round 9' in handoff
    assert '100/100' not in handoff and 'MAN-01..04' not in handoff
    argon = read('docs/renewal/review/FINAL_argon_acceptance.md').splitlines()
    assert argon[0].startswith('Superseded by R35 (owner decision): MAN-04 is post-release')

    changelog = read('CHANGELOG.md').split('\n## 0.1.0')[0]
    for item in ('Keep OCR pending', '~/.mdflow/cache', 'absolute PATH folders', '--command-env NAME',
                 'absolute source path', 'W_EXIFTOOL_UNUSABLE', 'billed'):
        assert item in changelog, item

    raw = (REPO / 'README.md').read_bytes()
    assert raw.count(b'\n') == raw.count(b'\r\n'), 'README must stay CRLF'
    readme = raw.decode('utf-8')
    assert re.search(r'^## Classification \(T, S, M\)\r$', readme, re.M)
    limits = re.search(r'^## Known limitations\r\n(.*?)(?=^## )', readme, re.M | re.S)[1]
    assert all(f'#{n}' in limits for n in (68, 69, 70, 71)) and '0.3.8' in limits
    assert 'standalone `png`, `jpg` and `jpeg`' in limits

    spec = read('docs/renewal/10_SPEC.md')
    section = spec.split('### 7.5 ')[1].split('\n\n')[0]
    table = [line for line in section.splitlines() if line.startswith('| `')]  # not the "Deleted:" line
    codes = set(re.findall(r'\b([EW]_[A-Z0-9_]+)', '\n'.join(table)))
    errors, warnings = sum(c[0] == 'E' for c in codes), sum(c[0] == 'W' for c in codes)
    assert f'({errors} E_ + {warnings} W_ = {len(codes)} codes)' in read('docs/renewal/30_TESTPLAN.md')
    version = re.search(r'Status: SPEC (DRAFT-[\d.]+)', spec)[1]
    acceptance = read('docs/renewal/90_ACCEPTANCE.md')
    assert f'Synced to SPEC {version},' in acceptance.splitlines()[2]
    fx71 = next(line for line in acceptance.splitlines() if line.startswith('1. FX-71 streams'))
    assert 'Round 9' in fx71
