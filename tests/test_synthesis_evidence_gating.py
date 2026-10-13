"""Regression tests: evidence-gated sales recommendations + synthesis failure reason.

Covers two issues:
1. The deterministic sales-pattern guidance must be derived only from verified
   evidence. When a dataset lacks region and/or product fields, recommendations
   and the executive summary must recommend data validation / collecting the
   missing fields instead of claiming a "weakest region" or "underperforming
   product segment".
2. When Nemotron synthesis fails (empty content or finish_reason="length"), the
   company investigation must preserve the real failure reason so the two cases
   are distinguishable, without inflating max_tokens.
"""

import pytest

import app.core.commander as commander
import app.core.company_workspace as company_workspace
import app.database.db as database
from app.core.company_context import build_company_dataset_evidence
from app.core.evidence_reasoning import build_reasoning_pack


# Dataset WITH verified region, product and monthly fields.
REGION_PRODUCT_CSV = (
    b"Row ID,Order ID,Order Date,Region,Product Name,Sales\n"
    b"1,O1,2024-01-05,North,Alpha,1000\n"
    b"2,O2,2024-01-15,South,Beta,100\n"
    b"3,O3,2024-02-10,North,Alpha,800\n"
    b"4,O4,2024-02-20,South,Beta,60\n"
    b"5,O5,2024-03-05,North,Alpha,600\n"
    b"6,O6,2024-03-15,South,Beta,20\n"
)

# Dataset WITHOUT region, product or monthly fields (mirrors video_games_sales).
GENERIC_CSV = (
    b"Rank,Name,Platform,Year,Genre,Publisher,NA_Sales,EU_Sales,JP_Sales,Other_Sales,Global_Sales\n"
    b"1,GameA,X360,2010,Action,Pub1,100,50,20,10,180\n"
    b"2,GameB,PS3,2011,Adventure,Pub2,80,60,30,5,175\n"
    b"3,GameC,Wii,2012,Sports,Pub3,50,90,10,15,165\n"
    b"4,GameD,PC,2013,Action,Pub1,200,40,25,8,273\n"
)

PATTERN_QUESTION = (
    "What are the strongest and weakest sales patterns in the current dataset "
    "across regions, products, and time, and what should management investigate "
    "first to improve sales performance?"
)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    workspace_dir = tmp_path / "company_workspace"
    monkeypatch.setattr(company_workspace, "WORKSPACE_DIR", workspace_dir)
    monkeypatch.setattr(
        company_workspace, "UPLOAD_DIR", workspace_dir / "datasets"
    )
    monkeypatch.setattr(
        company_workspace,
        "PROFILE_PATH",
        workspace_dir / "company_profile.json",
    )
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "history.db")
    company_workspace.initialize_workspace()
    return tmp_path


def _seed_generic():
    company_workspace.save_dataset_bytes("generic_sales.csv", GENERIC_CSV)


def _seed_region_product():
    company_workspace.save_dataset_bytes("train.csv", REGION_PRODUCT_CSV)


# ---------------------------------------------------------------------------
# Issue 2: evidence-gated recommendations / executive summary
# ---------------------------------------------------------------------------

def test_generic_dataset_does_not_claim_weakest_region_or_product(workspace):
    _seed_generic()
    pack = build_reasoning_pack(
        PATTERN_QUESTION, build_company_dataset_evidence(PATTERN_QUESTION)
    )

    draft = pack["executive_summary_draft"]

    # No region/product data exists, so no such claims may be made.
    assert "weakest region" not in draft.lower()
    assert "underperforming product" not in draft.lower()
    # Guidance instead points at the missing fields.
    assert "Collect or validate region and product data" in draft


def test_generic_dataset_recommends_validation_not_region_product(workspace):
    _seed_generic()
    pack = build_reasoning_pack(
        PATTERN_QUESTION, build_company_dataset_evidence(PATTERN_QUESTION)
    )

    statements = " ".join(
        item["statement"] for item in pack["recommendations"]
    )

    assert "Validate or collect the region and product field(s)" in statements
    assert "Investigate regional, product, and time-based" not in statements


def test_region_product_dataset_preserves_existing_behavior(workspace):
    _seed_region_product()
    pack = build_reasoning_pack(
        PATTERN_QUESTION, build_company_dataset_evidence(PATTERN_QUESTION)
    )

    draft = pack["executive_summary_draft"]

    assert "weakest region" in draft.lower()
    assert "underperforming product" in draft.lower()

    statements = " ".join(
        item["statement"] for item in pack["recommendations"]
    )
    assert "South" in statements
    assert "underperforming product segment" in statements


# ---------------------------------------------------------------------------
# Issue 1: preserve the real Nemotron failure reason
# ---------------------------------------------------------------------------

def test_length_failure_reason_is_preserved(workspace, monkeypatch):
    _seed_generic()

    reason = (
        "Nemotron stopped early (finish_reason='length') and returned "
        "incomplete output."
    )

    def failing_completion(**kwargs):
        raise ValueError(reason)

    monkeypatch.setattr(commander, "get_completion", failing_completion)

    result = commander.run_commander_task("t-length", PATTERN_QUESTION)

    synthesis = result["metrics"]["nvidia_synthesis"]

    assert synthesis["synthesis_fallback"] is True
    assert synthesis["synthesis_failure_reason"] == reason
    assert "finish_reason='length'" in synthesis["executive_summary"]


def test_empty_content_reason_is_preserved(workspace, monkeypatch):
    _seed_generic()

    reason = "Nemotron returned empty content. Finish reason: stop."

    def failing_completion(**kwargs):
        raise ValueError(reason)

    monkeypatch.setattr(commander, "get_completion", failing_completion)

    result = commander.run_commander_task("t-empty", PATTERN_QUESTION)

    synthesis = result["metrics"]["nvidia_synthesis"]

    assert synthesis["synthesis_fallback"] is True
    assert synthesis["synthesis_failure_reason"] == reason
    assert "empty content" in synthesis["executive_summary"]


def test_success_has_no_failure_reason(workspace, monkeypatch):
    _seed_generic()

    monkeypatch.setattr(
        commander,
        "get_completion",
        lambda **kwargs: "Executive summary text.",
    )

    result = commander.run_commander_task("t-ok", PATTERN_QUESTION)

    synthesis = result["metrics"]["nvidia_synthesis"]

    assert synthesis["synthesis_fallback"] is False
    assert synthesis["synthesis_failure_reason"] is None
    assert synthesis["executive_summary"] == "Executive summary text."