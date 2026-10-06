import uuid

import pytest

from app.core.action_engine import (
    initialize_actions,
    request_action,
    execute_action,
    get_task_actions,
)
from app.core.approval import create_approval_request, update_approval


def unique_task_id():
    return f"action-test-{uuid.uuid4()}"


def test_initialize_actions():
    initialize_actions()


def test_request_action():
    task_id = unique_task_id()

    action_id = request_action(
        task_id,
        "Review expense allocation.",
    )

    assert isinstance(action_id, int)

    actions = get_task_actions(task_id)

    assert len(actions) == 1
    assert actions[0]["task_id"] == task_id
    assert actions[0]["action"] == "Review expense allocation."
    assert actions[0]["status"] == "pending_approval"


def test_action_blocked_while_pending():
    task_id = unique_task_id()

    create_approval_request(
        task_id,
        "Approve expense review.",
    )

    with pytest.raises(
        ValueError,
        match="approval is still pending",
    ):
        execute_action(
            task_id,
            "Review expense allocation.",
        )


def test_action_blocked_when_rejected():
    task_id = unique_task_id()

    create_approval_request(
        task_id,
        "Approve expense review.",
    )

    update_approval(
        task_id,
        "rejected",
    )

    with pytest.raises(
        ValueError,
        match="request was rejected",
    ):
        execute_action(
            task_id,
            "Review expense allocation.",
        )


def test_action_executes_after_approval():
    task_id = unique_task_id()

    create_approval_request(
        task_id,
        "Approve expense review.",
    )

    update_approval(
        task_id,
        "approved",
    )

    result = execute_action(
        task_id,
        "Review expense allocation.",
    )

    assert result["task_id"] == task_id
    assert result["action"] == "Review expense allocation."
    assert result["status"] == "executed"
    assert "SIMULATED EXECUTION" in result["result"]


def test_action_requires_approval_request():
    task_id = unique_task_id()

    with pytest.raises(
        ValueError,
        match="No approval request",
    ):
        execute_action(
            task_id,
            "Review expense allocation.",
        )