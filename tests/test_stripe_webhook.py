"""Stripe webhook subscription sync validation."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.main import process_stripe_subscription_event


def test_subscription_event_missing_org_id_raises() -> None:
    with pytest.raises(ValueError, match="missing metadata.org_id"):
        process_stripe_subscription_event(
            "customer.subscription.updated",
            {"id": "sub_123", "status": "active", "metadata": {}},
        )


@patch("backend.main.update_subscription")
def test_subscription_event_with_org_id_processed(mock_update) -> None:
    result = process_stripe_subscription_event(
        "customer.subscription.updated",
        {
            "id": "sub_123",
            "status": "active",
            "customer": "cus_123",
            "metadata": {"org_id": "org_test"},
            "items": {"data": [{"price": {"id": "price_pro_monthly"}}]},
        },
    )
    assert result is not None
    assert result["processed"] is True
    assert result["org_id"] == "org_test"
    assert result["plan"] == "pro"
    mock_update.assert_called_once()


def test_non_subscription_event_returns_none() -> None:
    assert process_stripe_subscription_event("invoice.paid", {"metadata": {}}) is None
