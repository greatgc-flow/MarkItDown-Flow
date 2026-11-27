import json
from pathlib import Path

import pytest

from mdflow import cli


@pytest.mark.req("REQ-CLS-05", "REQ-RPT-01")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-02")
def test_T_CLI_09_strict_preview_then_explicit_partial(tmp_path, gen, capsys):
    root = tmp_path / 'sources'
    root.mkdir()
    (root / 'plain.txt').write_text('A complete note.', encoding='utf8')
    mixed = root / 'mixed.pdf'
    mixed.write_bytes(gen.pdf_mixed())
    out = tmp_path / 'out'
    assert cli.main(['run', str(root), '-o', str(out)]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [(row['outcome'], row['reason']) for row in rows if row['kind'] == 'file'] == [
        ('excluded', 'ocr_required'), ('complete', 'direct')]
    assert len(list(out.rglob('*.md'))) == 1
    before = set(tmp_path.rglob('*'))
    assert cli.main(['run', '--dry-run', str(mixed)]) == 0
    preview = [json.loads(line) for line in capsys.readouterr().out.splitlines()][1]
    assert preview['inspection']['inspected_pages'] == preview['inspection']['total_pages']
    assert set(tmp_path.rglob('*')) == before
    assert cli.main(['extract-text', str(mixed), '-o', str(out)]) == 0
    partial = list(out.rglob('*.text-only.md'))
    assert len(partial) == 1 and 'omitted' in partial[0].read_text(encoding='utf8').lower()
