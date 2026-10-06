"""Idempotent demo workspace seeding for AI Company OS.

Seeding only ever happens when the Company Workspace is completely empty
(no profile and no datasets). Running it again on a populated workspace is a
safe no-op, so it can be wired into setup scripts or a demo bootstrap without
risking overwriting real user data.
"""

from pathlib import Path

from app.core.company_workspace import (
    load_company_profile,
    list_datasets,
    save_company_profile,
    save_dataset_bytes,
)

DEMO_DATASET_FILENAME = "video_games_sales.csv"

DEMO_DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "company_workspace"
    / "datasets"
    / DEMO_DATASET_FILENAME
)

DEMO_PROFILE = {
    "name": "NovaMart Interactive",
    "industry": "Video Games",
    "description": (
        "Global video game publisher and retailer. This demo workspace is "
        "seeded from the bundled video_games_sales.csv dataset."
    ),
    "website": "https://example.com",
    "headquarters": "Austin, TX",
    "stage": "Growth",
    "team_size": "120",
    "founded_year": "2012",
    "currency": "USD",
    "reporting_period": "Annual",
    "primary_kpi": "Revenue",
    "revenue_target": "1000000000",
    "growth_target": "15",
}


def workspace_is_empty():
    """Return True only when there is no profile and no connected dataset."""
    profile = load_company_profile()

    has_profile = bool(
        profile.get("name")
        or profile.get("industry")
        or profile.get("description")
    )

    return not has_profile and not list_datasets()


def seed_demo_workspace():
    """Populate the workspace with demo data once.

    Returns a status dictionary. The call is idempotent: a non-empty workspace
    is reported as ``skipped`` and left untouched.
    """

    if not workspace_is_empty():
        return {
            "status": "skipped",
            "message": "Workspace is not empty; demo seeding skipped.",
        }

    if not DEMO_DATASET_PATH.exists():
        return {
            "status": "error",
            "message": f"Demo dataset is missing: {DEMO_DATASET_PATH}",
        }

    data = DEMO_DATASET_PATH.read_bytes()

    try:
        info = save_dataset_bytes(DEMO_DATASET_FILENAME, data)
    except ValueError as exc:
        return {
            "status": "error",
            "message": f"Could not seed the demo dataset: {exc}",
        }

    save_company_profile(DEMO_PROFILE)

    return {
        "status": "success",
        "message": "Demo workspace seeded.",
        "dataset": info.get("filename"),
        "rows": info.get("rows"),
        "profile": DEMO_PROFILE["name"],
    }
