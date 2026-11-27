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


@pytest.mark.req("REQ-CLS-05", "REQ-RPT-01")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-03")
def test_T_CLI_10_scan_on_final_page_and_digest_bound_handoff(tmp_path, gen, capsys):
    import hashlib
    source = tmp_path / "100.pdf"
    source.write_bytes(gen.make_pdf([{"text": "Visible text"}] * 99 + [{"image_seed": 10}]))
    out = tmp_path / "out"

    def run(*args, expected=0):
        assert cli.main(list(map(str, args))) == expected
        return [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    original = source.read_bytes()
    sha = hashlib.sha256(original).hexdigest()
    preview = run("run", "--dry-run", source)[1]
    assert preview["reason"] == "ocr_required"
    assert preview["inspection"]["pages"][-1] == {"number": 100, "role": "ocr"}
    assert preview["inspection"]["measured_pages"] == 100
    assert abs(sum(preview["inspection"]["area_percent"].values()) - 100) <= 0.2
    assert run("run", source, "-o", out)[1]["outcome"] == "excluded"
    assert not out.exists()
    args = ["handoff-copy", source, "--sha256", sha, "--original-sha256", sha, "-o", out]
    copy = run(*args)[0]
    assert Path(copy["output"]).read_bytes() == original
    assert run(*args)[0]["status"] == "reused"
    partial_args = ["extract-text", source, "-o", out, "--expected-sha256", sha]
    partial = run(*partial_args)[1]
    note = Path(partial["output"])
    assert note.read_text().count("Visible text") == 99
    note.write_text("Owner edit")
    assert run(*partial_args, expected=2)[1]["action"] == "edited_output"
    assert note.read_text() == "Owner edit"
    source.write_bytes(gen.pdf_scan())
    assert run(*args, expected=2)[0]["status"] == "source_changed"


@pytest.mark.req("REQ-CLS-05", "REQ-RPT-01")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-02")
def test_T_CLI_11_strict_mode_cannot_accept_legacy_egress_or_write_during_preview(tmp_path, gen, capsys):
    source = tmp_path / "scan.pdf"
    source.write_bytes(gen.pdf_scan())
    out = tmp_path / "out"
    for args in (["--dry-run", "-o", str(out)], ["--dry-run", "--provider", "command"], ["--dry-run", "--yes"]):
        assert cli.main(["run", str(source), *args]) == 1
        assert capsys.readouterr().out == ""
    assert cli.main(["extract-text", str(source), "-o", str(out)]) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[1])
    assert row["action"] == "no_usable_text" and not out.exists()
