"""R27 offline builder and frozen-asset integrity checks; no release success implied."""
import json
import shutil
import zipfile

import pytest

from _support import REPO, ASSETS, SUBJECTS, WHEEL, REFERENCE, load_py, sha256_file


@pytest.mark.req('REQ-PKG-01', 'REQ-PKG-02', 'REQ-PKG-14', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM9')
def test_T_GEN_54_r27_wheel_reproducible_and_every_frozen_asset_rejects_tampering(tmp_path):
    builder = load_py(REPO / 'tools/build_engine.py', 'build_engine')
    release = load_py(REPO / 'tools/build_release.py', 'mdflow_r27_release')
    first = tmp_path / 'candidate'
    wheel = builder.build(first)
    other = builder.build(tmp_path / 'repeat')
    assert wheel.name == WHEEL and wheel.read_bytes() == other.read_bytes()
    with zipfile.ZipFile(wheel) as archive:
        metadata = archive.read('mdflow-2.0.0.dist-info/METADATA').decode()
        dependency, = [line for line in metadata.splitlines() if line.startswith('Requires-Dist:')]
        assert 'markitdown-gc' in dependency and '>=0.3.5' in dependency and '<0.4' in dependency
        assert 'Tag: py3-none-any' in archive.read('mdflow-2.0.0.dist-info/WHEEL').decode()
    with pytest.raises(ValueError, match='refusing to replace'):
        builder.build(first)
    # Synthetic plugin bytes exercise verification only; never publication.
    (first / 'main.js').write_text('\n'.join(repr(c) for c in release.COMMANDS), encoding='utf-8')
    (first / 'styles.css').write_text('.r27 { color: inherit; }', encoding='utf-8')
    shutil.copyfile(REPO / 'manifest.json', first / 'manifest.json')
    for name in ('BOOTSTRAP.md', 'NOTICE.txt', 'LICENSE'):
        (first / name).write_text('Offline test fixture.\n', encoding='utf-8')
    reference = f'./{WHEEL} --hash=sha256:{sha256_file(wheel)}\n'
    (first / REFERENCE).write_text(reference, encoding='utf-8')

    def freeze():
        (first / 'SHA256SUMS').write_text(''.join(f'{sha256_file(first / n)}  {n}\n' for n in ASSETS), encoding='utf-8')
        candidate = {'tag': '2.0.0', 'reference_sha256': sha256_file(first / REFERENCE),
                     'draft_release': {'assets': [{'name': n, 'sha256': sha256_file(first / n)} for n in SUBJECTS]}}
        (first / 'release-candidate.json').write_text(json.dumps(candidate), encoding='utf-8')

    freeze()
    release.verify(first)
    for name in SUBJECTS:
        path = first / name
        original = path.read_bytes()
        try:
            path.write_bytes(original + b'\0')
            with pytest.raises(ValueError):
                release.verify(first)
        finally:
            path.write_bytes(original)
    # A rehashed manifest cannot silently bind a different wheel reference.
    (first / REFERENCE).write_text(reference.replace(sha256_file(wheel), '0' * 64), encoding='utf-8')
    freeze()
    with pytest.raises(ValueError, match='reference wheel hash differs'):
        release.verify(first)
