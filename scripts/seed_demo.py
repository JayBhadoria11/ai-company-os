"""Seed the AI Company OS demo workspace.

Usage (from the project root)::

    python scripts/seed_demo.py

The seeder is idempotent and only runs when the Company Workspace is empty.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.demo_seed import seed_demo_workspace


def main():
    result = seed_demo_workspace()
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") in {"success", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
