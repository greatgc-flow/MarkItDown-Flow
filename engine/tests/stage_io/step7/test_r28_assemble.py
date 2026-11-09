"""R28 Assemble floor: consume text/G2b/mismatch/directory fixtures explicitly."""
import json

import pytest


@pytest.mark.req('REQ-ASM-01', 'REQ-ASM-02', 'REQ-ASM-03', 'REQ-GEN-07')
@pytest.mark.cov('S11', 'FM0')
@pytest.mark.fx('FX-28', 'FX-31', 'FX-41', 'FX-51')
@pytest.mark.parametrize('case', ['text', 'g2b', 'mismatch', 'directory'])
def test_T_ASM_51_r28_convert_only_classes_and_directory_keep_base_and_provenance(flow, gen, case):
    names = {
        'text': ('memo.txt', gen.txt_utf8(), 'txt'),
        'g2b': ('page.html', b'<html><body>Own HTML fixture<img src="image.png"></body></html>', 'html'),
        'mismatch': ('renamed.docx', gen.pdf_text(), 'pdf'),
        'directory': ('nested/memo.txt', gen.txt_utf8(), 'txt'),
    }
    name, data, fmt = names[case]
    flow.put(name, data)
    # Core conversion is the controlled S5 boundary; assembly must preserve it.
    base = 'Converted base for ' + case + '\n\n**Own content.**\n'
    flow.core.behavior = lambda *args: base
    result = flow.run()
    assert len(result['files']) == 1
    entry = result['files'][0]
    assert entry['path'] == name and entry['format'] == fmt and entry['action'] == 'convert_only', json.dumps(entry)
    assert entry['outputs'] == [name + '.md'] and entry['placements'] == 0
    output = (flow.out / (name + '.md')).read_text(encoding='utf-8')
    header, body = output[4:].split('---\n', 1)
    fields = {k: json.loads(v) for line in header.splitlines() for k, v in [line.split(': ', 1)]
              if k in {'source', 'format', 'sha256'}}
    assert fields['source'] == name and fields['format'] == fmt and fields['sha256'] == gen.sha256(data)
    assert base.strip() in body and 'mdflow:pending' not in body
    assert not any(entry['requests'].values())
    assert sorted(p.relative_to(flow.out).as_posix() for p in flow.out.rglob('*') if p.is_file()) == [name + '.md']
