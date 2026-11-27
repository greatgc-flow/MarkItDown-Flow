"""MarkItDown-Flow engine."""

import os

# The CLI can run without the shell. Opt out before Core imports Magika and ONNX Runtime.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

# Windows also exposes a process-level runtime switch. Set it before a Core session is constructed.
from .core_guard import quiet_output

with quiet_output():
    try:
        import onnxruntime
    except ModuleNotFoundError as error:
        if error.name != "onnxruntime":
            raise
    else:
        onnxruntime.disable_telemetry_events()

__version__ = "2.1.0"
