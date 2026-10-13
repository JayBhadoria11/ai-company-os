"""Regression tests for Nemotron finish_reason="length"/empty-content failures.

Two defects are locked in here:
1. nebius_client must NEVER return truncated output as a success. A
   finish_reason="length" response (even with non-empty content) must raise.
2. When Nemotron synthesis is unavailable (empty or truncated), the company
   investigation must return a clearly-labelled deterministic fallback built
   from verified evidence, and must not claim that synthesis succeeded.
"""

from types import SimpleNamespace

import pytest

import app.core.commander as commander
import app.core.company_workspace as company_workspace
import app.database.db as database
import app.llm.nebius_client as nebius_client


SALES_CSV = (
    b"Row ID,Order ID,Order Date,Region,Category,Sales\n"
    b"1,CA-1,01/05/2024,South,Furniture,100.0\n"
    b"2,CA-2,02/10/2024,North,Technology,200.0\n"
    b"3,CA-3,03/15/2024,South,Office Supplies,300.0\n"
    b"4,CA-4,04/20/2024,West,Furniture,400.0\n"
)

HR_CSV = (
    b"EmployeeNumber,Department,Attrition,OverTime,MonthlyIncome,YearsAtCompany,Gender,JobRole\n"
    b"1,Sales,Yes,Yes,5000,3,Female,Sales Executive\n"
    b"2,Sales,No,No,6000,5,Male,Sales Executive\n"
    b"3,HR,No,Yes,4000,2,Female,HR Specialist\n"
    b"4,Sales,No,No,7000,7,Male,Sales Executive\n"
)

QUERY = (
    "What are our total sales, number of orders, and average order value?"
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


def _seed():
    company_workspace.save_dataset_bytes("train.csv", SALES_CSV)
    company_workspace.save_dataset_bytes("HR_Analytics.csv", HR_CSV)


# ---------------------------------------------------------------------------
# nebius_client: finish_reason="length" / empty output must raise
# ---------------------------------------------------------------------------

def _fake_create(content, finish_reason):
    def create(**kwargs):
        choice = SimpleNamespace(
            message=SimpleNamespace(content=content),
            finish_reason=finish_reason,
        )
        return SimpleNamespace(choices=[choice])
    return create


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setattr(
        nebius_client,
        "validate_config",
        lambda: None,
    )
    created = {}

    def install(content, finish_reason):
        created["client"] = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=_fake_create(content, finish_reason)
                )
            )
        )
        monkeypatch.setattr(nebius_client, "OpenAI", lambda *a, **k: created["client"])
        return created

    return install


def test_length_truncated_content_raises(fake_llm):
    fake_llm(content="QUESTION 1\nANSWER\nSales total 1000.0", finish_reason="length")

    with pytest.raises(ValueError, match="finish_reason='length'"):
        nebius_client.get_completion(prompt="Query", max_tokens=4000)


def test_empty_content_raises(fake_llm):
    fake_llm(content="", finish_reason="length")

    with pytest.raises(ValueError, match="empty content"):
        nebius_client.get_completion(prompt="Query", max_tokens=4000)


def test_complete_content_returns(fake_llm):
    fake_llm(content="Sales total 1000.0", finish_reason="stop")

    assert nebius_client.get_completion(prompt="Query", max_tokens=4000) == (
        "Sales total 1000.0"
    )


# ---------------------------------------------------------------------------
# commander company investigation: graceful, clearly-labelled fallback
# ---------------------------------------------------------------------------

def test_synthesis_failure_uses_labelled_deterministic_fallback(
    workspace, monkeypatch
):
    _seed()

    def failing_completion(**kwargs):
        raise ValueError(
            "Nemotron stopped early (finish_reason='length') and returned "
            "incomplete output."
        )

    monkeypatch.setattr(commander, "get_completion", failing_completion)

    result = commander.run_commander_task("t-fallback", QUERY)

    assert result["status"] == "success"

    metrics = result["metrics"]
    synthesis = metrics["nvidia_synthesis"]

    assert synthesis["synthesis_fallback"] is True
    assert synthesis["synthesis_note"] is not None
    assert "unavailable" in synthesis["executive_summary"].lower()
    assert "not nemotron synthesis" in synthesis["executive_summary"].lower()
    assert synthesis["executive_summary"].strip()

    # The deterministic verified summary is preserved verbatim and labelled.
    assert synthesis["verified_summary"] == synthesis["executive_summary"].split(
        "\n\n", 1
    )[-1].strip()

    # Verified evidence remains the source of truth.
    assert synthesis["key_insights"]
    assert isinstance(synthesis["risks"], list)
    assert isinstance(synthesis["recommended_actions"], list)

    # The finding carries the same labelled fallback, never a silent empty.
    finding_text = result["findings"][0]["finding"]
    assert finding_text == synthesis["executive_summary"]


def test_synthesis_success_is_not_marked_fallback(workspace, monkeypatch):
    _seed()

    monkeypatch.setattr(
        commander,
        "get_completion",
        lambda **kwargs: "ANSWER\nSales total 1000.0.",
    )

    result = commander.run_commander_task("t-ok", QUERY)

    synthesis = result["metrics"]["nvidia_synthesis"]

    assert synthesis["synthesis_fallback"] is False
    assert synthesis["synthesis_note"] is None
    assert synthesis["executive_summary"] == "ANSWER\nSales total 1000.0."