"""Deterministic diagnosis engine bridging collector snapshots → ranked hypotheses.

Consumers call `network_agent.engine.decision_engine.diagnose`; supporting modules provide
confidence composition (`confidence.py`) and rule constants (`rules.py`).
"""
