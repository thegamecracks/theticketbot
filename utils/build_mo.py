"""Iterates through .po files in source packages and invokes msgfmt on them."""

import subprocess
from pathlib import Path

for po_path in Path("src").rglob("*.po"):
    print(po_path)
    output = po_path.with_suffix(".mo")
    subprocess.check_call(["msgfmt", "-o", output, po_path])
