import uuid

import pytest

import app.database.db as database
from app.core.approval import (
    initialize_approvals,
    create_approval_request,
    get_approval,
    update_approval,
    list_pending_approvals,
)


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Isolate every approval test to a temporary DB.

    Keeps the real persisted approval history untouched and prevents records
    from one test run leaking into the next.
    """
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "approvals.db")


def unique_task_id():
    return f"approval-test-{uuid.uuid4()}"


def test_initialize_approvals():
    initialize_approvals()


def test_create_pending_approval():
    task_id = unique_task_id()

    request_id = create_approval_request(
        task_id,
        "Review recommended business actions.",
    )

    assert isinstance(request_id, int)

    approval = get_approval(task_id)

    assert approval["task_id"] == task_id
    assert approval["status"] == "pending"
    assert approval["summary"] == (
        "Review recommended business actions."
    )


def test_approve_request():
    task_id = unique_task_id()

    create_approval_request(
        task_id,
        "Approve recommended actions.",
    )

    approval = update_approval(
        task_id,
        "approved",
    )

    assert approval["status"] == "approved"


def test_reject_request():
    task_id = unique_task_id()

    create_approval_request(
        task_id,
        "Reject recommended actions.",
    )

    approval = update_approval(
        task_id,
        "rejected",
    )

    assert approval["status"] == "rejected"


def test_invalid_status():
    task_id = unique_task_id()

    create_approval_request(
        task_id,
        "Test approval.",
    )

    with pytest.raises(ValueError, match="approved.*rejected"):
        update_approval(
            task_id,
            "invalid",
        )


def test_cannot_update_completed_request():
    task_id = unique_task_id()

    create_approval_request(
        task_id,
        "Test completed approval.",
    )

    update_approval(
        task_id,
        "approved",
    )

    with pytest.raises(
        ValueError,
        match="does not exist or is no longer pending",
    ):
        update_approval(
            task_id,
            "rejected",
        )


def test_list_pending_approvals_newest_first():
    create_approval_request(
        "pending-a",
        "First pending.",
    )
    create_approval_request(
        "pending-b",
        "Second pending.",
    )

    pending = list_pending_approvals()
    task_ids = [item["task_id"] for item in pending]

    # The two just-created requests are the newest (top of the pending list).
    assert task_ids[0] == "pending-b"
    assert task_ids[1] == "pending-a"
    assert all(item["status"] == "pending" for item in pending)


def test_approve_removes_from_pending_list():
    task_id = unique_task_id()
    create_approval_request(task_id, "Will be approved.")

    assert any(item["task_id"] == task_id for item in list_pending_approvals())

    update_approval(task_id, "approved")

    assert not any(item["task_id"] == task_id for item in list_pending_approvals())


def test_create_approval_request_upserts_does_not_duplicate():
    task_id = unique_task_id()

    first_id = create_approval_request(task_id, "Initial summary.")
    second_id = create_approval_request(task_id, "Updated summary.")

    # Upsert: the same logical row is reused, never duplicated.
    assert first_id == second_id

    matching = [
        item for item in list_pending_approvals() if item["task_id"] == task_id
    ]
    assert len(matching) == 1
    assert matching[0]["summary"] == "Updated summary."


def test_approval_gate_does_not_auto_execute():
    from app.core.action_engine import (
        request_action,
        execute_action,
        get_task_actions,
    )

    task_id = "gate-no-auto"
    create_approval_request(task_id, "Approve the recommended action.")

    request_action(task_id, "Act on the recommendation.")

    # A pending approval blocks execution.
    with pytest.raises(ValueError, match="pending"):
        execute_action(task_id, "Act on the recommendation.")

    # Approving records the decision but does NOT auto-execute anything.
    update_approval(task_id, "approved")
    actions = get_task_actions(task_id)
    assert actions and actions[0]["status"] == "pending_approval"

    # Only an explicit execution call (which requires an approved approval)
    # transitions the action.
    result = execute_action(task_id, "Act on the recommendation.")
    assert result["status"] == "executed"