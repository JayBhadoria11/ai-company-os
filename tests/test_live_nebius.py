"""Opt-in live integration tests against the real Nebius Token Factory API.

These tests are skipped unless ``NEBIUS_LIVE_TESTS=1`` is set, so the default
test run never requires a real API key or network access. To run them::

    $env:NEBIUS_LIVE_TESTS=1; python -m pytest tests/test_live_nebius.py
"""

import os

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("NEBIUS_LIVE_TESTS") != "1",
    reason="Set NEBIUS_LIVE_TESTS=1 to run live Nebius integration tests.",
)


def test_live_nebius_returns_non_empty_completion():
    from app.llm.nebius_client import get_completion

    content = get_completion(
        "Reply with exactly one short sentence confirming the connection.",
        max_tokens=64,
    )

    assert isinstance(content, str)
    assert content.strip()
