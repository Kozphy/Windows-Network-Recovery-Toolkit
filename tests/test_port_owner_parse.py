from __future__ import annotations

from pathlib import Path

from src.attribution.port_owner import netstat_listen_rows, owners_for_port


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "netstat_sample_listen.txt"


def test_netstat_listen_rows_fixture() -> None:
    txt = FIXTURE.read_text(encoding="utf-8")
    rows = netstat_listen_rows(txt)
    ports = {(h, p, pid) for (h, p, pid) in rows}
    assert ("127.0.0.1", 58815, 24040) in ports
    pids58815 = owners_for_port(rows, 58815)
    assert pids58815 == [24040]
