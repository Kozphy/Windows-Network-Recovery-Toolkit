import os
from typing import Any

import stripe


def init_stripe() -> None:
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


def create_checkout_session(
    customer_email: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    init_stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        customer_email=customer_email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    return dict(session)


def verify_webhook(payload: bytes, sig_header: str) -> dict[str, Any]:
    init_stripe()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=secret)
    return dict(event)
