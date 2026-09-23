"""Shared test data types."""

import sqlite3
from typing import TypedDict, override

from newtrackon.persistence import HistoryData


class TrackerDataDict(TypedDict):
    host: str
    url: str
    ips: list[str] | None
    latency: int | None
    last_checked: int
    interval: int
    status: int
    uptime: float
    countries: list[str] | None
    country_codes: list[str] | None
    networks: list[str] | None
    added: int
    historic: list[int]
    last_downtime: int
    last_uptime: int


class ReusableConnection(sqlite3.Connection):
    """Keep a fixture's database open across application calls."""

    @override
    def close(self) -> None:
        pass


def make_history(timestamp: int) -> HistoryData:
    return {"url": "udp://tracker.example.com:6969/announce", "time": timestamp, "status": 1, "ip": "1.2.3.4", "info": []}
