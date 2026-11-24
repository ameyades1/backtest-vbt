"""Retired: the live tool for S44984096 is now the release version.

    python release/s44984096/live.py report --refresh      (from the repo root)

This stub forwards every command to it, so old habits still work and there is only one live tool writing to live/.
The old research version (with --month-end) is in git history before this commit.
"""
import runpy, sys
from pathlib import Path

REL = Path(__file__).resolve().parents[1] / "release" / "s44984096" / "live.py"
if __name__ == "__main__":
    if "--month-end" in sys.argv:
        sys.exit("--month-end is not supported: the release live.py finds month ends itself.")
    print(f"note: forwarding to {REL.relative_to(REL.parents[2])}\n", file=sys.stderr)
    sys.argv[0] = str(REL)
    sys.path.insert(0, str(REL.parent))
    runpy.run_path(str(REL), run_name="__main__")
