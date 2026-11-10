"""Program lookup that never searches the current folder (security review C1)."""

from __future__ import annotations

import os


def resolve_executable(name: str, search_path: str) -> str | None:
    """Absolute path of the bare program ``name`` found in an absolute ``search_path`` entry, else ``None``.

    Empty, ``.`` and relative entries are skipped: on Windows ``shutil.which`` (3.10-3.11 always, 3.12+ unless
    ``NoDefaultCurrentDirectoryInExePath`` is set) and ``CreateProcess`` would otherwise run a program planted in
    the current folder. On Windows each ``PATHEXT`` extension is tried; a name already carrying one is tried as is.
    """
    extensions = [""]
    if os.name == "nt":
        known = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep) if e]
        has_known = os.path.splitext(name)[1].upper() in {e.upper() for e in known}
        extensions = ([""] if has_known else []) + known
    for folder in search_path.split(os.pathsep):
        if not folder or not os.path.isabs(folder):
            continue
        for extension in extensions:
            candidate = os.path.join(folder, name + extension)
            if os.path.isfile(candidate) and (os.name == "nt" or os.access(candidate, os.X_OK)):
                return candidate
    return None


def resolve_override(value: str, search_path: str) -> str | None:
    """A ``*_PATH`` override: a bare name is looked up like ``resolve_executable``; a path is the user's choice."""
    return value if os.path.dirname(value) else resolve_executable(value, search_path)
