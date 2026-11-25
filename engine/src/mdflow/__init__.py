"""MarkItDown-Flow engine."""

import os

# The CLI can run without the shell. Opt out before Core imports Magika and ONNX Runtime.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

__version__ = "2.0.2"
