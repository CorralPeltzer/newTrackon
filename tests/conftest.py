"""Shared pytest fixtures for newTrackon test suite."""

import json
import sqlite3
from collections import deque
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def clean_global_state():
    """Automatically clean global state before and after each test."""
    import newTrackon.persistence as persistence
    import newTrackon.trackon as trackon

    # Clear before test
    persistence.submitted_trackers.clear()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()
    trackon.processing_trackers = False

    yield

    # Clear after test
    persistence.submitted_trackers.clear()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()
    trackon.processing_trackers = False


@pytest.fixture
def in_memory_db():
    """Provide an in-memory SQLite database with schema."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
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
            added TEXT,
            historic TEXT,
            last_downtime INTEGER,
            last_uptime INTEGER
        )
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_db_connection(in_memory_db, monkeypatch):
    """Patch sqlite3.connect to use in-memory database."""
    original_connect = sqlite3.connect

    def patched_connect(database, *args, **kwargs):
        if database == "data/trackon.db":
            return in_memory_db
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr("sqlite3.connect", patched_connect)
    return in_memory_db


@pytest.fixture
def sample_tracker_data():
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
        "added": "01-01-2024",
        "historic": [1] * 100,
        "last_downtime": 1699990000,
        "last_uptime": 1700000000,
    }


@pytest.fixture
def sample_tracker(sample_tracker_data):
    """Create a sample Tracker instance for testing."""
    from newTrackon.tracker import Tracker

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
def insert_sample_tracker(mock_db_connection, sample_tracker_data):
    """Insert sample tracker into the test database."""
    mock_db_connection.execute(
        "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
        ),
    )
    mock_db_connection.commit()
    return sample_tracker_data


@pytest.fixture
def mock_network():
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
def reset_globals():
    """Reset global state between tests."""
    import newTrackon.persistence as persistence
    import newTrackon.scraper as scraper
    import newTrackon.trackon as trackon

    # Save original scalar values
    old_ipv4 = scraper.my_ipv4
    old_ipv6 = scraper.my_ipv6
    old_processing = trackon.processing_trackers

    # Clear deques at the start to ensure clean state
    persistence.submitted_trackers.clear()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()
    trackon.processing_trackers = False

    yield

    # Restore original scalar values
    scraper.my_ipv4 = old_ipv4
    scraper.my_ipv6 = old_ipv6
    trackon.processing_trackers = old_processing

    # Clear deques after test (don't restore old contents - start fresh for next test)
    persistence.submitted_trackers.clear()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()


@pytest.fixture
def empty_deques(reset_globals):
    """Provide empty deques for testing."""
    import newTrackon.persistence as persistence

    persistence.submitted_trackers.clear()
    persistence.raw_data.clear()
    persistence.submitted_data.clear()
    yield persistence


@pytest.fixture
def flask_client(mock_db_connection):
    """Create Flask test client with mocked database."""
    from newTrackon.views import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_tracker_response():
    """Return a mock successful tracker response."""
    return {
        "interval": 1800,
        "complete": 100,
        "incomplete": 50,
        "peers": [{"IP": "1.2.3.4", "port": 6881}],
    }


@pytest.fixture
def mock_udp_response():
    """Return mock UDP tracker response data."""
    return {
        "interval": 1800,
        "leechers": 50,
        "seeds": 100,
        "peers": [{"IP": "1.2.3.4", "port": 6881}],
    }


@pytest.fixture
def bencoded_tracker_response():
    """Return a valid bencoded tracker response."""
    # d8:completei100e10:incompletei50e8:intervali1800e5:peers6:...e
    return b"d8:completei100e10:incompletei50e8:intervali1800e5:peers6:\x01\x02\x03\x04\x1a\xe1e"


@pytest.fixture
def mock_ip_resolution():
    """Mock socket.getaddrinfo for IP resolution."""
    with patch("socket.getaddrinfo") as mock:
        mock.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 6969)),
        ]
        yield mock
