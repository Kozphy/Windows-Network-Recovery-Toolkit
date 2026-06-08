"""Step 2 — process classifier tests (fixture-portable)."""

from __future__ import annotations

from pathlib import Path

from src.classification.models import ProcessClassificationInput, ProcessClassificationKind
from src.classification.process_classifier import classify_process
from src.proxy_guard.incident_pipeline import analyze_fixture
from src.replay.fixture_loader import load_fixture

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "proxy_incidents"


def test_cursor_launches_node_writes_proxyserver() -> None:
    fx = load_fixture(FIXTURES / "cursor_known_proxy.json")
    bundle = analyze_fixture(fx)
    assert bundle["classification"]["classification"] == ProcessClassificationKind.KNOWN_CURSOR_PROXY.value
    assert bundle["classification"]["confidence"] <= 0.85


def test_vscode_extension_node() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Program Files\nodejs\node.exe",
        command_line="node extension-host",
        parent_image_path=r"C:\Program Files\Microsoft VS Code\Code.exe",
        parent_command_line="Code.exe --extensionDevelopmentPath",
        has_registry_writer_proof=True,
        proxy_server_after="127.0.0.1:8080",
        registry_target="ProxyServer",
        registry_value_name="proxyserver",
    )
    cls = classify_process(inp)
    assert cls.classification == ProcessClassificationKind.KNOWN_VSCODE_EXTENSION


def test_npm_dev_server_localhost() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Program Files\nodejs\node.exe",
        command_line="npm run dev",
        has_registry_writer_proof=True,
        proxy_server_after="127.0.0.1:3000",
        registry_target="ProxyServer",
        registry_value_name="proxyserver",
    )
    cls = classify_process(inp)
    assert cls.classification == ProcessClassificationKind.KNOWN_DEV_PROXY


def test_powershell_encodedcommand_temp() -> None:
    fx = load_fixture(FIXTURES / "suspicious_powershell_temp_proxy.json")
    bundle = analyze_fixture(fx)
    assert bundle["classification"]["classification"] == ProcessClassificationKind.SUSPICIOUS_PROXY.value


def test_external_proxy_mitm() -> None:
    fx = load_fixture(FIXTURES / "external_proxy_mitm_risk.json")
    bundle = analyze_fixture(fx)
    assert bundle["classification"]["classification"] == ProcessClassificationKind.POSSIBLE_MITM_RISK.value


def test_nvidia_python_no_registry_proof() -> None:
    inp = ProcessClassificationInput(
        image_path=r"C:\Python311\python.exe",
        command_line="python -m nvidia_smi_helper",
        has_listener_only=True,
        causation_level="CORRELATION_ONLY",
        proxy_server_after="127.0.0.1:64394",
    )
    cls = classify_process(inp)
    assert cls.classification in (ProcessClassificationKind.CORRELATION_ONLY, ProcessClassificationKind.UNKNOWN)
    assert cls.confidence <= 0.45


def test_listener_only_no_registry_writer() -> None:
    fx = load_fixture(FIXTURES / "correlation_only_listener.json")
    bundle = analyze_fixture(fx)
    assert bundle["classification"]["classification"] == ProcessClassificationKind.CORRELATION_ONLY.value
    assert "registry writer proof unavailable" in bundle["policy"]["explanation"][0].lower() or bundle["policy"]["decision"] == "CORRELATION_ONLY_ALERT"


def test_unknown_node_powershell_localhost() -> None:
    fx = load_fixture(FIXTURES / "unknown_node_powershell_proxy.json")
    bundle = analyze_fixture(fx)
    assert bundle["causation"]["causation_level"] == "FINAL_CAUSATION"
    assert bundle["classification"]["classification"] in (
        ProcessClassificationKind.UNKNOWN_LOCAL_PROXY.value,
        ProcessClassificationKind.REGISTRY_WRITER_CONFIRMED.value,
    )
