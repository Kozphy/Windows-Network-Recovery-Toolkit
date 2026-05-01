"""Stripe billing integration helpers for checkout and webhook verification.

This module is called by `backend.main` payment endpoints. It wraps minimal
Stripe operations while leaving business-level subscription updates to API
handlers and DB helpers.

Key invariants:
    - Stripe client is configured from environment variables per call.
    - No local state is persisted in this module.
"""

import os
from typing import Any

import stripe


def init_stripe() -> None:
    """Initialize Stripe SDK API key from environment.

    Args:
        None.

    Returns:
        None.

    Raises:
        None. Empty key is permitted but downstream API calls will fail.
    """
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


def create_checkout_session(
    customer_email: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Create a Stripe subscription checkout session.

    Side effects:
        Performs outbound API call to Stripe.

    Idempotency:
        Not idempotent. Repeated calls create distinct checkout sessions.

    Args:
        customer_email: Email prefilled in Stripe checkout.
        price_id: Stripe price identifier for selected plan.
        success_url: Redirect URL after successful checkout.
        cancel_url: Redirect URL after checkout cancellation.
        metadata: Additional metadata persisted in Stripe session.

    Returns:
        dict[str, Any]: Stripe checkout session object as dictionary.

    Raises:
        stripe.error.StripeError: On Stripe API validation/network failures.
    """
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
    """Verify and decode a Stripe webhook event.

    Audit Notes:
        - What can go wrong: invalid signature or wrong webhook secret.
        - Detection: signature verification exception.
        - Recovery: confirm `STRIPE_WEBHOOK_SECRET` and endpoint config.

    Args:
        payload: Raw webhook request body bytes.
        sig_header: Stripe signature header value.

    Returns:
        dict[str, Any]: Verified Stripe event payload.

    Raises:
        stripe.error.SignatureVerificationError: On invalid signature.
        stripe.error.StripeError: On malformed payload or SDK errors.
    """
    init_stripe()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=secret)
    return dict(event)
