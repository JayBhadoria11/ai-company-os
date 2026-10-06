"""The synthesis prompt must receive bounded, non-duplicated evidence.

A very large dataset (e.g. a 400k-row train.csv) produces a large deterministic
analysis. The prompt sent to Nemotron must not ship every raw breakdown or
duplicate the reasoning arrays, or the model can exhaust its output budget and
return finish_reason="length" with empty content. These tests lock in the
bounded, de-duplicated synthesis context while proving the full deterministic
analysis is still retained.
"""

import json

import pytest

import app.core.commander as commander
import app.core.company_workspace as company_workspace
import app.database.db as database
from app.core.company_context import build_company_dataset_evidence
from app.core.evidence_reasoning import build_reasoning_pack


def _large_csv():
    """A dataset large enough to exercise the evidence caps."""
    header = (
        "Row ID,Order ID,Order Date,Region,Product Name,Category,"
        "Marketing Channel,Sales,Quantity,Discount"
    )
    rows = [header]
    rid = 0
    regions = ["North", "South", "East", "West", "Central", "Northeast",
               "Southwest", "Midwest", "Southeast", "Northwest"]
    channels = ["Online", "Retail", "Partner", "Direct"]
    for year in range(2022, 2025):
        for month in range(1, 13):
            for pid in range(60):
                rid += 1
                region = regions[pid % len(regions)]
                channel = channels[pid % len(channels)]
                sales = 100 + (pid % 37) - (month * 2)
                rows.append(
                    f"{rid},O{rid},{year}-{month:02d}-15,{region},"
                    f"Product{pid},Cat{pid % 40},{channel},{sales},"
                    f"{1 + (pid % 5)},0"
                )
    return "\n".join(rows).encode()


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


def _seed():
    company_workspace.save_dataset_bytes("train.csv", _large_csv())


def _build_context(query):
    combined = build_company_dataset_evidence(query)
    reasoning = build_reasoning_pack(query, combined)
    return combined, reasoning


def test_compact_evidence_omits_huge_cross_tabs(workspace):
    _seed()
    combined, _ = _build_context(
        "What are the strongest and weakest sales patterns across regions, "
        "products, and time, and what should management investigate first?"
    )

    digest = commander._compact_evidence_for_prompt(combined["evidence"])

    payload = digest["train.csv"]
    # The cross-tab arrays that the reasoning pack never uses are gone.
    for key in ("product_region", "product_channel", "sellers", "reviews", "payments"):
        assert key not in payload

    # The digest is bounded to small, decision-relevant slices.
    assert len(payload["top_products"]) <= commander._EVIDENCE_PRODUCTS
    assert len(payload["top_regions"]) <= commander._EVIDENCE_REGIONS
    assert len(payload["monthly"]) <= commander._EVIDENCE_MONTHS
    assert len(payload["channels"]) <= commander._EVIDENCE_CHANNELS


def test_compact_reasoning_drops_raw_pattern_arrays(workspace):
    _seed()
    _, reasoning = _build_context(
        "What are the strongest and weakest sales patterns across regions, "
        "products, and time, and what should management investigate first?"
    )

    compact = commander._compact_reasoning_for_prompt(reasoning)

    pattern = compact["sales_pattern"]
    # Computed summary values are preserved ...
    assert pattern["strongest_region"] is not None
    assert pattern["weakest_region"] is not None
    assert "strongest_month" in pattern
    # ... while the raw lists that duplicated the evidence digest are dropped.
    for key in ("regions", "products", "monthly"):
        assert key not in pattern


def test_compact_serialization_is_smaller_than_raw(workspace):
    _seed()
    combined, reasoning = _build_context(
        "What are the strongest and weakest sales patterns across regions, "
        "products, and time, and what should management investigate first?"
    )

    raw = (
        json.dumps(reasoning, indent=2, default=str)
        + json.dumps(combined["evidence"], indent=2, default=str)
    )

    compact = commander._bounded_json(
        commander._compact_evidence_for_prompt(combined["evidence"]),
        commander.SYNTHESIS_EVIDENCE_CHAR_LIMIT,
    )
    compact += json.dumps(
        commander._compact_reasoning_for_prompt(reasoning),
        separators=(",", ":"),
        default=str,
    )

    assert len(compact) < len(raw)
    assert len(compact) <= commander.SYNTHESIS_PROMPT_CHAR_BUDGET


def test_commander_sends_bounded_prompt_and_keeps_full_analysis(
    workspace, monkeypatch
):
    _seed()

    captured = {}

    def fake_completion(**kwargs):
        captured["prompt"] = kwargs.get("prompt")
        return "Executive summary text."

    monkeypatch.setattr(commander, "get_completion", fake_completion)

    result = commander.run_commander_task(
        "t-large",
        "What are the strongest and weakest sales patterns across regions, "
        "products, and time, and what should management investigate first?",
    )

    prompt = captured["prompt"]
    assert len(prompt) <= commander.SYNTHESIS_PROMPT_CHAR_BUDGET

    # The prompt still carries the decision-relevant evidence and filenames.
    assert "train.csv" in prompt
    assert "metrics" in prompt
    assert "top_products" in prompt
    assert "strongest" in prompt.lower()
    assert "weakest" in prompt.lower()

    # The stored deterministic analysis is NOT truncated.
    metrics = result["metrics"]
    analysis = metrics["company_analysis"]
    assert len(analysis["breakdowns"]["products"]) >= 50
    assert len(metrics["dataset_evidence"]["evidence"]["train.csv"]["evidence"]["products"]) >= 50
    # The stored reasoning pack keeps its full sales_pattern lists.
    assert "products" in metrics["reasoning"]["sales_pattern"]

    # No raw cross-tab bloat is shipped into the prompt text.
    assert "product_region" not in prompt
    assert "product_channel" not in prompt
    assert "sellers" not in prompt