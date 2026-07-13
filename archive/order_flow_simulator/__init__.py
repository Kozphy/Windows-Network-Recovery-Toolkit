"""Order-flow lifecycle simulator (event sourcing + audit + latency demo).

Not a trading system — demonstrates fintech-style reliability patterns for portfolios.
"""

from order_flow_simulator.simulator import OrderFlowSimulator, SimulationResult

__all__ = ["OrderFlowSimulator", "SimulationResult"]
