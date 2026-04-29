from dataclasses import dataclass


@dataclass
class DiagnoseInput:
    ping: bool
    dns: bool
    https: bool
    proxy: bool
    time_wait: int
    established: int


def detect_anomaly(
    current_time_wait: int,
    current_established: int,
    recent_metrics: list[dict],
) -> dict:
    if not recent_metrics:
        return {
            "anomaly": False,
            "reason": "Not enough history yet.",
            "signals": {
                "rapid_growth": False,
                "continuous_growth": False,
                "sudden_spike": False,
            },
        }

    prev = recent_metrics[0]
    prev_tw = int(prev["time_wait"])
    prev_est = int(prev["established"])

    rapid_growth = (
        (prev_tw > 0 and current_time_wait > prev_tw * 2)
        or (prev_est > 0 and current_established > prev_est * 2)
    )
    sudden_spike = (
        (current_time_wait - prev_tw) > 1000
        or (current_established - prev_est) > 1000
    )

    # recent_metrics comes newest-first from DB.
    tw_series = [m["time_wait"] for m in recent_metrics[:4]][::-1] + [current_time_wait]
    est_series = [m["established"] for m in recent_metrics[:4]][::-1] + [current_established]
    continuous_growth = False
    if len(tw_series) >= 5:
        tw_increasing = all(tw_series[i] > tw_series[i - 1] for i in range(1, len(tw_series)))
        est_increasing = all(est_series[i] > est_series[i - 1] for i in range(1, len(est_series)))
        continuous_growth = tw_increasing or est_increasing

    anomaly = rapid_growth or sudden_spike or continuous_growth
    if anomaly:
        reason = "Rapid or continuous connection growth detected."
    else:
        reason = "No abnormal trend detected in recent metrics."

    return {
        "anomaly": anomaly,
        "reason": reason,
        "signals": {
            "rapid_growth": rapid_growth,
            "continuous_growth": continuous_growth,
            "sudden_spike": sudden_spike,
        },
    }


def classify_root_cause(data: DiagnoseInput, anomaly: dict) -> dict:
    if not data.ping:
        return {
            "root_cause": "Network unreachable",
            "confidence": "high",
            "recommendation": "Check adapter/router/ISP path before running repair scripts.",
            "risk": "LOW",
        }

    if data.ping and not data.dns:
        return {
            "root_cause": "DNS issue",
            "confidence": "high",
            "recommendation": "Run reset_dns.bat and retest nslookup/curl/browser.",
            "risk": "LOW",
        }

    if data.proxy:
        return {
            "root_cause": "Proxy misconfiguration",
            "confidence": "high",
            "recommendation": "Run reset_proxy.bat and reopen browser.",
            "risk": "LOW",
        }

    if data.ping and data.dns and not data.https:
        return {
            "root_cause": "HTTPS/TLS/firewall path issue",
            "confidence": "medium-high",
            "recommendation": "Check VPN/antivirus/firewall filters. If unclear, run one_click_fix.bat then restart.",
            "risk": "MEDIUM",
        }

    if data.time_wait > 5000 or anomaly["anomaly"]:
        return {
            "root_cause": "Connection exhaustion / leak trend",
            "confidence": "medium-high",
            "recommendation": "Restart network-heavy applications and review connection reuse in code (Session/pooling).",
            "risk": "LOW",
        }

    if data.ping and data.dns and data.https and not data.proxy:
        return {
            "root_cause": "Possible router/NAT/session intermittency",
            "confidence": "medium",
            "recommendation": "Monitor trends, try another network, and compare behavior over time.",
            "risk": "LOW",
        }

    return {
        "root_cause": "Mixed network state",
        "confidence": "medium",
        "recommendation": "Run one_click_fix.bat and restart, then collect new diagnostics.",
        "risk": "HIGH",
    }
