"""The peer-review archive is one index of permalinks; live docs link only to files that exist."""
import re

import pytest

from _support import REPO

REVIEW = REPO / 'docs/renewal/review'
PERMALINK = 'https://github.com/greatgc-flow/MarkItDown-Flow/blob/d3df2524be63ad82f9c706545de15a5c1be78155/docs/renewal/review/'
KEPT = {'INDEX.md', 'MAN01_access_record.md', 'FINAL_argon_acceptance.md'}


@pytest.mark.req('REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_99_review_archive_index_permalinks_and_short_handoff():
    assert {path.name for path in REVIEW.iterdir()} == KEPT
    index = (REVIEW / 'INDEX.md').read_text(encoding='utf-8')
    archived = re.findall(re.escape(PERMALINK) + r'([A-Za-z0-9_]+\.md)\)', index)
    assert len(archived) == len(set(archived)) == 35 and not KEPT & set(archived)
    for doc in REPO.glob('docs/renewal/*.md'):
        for target in re.findall(r'\]\(review/([^)#]+)', doc.read_text(encoding='utf-8')):
            assert (REVIEW / target).is_file(), f'{doc.name} -> review/{target}'
    handoff = (REPO / 'docs/renewal/HANDOFF.md').read_text(encoding='utf-8').splitlines()
    assert len(handoff) <= 15
