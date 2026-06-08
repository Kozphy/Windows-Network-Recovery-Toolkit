from __future__ import annotations


def test_linked_failure_block_payload_importable() -> None:
    from platform_core.fleet import linked_failure_block_payload

    assert linked_failure_block_payload("") == {
        "found": False,
        "failure_block_id": "",
        "detail": "no_failure_block_id",
    }
