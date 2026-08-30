from src.platform_core.control_testing.catalog import ENDPOINT_CONTROL_CATALOG, get_control


def test_catalog_has_stable_unique_ids():
    ids = [control.control_id for control in ENDPOINT_CONTROL_CATALOG]
    assert ids == ["CTRL-001", "CTRL-002", "CTRL-003"]
    assert len(ids) == len(set(ids))


def test_catalog_controls_are_versioned_and_limited():
    for control in ENDPOINT_CONTROL_CATALOG:
        assert control.version
        assert control.requirements
        assert any("does not authorize remediation" in item for item in control.limitations)


def test_get_control_is_case_insensitive():
    assert get_control("ctrl-002") is not None
    assert get_control("missing") is None
