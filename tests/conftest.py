"""Shared pytest fixtures for newTrackon test suite."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from collections.abc import Generator
from queue import Empty
from sqlite3 import Connection
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient

from newtrackon.bdecode import BDecodeResponse
from newtrackon.scraper import UDPAnnounceResponse
from tests.helpers import ReusableConnection, TrackerDataDict

if TYPE_CHECKING:
    from newtrackon.tracker import Tracker


def drain_submitted_queue() -> None:
    from newtrackon import ingest

    while True:
        try:
            _ = ingest.submitted_queue.get_nowait()
            ingest.submitted_queue.task_done()
        except Empty:
            break


@pytest.fixture(autouse=True)
def clean_global_state() -> Generator[None]:
    """Automatically clean global state before and after each test."""
    from newtrackon import persistence

    # Clear before test
    drain_submitted_queue()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()

    yield

    # Clear after test
    drain_submitted_queue()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()


@pytest.fixture
def in_memory_db() -> Generator[Connection]:
    """Provide an in-memory SQLite database with schema."""
    conn = sqlite3.connect(":memory:", factory=ReusableConnection)
    _ = conn.execute("""
        CREATE TABLE status (
            host TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            ip TEXT,
            latency INTEGER,
            last_checked INTEGER,
            interval INTEGER,
            status INTEGER,
            uptime INTEGER,
            country TEXT,
            country_code TEXT,
            network TEXT,
            added INTEGER,
            historic TEXT,
            last_downtime INTEGER,
            last_uptime INTEGER,
            recent_ip TEXT
        )
    """)
    conn.commit()
    yield conn
    sqlite3.Connection.close(conn)


@pytest.fixture
def mock_db_connection(in_memory_db: Connection, monkeypatch: pytest.MonkeyPatch) -> Connection:
    """Patch sqlite3.connect to use in-memory database."""
    original_connect = sqlite3.connect

    def patched_connect(database: str) -> Connection:
        if database == "data/trackon.db":
            return in_memory_db
        return original_connect(database)

    monkeypatch.setattr("sqlite3.connect", patched_connect)
    return in_memory_db


@pytest.fixture
def sample_tracker_data() -> TrackerDataDict:
    """Return sample tracker data as a dictionary."""
    return {
        "host": "tracker.example.com",
        "url": "udp://tracker.example.com:6969/announce",
        "ips": ["93.184.216.34"],
        "latency": 50,
        "last_checked": 1700000000,
        "interval": 1800,
        "status": 1,
        "uptime": 95,
        "countries": ["United States"],
        "country_codes": ["us"],
        "networks": ["Example ISP"],
        "added": 1704067200,
        "historic": [1] * 100,
        "last_downtime": 1699990000,
        "last_uptime": 1700000000,
    }


@pytest.fixture
def sample_tracker(sample_tracker_data: TrackerDataDict) -> Tracker:
    """Create a sample Tracker instance for testing."""
    from newtrackon.tracker import Tracker

    tracker = Tracker(
        host=sample_tracker_data["host"],
        url=sample_tracker_data["url"],
        ips=sample_tracker_data["ips"],
        latency=sample_tracker_data["latency"],
        last_checked=sample_tracker_data["last_checked"],
        interval=sample_tracker_data["interval"],
        status=sample_tracker_data["status"],
        uptime=sample_tracker_data["uptime"],
        countries=sample_tracker_data["countries"],
        country_codes=sample_tracker_data["country_codes"],
        networks=sample_tracker_data["networks"],
        historic=deque(sample_tracker_data["historic"], maxlen=1000),
        added=sample_tracker_data["added"],
        last_downtime=sample_tracker_data["last_downtime"],
        last_uptime=sample_tracker_data["last_uptime"],
    )
    return tracker


@pytest.fixture
def insert_sample_tracker(mock_db_connection: Connection, sample_tracker_data: TrackerDataDict) -> TrackerDataDict:
    """Insert sample tracker into the test database."""
    _ = mock_db_connection.execute(
        "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            sample_tracker_data["host"],
            sample_tracker_data["url"],
            json.dumps(sample_tracker_data["ips"]),
            sample_tracker_data["latency"],
            sample_tracker_data["last_checked"],
            sample_tracker_data["interval"],
            sample_tracker_data["status"],
            sample_tracker_data["uptime"],
            json.dumps(sample_tracker_data["countries"]),
            json.dumps(sample_tracker_data["country_codes"]),
            json.dumps(sample_tracker_data["networks"]),
            sample_tracker_data["added"],
            json.dumps(sample_tracker_data["historic"]),
            sample_tracker_data["last_downtime"],
            sample_tracker_data["last_uptime"],
            json.dumps({}),
        ),
    )
    mock_db_connection.commit()
    return sample_tracker_data


@pytest.fixture
def mock_network() -> Generator[dict[str, MagicMock]]:
    """Disable all network calls by default."""
    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
        patch("socket.socket") as mock_socket,
        patch("socket.getaddrinfo") as mock_getaddrinfo,
        patch("dns.resolver.resolve") as mock_dns,
    ):
        yield {
            "get": mock_get,
            "post": mock_post,
            "socket": mock_socket,
            "getaddrinfo": mock_getaddrinfo,
            "dns": mock_dns,
        }


@pytest.fixture
def reset_globals() -> Generator[None]:
    """Reset global state between tests."""
    from newtrackon import persistence, scraper

    # Save original scalar values
    old_ipv4 = scraper.my_ipv4
    old_ipv6 = scraper.my_ipv6

    # Clear buffers at the start to ensure clean state
    drain_submitted_queue()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()

    yield

    # Restore original scalar values
    scraper.my_ipv4 = old_ipv4
    scraper.my_ipv6 = old_ipv6

    # Clear buffers after test (don't restore old contents - start fresh for next test)
    drain_submitted_queue()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()


@pytest.fixture
def empty_queues(reset_globals: None) -> Generator[None]:
    """Provide empty buffers for testing."""
    _ = reset_globals
    from newtrackon import persistence

    drain_submitted_queue()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()
    yield


@pytest.fixture
def flask_client(mock_db_connection: Connection) -> Generator[FlaskClient]:
    """Create Flask test client with mocked database."""
    _ = mock_db_connection
    from newtrackon.views import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_tracker_response() -> BDecodeResponse:
    """Return a mock successful tracker response."""
    return {
        "interval": 1800,
        "complete": 100,
        "incomplete": 50,
        "peers": [{"IP": "1.2.3.4", "port": 6881}],
    }


@pytest.fixture
def mock_udp_response() -> UDPAnnounceResponse:
    """Return mock UDP tracker response data."""
    return {
        "interval": 1800,
        "leechers": 50,
        "seeds": 100,
        "peers": [{"IP": "1.2.3.4", "port": 6881}],
    }


@pytest.fixture
def bencoded_tracker_response() -> bytes:
    """Return a valid bencoded tracker response."""
    # d8:completei100e10:incompletei50e8:intervali1800e5:peers6:...e
    return b"d8:completei100e10:incompletei50e8:intervali1800e5:peers6:\x01\x02\x03\x04\x1a\xe1e"


@pytest.fixture
def mock_ip_resolution() -> Generator[MagicMock]:
    """Mock socket.getaddrinfo for IP resolution."""
    with patch("socket.getaddrinfo") as mock:
        mock.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 6969)),
        ]
        yield mock
