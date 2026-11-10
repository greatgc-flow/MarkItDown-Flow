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
    assert 'MAN-01..04' not in handoff
    pending = next(line for line in handoff.splitlines() if line.startswith('Pending before 2.0.0'))
    assert 'trace.py score' in pending and '99/100' in pending
    assert 'C3' in handoff
    argon = read('docs/renewal/review/FINAL_argon_acceptance.md').splitlines()
    assert argon[0].startswith('Superseded by R35 (owner decision): MAN-04 is post-release')
    assert 'may be released at' in argon[0] and 'MAN-01..03' in argon[0]
    decisions = read('docs/renewal/01_DECISIONS.md')
    r4 = next(line for line in decisions.splitlines() if line.startswith('| R4 '))
    assert '(plugin location superseded by R38)' in r4

    changelog = read('CHANGELOG.md').split('\n## 0.1.0')[0]
    for item in ('Keep OCR pending', '~/.mdflow/cache', 'absolute PATH folders', '--command-env NAME',
                 'absolute source path', 'W_EXIFTOOL_UNUSABLE', 'billed', 'launches no conversion',
                 '(C3)', '`*_CREDENTIAL`', '`max_requests`'):
        assert item in changelog, item
    assert 'reruns the original command' not in changelog
    assert changelog.index('### Removed') < changelog.index('### Security')

    raw = (REPO / 'README.md').read_bytes()
    assert b'\r' not in raw, 'README follows the repository LF policy (.gitattributes: * text=auto eol=lf)'
    readme = raw.decode('utf-8')
    classification = re.search(r'^## Classification \(T, S, M\)\n(.*?)(?=^## )', readme, re.M | re.S)[1]
    for item in ('Remote OCR', 'Closing the dialog converts nothing', 'only reported',
                 '`python -I -m mdflow classify <PATH>`'):
        assert item in classification, item
    assert 'every class' not in classification and 'no usable text layer' not in classification
    limits = re.search(r'^## Known limitations\n(.*?)(?=^## )', readme, re.M | re.S)[1]
    assert all(f'#{n}' in limits for n in (68, 69, 70, 71)) and '0.3.8' in limits
    assert 'standalone `png`, `jpg` and `jpeg`' in limits

    spec = read('docs/renewal/10_SPEC.md')
    section = spec.split('### 7.5 ')[1].split('\n\n')[0]
    table = [line for line in section.splitlines() if line.startswith('| `')]  # not the "Deleted:" line
    codes = set(re.findall(r'\b([EW]_[A-Z0-9_]+)', '\n'.join(table)))
    errors, warnings = sum(c[0] == 'E' for c in codes), sum(c[0] == 'W' for c in codes)
    testplan = read('docs/renewal/30_TESTPLAN.md')
    assert f'({errors} E_ + {warnings} W_ = {len(codes)} codes)' in testplan
    shell = read('docs/renewal/20_SHELL.md').split('| Engine error code |')[1].split('| Shell diagnostic key |')[0]
    assert set(re.findall(r'^\| `([EW]_[A-Z0-9_]+)`', shell, re.M)) == codes
    assert testplan.index('| T-META-92 |') < testplan.index('| T-META-93 |') < testplan.index('| T-META-94 |')
    version = re.search(r'Status: SPEC (DRAFT-[\d.]+)', spec)[1]
    acceptance = read('docs/renewal/90_ACCEPTANCE.md')
    assert f'Synced to SPEC {version},' in acceptance.splitlines()[2]
    fx71 = next(line for line in acceptance.splitlines() if line.startswith('1. FX-71 streams'))
    assert 'Round 9' in fx71
