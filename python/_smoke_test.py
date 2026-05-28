"""Throwaway smoke test for the refactored helpers — not part of the plugin."""
import sys
sys.path.insert(0, '.')
import markitdown_wrapper as w

assert w.phase_result(content='x', status='y') == {'content': 'x', 'status': 'y'}
assert w.phase_result(content='x', status='y', model='m') == {'content': 'x', 'status': 'y', 'model': 'm'}
assert w.phase_result() == {'content': '', 'status': 'Skipped'}

assert w.mime_matches('image/png', ['image/']) is True
assert w.mime_matches('image/png', ['application/pdf']) is False
assert w.mime_matches('foo/bar', []) is True   # empty list = match-all
assert w.mime_matches('foo/bar', None) is True  # None = match-all

assert w.lazy_import('os') is not None
assert w.lazy_import('json', 'dumps') is not None
assert w.lazy_import('nonexistent_pkg_xyz_123') is None
assert w.lazy_import('os', 'nonexistent_attr_xyz') is None

print('OK — all helper assertions passed.')
