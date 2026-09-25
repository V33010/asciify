from __future__ import annotations

import sys
from pathlib import Path

# Keep the test suite runnable directly from a source checkout without first
# installing the maturin package.  This also lets Python-only tests run when
# the Rust extension has not been built yet.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
