import uuid

import pytest

from app.core.approval import (
    initialize_approvals,
    create_approval_request,
    get_approval,
    update_approval,
)


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