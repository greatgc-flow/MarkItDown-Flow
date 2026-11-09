"""Reject the upstream distribution sharing the fork's import namespace."""
from importlib import metadata


class CoreConflict(RuntimeError):
    """A broken environment, independent of any document's contents."""


def check() -> None:
    # Do not cache: embedded callers can change sys.path during their lifetime.
    try:
        metadata.distribution('markitdown')
    except metadata.PackageNotFoundError:
        return
    raise CoreConflict('E_CORE_CONFLICT: upstream markitdown is installed alongside markitdown-gc; '
                       'remove markitdown or create a dedicated mdflow virtual environment.')
