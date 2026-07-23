import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "continuous_agent" / "agent.py"
SPEC = importlib.util.spec_from_file_location("continuous_agent_module", MODULE_PATH)
AGENT = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(AGENT)


class ContinuousAgentTests(unittest.TestCase):
    def test_file_observation_is_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "proof.txt"
            target.write_text("ok", encoding="utf-8")
            result = AGENT.observe(
                {"id": "proof", "type": "file_exists", "path": str(target), "expected": True}
            )
            self.assertEqual(result.status, "healthy")
            self.assertTrue(result.fingerprint)

    def test_unknown_check_type_becomes_error_evidence(self):
        result = AGENT.observe({"id": "unknown", "type": "not-supported"})
        self.assertEqual(result.status, "error")
        self.assertIn("unsupported check type", result.summary)

    def test_alert_is_written_only_for_degraded_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "audit.jsonl"
            alerts = root / "alerts.jsonl"
            state = {"checks": {}}
            config = {
                "checks": [
                    {
                        "id": "missing",
                        "type": "file_exists",
                        "path": str(root / "missing.txt"),
                        "expected": True,
                    }
                ]
            }

            AGENT.run_cycle(config, state, audit, alerts)
            AGENT.run_cycle(config, state, audit, alerts)

            audit_records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
            alert_records = [json.loads(line) for line in alerts.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(audit_records), 2)
            self.assertEqual(len(alert_records), 1)
            self.assertFalse(alert_records[0]["automatic_remediation"])


if __name__ == "__main__":
    unittest.main()
