"""Unit tests for the database module."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from newTrackon import db
from newTrackon.tracker import Tracker


class ConnectionWrapper:
    """Wrapper that prevents closing the underlying connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def cursor(self) -> sqlite3.Cursor:
        return self._conn.cursor()

    def commit(self) -> None:
        self._conn.commit()

    def execute(self, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
        return self._conn.execute(*args, **kwargs)

    def close(self) -> None:
        # Don't actually close - we need to reuse the connection
        pass

    @property
    def row_factory(self) -> Any:
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self._conn.row_factory = value


@pytest.fixture
def test_db() -> Generator[sqlite3.Connection]:
    """Create an in-memory database with schema for testing."""
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
            added INTEGER,
            historic TEXT,
            last_downtime INTEGER,
            last_uptime INTEGER
        )
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def patched_db(test_db: sqlite3.Connection, monkeypatch: MonkeyPatch) -> sqlite3.Connection:
    """Patch sqlite3.connect to use the test database with wrapper."""
    original_connect = sqlite3.connect

    def patched_connect(database: str, *args: Any, **kwargs: Any) -> sqlite3.Connection | ConnectionWrapper:
        if database == "data/trackon.db":
            return ConnectionWrapper(test_db)
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr("sqlite3.connect", patched_connect)
    return test_db


@pytest.fixture
def sample_tracker_dict() -> dict[str, Any]:
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
def sample_tracker_obj(sample_tracker_dict: dict[str, Any]) -> Tracker:
    """Create a sample Tracker instance for testing."""
    return Tracker(
        host=sample_tracker_dict["host"],
        url=sample_tracker_dict["url"],
        ips=sample_tracker_dict["ips"],
        latency=sample_tracker_dict["latency"],
        last_checked=sample_tracker_dict["last_checked"],
        interval=sample_tracker_dict["interval"],
        status=sample_tracker_dict["status"],
        uptime=sample_tracker_dict["uptime"],
        countries=sample_tracker_dict["countries"],
        country_codes=sample_tracker_dict["country_codes"],
        networks=sample_tracker_dict["networks"],
        historic=deque(sample_tracker_dict["historic"], maxlen=1000),
        added=sample_tracker_dict["added"],
        last_downtime=sample_tracker_dict["last_downtime"],
        last_uptime=sample_tracker_dict["last_uptime"],
    )


@pytest.fixture
def inserted_sample_tracker(patched_db: sqlite3.Connection, sample_tracker_dict: dict[str, Any]) -> dict[str, Any]:
    """Insert sample tracker into the test database."""
    patched_db.execute(
        "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            sample_tracker_dict["host"],
            sample_tracker_dict["url"],
            json.dumps(sample_tracker_dict["ips"]),
            sample_tracker_dict["latency"],
            sample_tracker_dict["last_checked"],
            sample_tracker_dict["interval"],
            sample_tracker_dict["status"],
            sample_tracker_dict["uptime"],
            json.dumps(sample_tracker_dict["countries"]),
            json.dumps(sample_tracker_dict["country_codes"]),
            json.dumps(sample_tracker_dict["networks"]),
            sample_tracker_dict["added"],
            json.dumps(sample_tracker_dict["historic"]),
            sample_tracker_dict["last_downtime"],
            sample_tracker_dict["last_uptime"],
        ),
    )
    patched_db.commit()
    return sample_tracker_dict


class TestInsertNewTracker:
    """Tests for insert_new_tracker function."""

    def test_insert_new_tracker_stores_data_correctly(self, patched_db: sqlite3.Connection, sample_tracker_obj: Tracker) -> None:
        """Verify that insert_new_tracker stores all tracker data correctly."""
        db.insert_new_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT * FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == sample_tracker_obj.host
        assert row[1] == sample_tracker_obj.url
        assert row[3] == sample_tracker_obj.latency
        assert row[4] == sample_tracker_obj.last_checked
        assert row[5] == sample_tracker_obj.interval
        assert row[6] == sample_tracker_obj.status
        assert row[7] == sample_tracker_obj.uptime
        assert row[11] == sample_tracker_obj.added
        assert row[13] == sample_tracker_obj.last_downtime
        assert row[14] == sample_tracker_obj.last_uptime

    def test_insert_new_tracker_json_serializes_ips(self, patched_db: sqlite3.Connection, sample_tracker_obj: Tracker) -> None:
        """Verify that IPs are JSON serialized when inserted."""
        db.insert_new_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT ip FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_ips = json.loads(row[0])
        assert stored_ips == sample_tracker_obj.ips

    def test_insert_new_tracker_json_serializes_countries(
        self, patched_db: sqlite3.Connection, sample_tracker_obj: Tracker
    ) -> None:
        """Verify that countries are JSON serialized when inserted."""
        db.insert_new_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT country FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_countries = json.loads(row[0])
        assert stored_countries == sample_tracker_obj.countries

    def test_insert_new_tracker_json_serializes_country_codes(
        self, patched_db: sqlite3.Connection, sample_tracker_obj: Tracker
    ) -> None:
        """Verify that country codes are JSON serialized when inserted."""
        db.insert_new_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT country_code FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_country_codes = json.loads(row[0])
        assert stored_country_codes == sample_tracker_obj.country_codes

    def test_insert_new_tracker_json_serializes_networks(
        self, patched_db: sqlite3.Connection, sample_tracker_obj: Tracker
    ) -> None:
        """Verify that networks are JSON serialized when inserted."""
        db.insert_new_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT network FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_networks = json.loads(row[0])
        assert stored_networks == sample_tracker_obj.networks

    def test_insert_new_tracker_json_serializes_historic(
        self, patched_db: sqlite3.Connection, sample_tracker_obj: Tracker
    ) -> None:
        """Verify that historic deque is JSON serialized when inserted."""
        db.insert_new_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT historic FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_historic = json.loads(row[0])
        assert stored_historic == list(sample_tracker_obj.historic)

    def test_insert_new_tracker_with_multiple_ips(self, patched_db: sqlite3.Connection) -> None:
        """Verify that multiple IPs are stored correctly."""
        tracker = Tracker(
            host="multi.example.com",
            url="udp://multi.example.com:6969/announce",
            ips=["2001:db8::1", "93.184.216.34", "10.0.0.1"],
            latency=100,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=99,
            countries=["Germany", "United States", "Canada"],
            country_codes=["de", "us", "ca"],
            networks=["ISP1", "ISP2", "ISP3"],
            historic=deque([1, 1, 1, 0, 1], maxlen=1000),
            added=1705276800,
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        db.insert_new_tracker(tracker)

        cursor = patched_db.cursor()
        cursor.execute("SELECT ip FROM status WHERE host = ?", (tracker.host,))
        row = cursor.fetchone()

        stored_ips = json.loads(row[0])
        assert stored_ips == ["2001:db8::1", "93.184.216.34", "10.0.0.1"]


class TestGetAllData:
    """Tests for get_all_data function."""

    def test_get_all_data_returns_tracker_objects(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any]
    ) -> None:
        """Verify that get_all_data returns a list of Tracker objects."""
        trackers = db.get_all_data()

        assert len(trackers) == 1
        assert isinstance(trackers[0], Tracker)

    def test_get_all_data_returns_correct_host(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that returned Tracker has correct host."""
        trackers = db.get_all_data()

        assert trackers[0].host == sample_tracker_dict["host"]

    def test_get_all_data_returns_correct_url(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that returned Tracker has correct URL."""
        trackers = db.get_all_data()

        assert trackers[0].url == sample_tracker_dict["url"]

    def test_get_all_data_deserializes_ips(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that IPs are deserialized from JSON."""
        trackers = db.get_all_data()

        assert trackers[0].ips == sample_tracker_dict["ips"]

    def test_get_all_data_deserializes_countries(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that countries are deserialized from JSON."""
        trackers = db.get_all_data()

        assert trackers[0].countries == sample_tracker_dict["countries"]

    def test_get_all_data_deserializes_country_codes(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that country codes are deserialized from JSON."""
        trackers = db.get_all_data()

        assert trackers[0].country_codes == sample_tracker_dict["country_codes"]

    def test_get_all_data_deserializes_networks(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that networks are deserialized from JSON."""
        trackers = db.get_all_data()

        assert trackers[0].networks == sample_tracker_dict["networks"]

    def test_get_all_data_deserializes_historic_as_deque(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that historic is deserialized as a deque with maxlen."""
        trackers = db.get_all_data()

        assert isinstance(trackers[0].historic, deque)
        assert list(trackers[0].historic) == sample_tracker_dict["historic"]
        assert trackers[0].historic.maxlen == 1000

    def test_get_all_data_returns_correct_scalar_fields(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_dict: dict[str, Any]
    ) -> None:
        """Verify that scalar fields are returned correctly."""
        trackers = db.get_all_data()
        tracker = trackers[0]

        assert tracker.latency == sample_tracker_dict["latency"]
        assert tracker.last_checked == sample_tracker_dict["last_checked"]
        assert tracker.interval == sample_tracker_dict["interval"]
        assert tracker.status == sample_tracker_dict["status"]
        assert tracker.uptime == sample_tracker_dict["uptime"]
        assert tracker.added == sample_tracker_dict["added"]
        assert tracker.last_downtime == sample_tracker_dict["last_downtime"]
        assert tracker.last_uptime == sample_tracker_dict["last_uptime"]

    def test_get_all_data_returns_empty_list_when_no_trackers(self, patched_db: sqlite3.Connection) -> None:
        """Verify that get_all_data returns empty list when DB is empty."""
        trackers = db.get_all_data()

        assert trackers == []

    def test_get_all_data_orders_by_uptime_descending(self, patched_db: sqlite3.Connection) -> None:
        """Verify that trackers are ordered by uptime in descending order."""
        # Insert trackers with different uptimes
        for i, uptime in enumerate([50, 99, 75]):
            patched_db.execute(
                "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"tracker{i}.example.com",
                    f"udp://tracker{i}.example.com:6969/announce",
                    json.dumps(["1.2.3.4"]),
                    100,
                    1700000000,
                    1800,
                    1,
                    uptime,
                    json.dumps(["US"]),
                    json.dumps(["us"]),
                    json.dumps(["ISP"]),
                    "01-01-2024",
                    json.dumps([1] * 10),
                    1699990000,
                    1700000000,
                ),
            )
        patched_db.commit()

        trackers = db.get_all_data()

        assert len(trackers) == 3
        assert trackers[0].uptime == 99
        assert trackers[1].uptime == 75
        assert trackers[2].uptime == 50


class TestUpdateTracker:
    """Tests for update_tracker function."""

    def test_update_tracker_updates_url(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates the URL field."""
        sample_tracker_obj.url = "http://tracker.example.com:8080/announce"
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT url FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == "http://tracker.example.com:8080/announce"

    def test_update_tracker_updates_latency(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates latency."""
        sample_tracker_obj.latency = 200
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT latency FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == 200

    def test_update_tracker_updates_status(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates status."""
        sample_tracker_obj.status = 0
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT status FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == 0

    def test_update_tracker_updates_uptime(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates uptime."""
        sample_tracker_obj.uptime = 85
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT uptime FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == 85

    def test_update_tracker_updates_ips_with_json(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker JSON serializes updated IPs."""
        sample_tracker_obj.ips = ["2001:db8::1", "192.168.1.1"]
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT ip FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_ips = json.loads(row[0])
        assert stored_ips == ["2001:db8::1", "192.168.1.1"]

    def test_update_tracker_updates_historic_with_json(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker JSON serializes updated historic."""
        sample_tracker_obj.historic = deque([1, 0, 1, 0, 1], maxlen=1000)
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT historic FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_historic = json.loads(row[0])
        assert stored_historic == [1, 0, 1, 0, 1]

    def test_update_tracker_updates_countries_with_json(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker JSON serializes updated countries."""
        sample_tracker_obj.countries = ["Germany", "France"]
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT country FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_countries = json.loads(row[0])
        assert stored_countries == ["Germany", "France"]

    def test_update_tracker_updates_country_codes_with_json(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker JSON serializes updated country codes."""
        sample_tracker_obj.country_codes = ["de", "fr"]
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT country_code FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_country_codes = json.loads(row[0])
        assert stored_country_codes == ["de", "fr"]

    def test_update_tracker_updates_networks_with_json(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker JSON serializes updated networks."""
        sample_tracker_obj.networks = ["Deutsche Telekom", "Orange"]
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT network FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        stored_networks = json.loads(row[0])
        assert stored_networks == ["Deutsche Telekom", "Orange"]

    def test_update_tracker_updates_last_checked(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates last_checked."""
        sample_tracker_obj.last_checked = 1700001000
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT last_checked FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == 1700001000

    def test_update_tracker_updates_interval(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates interval."""
        sample_tracker_obj.interval = 3600
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT interval FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == 3600

    def test_update_tracker_updates_last_downtime(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates last_downtime."""
        sample_tracker_obj.last_downtime = 1700000500
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT last_downtime FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == 1700000500

    def test_update_tracker_updates_last_uptime(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that update_tracker updates last_uptime."""
        sample_tracker_obj.last_uptime = 1700000999
        db.update_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT last_uptime FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row[0] == 1700000999


class TestDeleteTracker:
    """Tests for delete_tracker function."""

    def test_delete_tracker_removes_tracker(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify that delete_tracker removes the tracker from DB."""
        db.delete_tracker(sample_tracker_obj)

        cursor = patched_db.cursor()
        cursor.execute("SELECT * FROM status WHERE host = ?", (sample_tracker_obj.host,))
        row = cursor.fetchone()

        assert row is None

    def test_delete_tracker_only_removes_specified_tracker(self, patched_db: sqlite3.Connection) -> None:
        """Verify that delete_tracker only removes the specified tracker."""
        # Insert two trackers
        for i in range(2):
            patched_db.execute(
                "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"tracker{i}.example.com",
                    f"udp://tracker{i}.example.com:6969/announce",
                    json.dumps(["1.2.3.4"]),
                    100,
                    1700000000,
                    1800,
                    1,
                    95,
                    json.dumps(["US"]),
                    json.dumps(["us"]),
                    json.dumps(["ISP"]),
                    "01-01-2024",
                    json.dumps([1] * 10),
                    1699990000,
                    1700000000,
                ),
            )
        patched_db.commit()

        tracker_to_delete = Tracker(
            host="tracker0.example.com",
            url="udp://tracker0.example.com:6969/announce",
            ips=["1.2.3.4"],
            latency=100,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=95,
            countries=["US"],
            country_codes=["us"],
            networks=["ISP"],
            historic=deque([1] * 10, maxlen=1000),
            added=1704067200,
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        db.delete_tracker(tracker_to_delete)

        cursor = patched_db.cursor()
        cursor.execute("SELECT host FROM status")
        rows = cursor.fetchall()

        assert len(rows) == 1
        assert rows[0][0] == "tracker1.example.com"

    def test_delete_tracker_no_error_for_nonexistent_tracker(
        self, patched_db: sqlite3.Connection, sample_tracker_obj: Tracker
    ) -> None:
        """Verify that delete_tracker doesn't raise error for nonexistent tracker."""
        # Should not raise an exception
        db.delete_tracker(sample_tracker_obj)


class TestGetApiData:
    """Tests for get_api_data function."""

    @pytest.fixture
    def populated_db(self, patched_db: sqlite3.Connection) -> sqlite3.Connection:
        """Populate DB with various trackers for API tests."""
        trackers = [
            # HTTP tracker with high uptime
            (
                "http.example.com",
                "http://http.example.com:8080/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["US"]),
                json.dumps(["us"]),
                json.dumps(["ISP1"]),
                "01-01-2024",
                json.dumps([1] * 100),
                1699990000,
                1700000000,
            ),
            # HTTPS tracker with high uptime
            (
                "https.example.com",
                "https://https.example.com:443/announce",
                json.dumps(["2.3.4.5"]),
                60,
                1700000000,
                1800,
                1,
                97,
                json.dumps(["UK"]),
                json.dumps(["uk"]),
                json.dumps(["ISP2"]),
                "01-01-2024",
                json.dumps([1] * 100),
                1699990000,
                1700000000,
            ),
            # UDP tracker with high uptime
            (
                "udp.example.com",
                "udp://udp.example.com:6969/announce",
                json.dumps(["3.4.5.6"]),
                40,
                1700000000,
                1800,
                1,
                96,
                json.dumps(["DE"]),
                json.dumps(["de"]),
                json.dumps(["ISP3"]),
                "01-01-2024",
                json.dumps([1] * 100),
                1699990000,
                1700000000,
            ),
            # UDP tracker with low uptime
            (
                "udp-low.example.com",
                "udp://udp-low.example.com:6969/announce",
                json.dumps(["4.5.6.7"]),
                80,
                1700000000,
                1800,
                1,
                70,
                json.dumps(["FR"]),
                json.dumps(["fr"]),
                json.dumps(["ISP4"]),
                "01-01-2024",
                json.dumps([1] * 70 + [0] * 30),
                1699990000,
                1700000000,
            ),
            # HTTP tracker that is down
            (
                "down.example.com",
                "http://down.example.com:8080/announce",
                json.dumps(["5.6.7.8"]),
                0,
                1700000000,
                1800,
                0,
                50,
                json.dumps(["ES"]),
                json.dumps(["es"]),
                json.dumps(["ISP5"]),
                "01-01-2024",
                json.dumps([0] * 50 + [1] * 50),
                1700000000,
                1699990000,
            ),
        ]
        for tracker in trackers:
            patched_db.execute(
                "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tracker,
            )
        patched_db.commit()
        return patched_db

    def test_get_api_data_http_returns_http_and_https_trackers(self, populated_db: sqlite3.Connection) -> None:
        """Verify /api/http returns HTTP and HTTPS trackers with uptime >= 95."""
        result = db.get_api_data("/api/http")

        assert "http://http.example.com:8080/announce" in result
        assert "https://https.example.com:443/announce" in result
        assert "udp://udp.example.com:6969/announce" not in result
        assert "http://down.example.com:8080/announce" not in result

    def test_get_api_data_udp_returns_udp_trackers(self, populated_db: sqlite3.Connection) -> None:
        """Verify /api/udp returns only UDP trackers with uptime >= 95."""
        result = db.get_api_data("/api/udp")

        assert "udp://udp.example.com:6969/announce" in result
        assert "http://http.example.com:8080/announce" not in result
        assert "https://https.example.com:443/announce" not in result
        # Low uptime UDP tracker should not be included
        assert "udp://udp-low.example.com:6969/announce" not in result

    def test_get_api_data_live_returns_all_live_trackers(self, populated_db: sqlite3.Connection) -> None:
        """Verify /api/live returns all trackers with status=1."""
        result = db.get_api_data("/api/live")

        # All live trackers regardless of uptime
        assert "http://http.example.com:8080/announce" in result
        assert "https://https.example.com:443/announce" in result
        assert "udp://udp.example.com:6969/announce" in result
        assert "udp://udp-low.example.com:6969/announce" in result
        # Down tracker should not be included
        assert "http://down.example.com:8080/announce" not in result

    def test_get_api_data_percentage_returns_trackers_above_threshold(self, populated_db: sqlite3.Connection) -> None:
        """Verify percentage query returns trackers with uptime >= threshold."""
        result = db.get_api_data("percentage", uptime=80)

        # Should include trackers with uptime >= 80
        assert "http://http.example.com:8080/announce" in result
        assert "https://https.example.com:443/announce" in result
        assert "udp://udp.example.com:6969/announce" in result
        # Should not include trackers with uptime < 80
        assert "udp://udp-low.example.com:6969/announce" not in result
        assert "http://down.example.com:8080/announce" not in result

    def test_get_api_data_percentage_zero_returns_all_trackers(self, populated_db: sqlite3.Connection) -> None:
        """Verify percentage query with 0 returns all trackers."""
        result = db.get_api_data("percentage", uptime=0)

        assert "http://http.example.com:8080/announce" in result
        assert "https://https.example.com:443/announce" in result
        assert "udp://udp.example.com:6969/announce" in result
        assert "udp://udp-low.example.com:6969/announce" in result
        assert "http://down.example.com:8080/announce" in result

    def test_get_api_data_returns_formatted_string(self, populated_db: sqlite3.Connection) -> None:
        """Verify get_api_data returns properly formatted string."""
        result = db.get_api_data("/api/live")

        # Each URL should be on its own line followed by an empty line
        lines = result.strip().split("\n")
        # Filter out empty lines
        urls = [line for line in lines if line.strip()]
        assert len(urls) == 4  # 4 live trackers

    def test_get_api_data_orders_by_uptime_descending(self, populated_db: sqlite3.Connection) -> None:
        """Verify results are ordered by uptime in descending order."""
        result = db.get_api_data("/api/live")

        lines = [line for line in result.strip().split("\n") if line.strip()]
        # First result should be the highest uptime tracker
        assert lines[0] == "http://http.example.com:8080/announce"  # 98%

    def test_get_api_data_exclude_ipv4_only(self, patched_db: sqlite3.Connection) -> None:
        """Verify include_ipv4_only=False filters out IPv4-only trackers."""
        # Insert tracker with only IPv4
        patched_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "ipv4only.example.com",
                "udp://ipv4only.example.com:6969/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["US"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                "01-01-2024",
                json.dumps([1] * 100),
                1699990000,
                1700000000,
            ),
        )
        # Insert tracker with both IPv4 and IPv6
        patched_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "dualstack.example.com",
                "udp://dualstack.example.com:6969/announce",
                json.dumps(["2001:db8::1", "1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                97,
                json.dumps(["US"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                "01-01-2024",
                json.dumps([1] * 100),
                1699990000,
                1700000000,
            ),
        )
        patched_db.commit()

        result = db.get_api_data("/api/live", include_ipv4_only=False)

        assert "udp://ipv4only.example.com:6969/announce" not in result
        assert "udp://dualstack.example.com:6969/announce" in result

    def test_get_api_data_exclude_ipv6_only(self, patched_db: sqlite3.Connection) -> None:
        """Verify include_ipv6_only=False filters out IPv6-only trackers."""
        # Insert tracker with only IPv6
        patched_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "ipv6only.example.com",
                "udp://ipv6only.example.com:6969/announce",
                json.dumps(["2001:db8::1"]),
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["US"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                "01-01-2024",
                json.dumps([1] * 100),
                1699990000,
                1700000000,
            ),
        )
        # Insert tracker with both IPv4 and IPv6
        patched_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "dualstack.example.com",
                "udp://dualstack.example.com:6969/announce",
                json.dumps(["2001:db8::1", "1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                97,
                json.dumps(["US"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                "01-01-2024",
                json.dumps([1] * 100),
                1699990000,
                1700000000,
            ),
        )
        patched_db.commit()

        result = db.get_api_data("/api/live", include_ipv6_only=False)

        assert "udp://ipv6only.example.com:6969/announce" not in result
        assert "udp://dualstack.example.com:6969/announce" in result

    def test_get_api_data_empty_database(self, patched_db: sqlite3.Connection) -> None:
        """Verify get_api_data returns empty string for empty database."""
        result = db.get_api_data("/api/live")

        assert result == ""


class TestJsonSerializationDeserialization:
    """Tests for JSON serialization/deserialization of list fields."""

    def test_roundtrip_empty_lists(self, patched_db: sqlite3.Connection) -> None:
        """Verify empty lists are properly serialized and deserialized."""
        tracker = Tracker(
            host="empty.example.com",
            url="udp://empty.example.com:6969/announce",
            ips=[],
            latency=100,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=95,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque([], maxlen=1000),
            added=1704067200,
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        db.insert_new_tracker(tracker)
        trackers = db.get_all_data()

        assert trackers[0].ips == []
        assert trackers[0].countries == []
        assert trackers[0].country_codes == []
        assert trackers[0].networks == []
        assert list(trackers[0].historic) == []

    def test_roundtrip_special_characters_in_strings(self, patched_db: sqlite3.Connection) -> None:
        """Verify strings with special characters are properly handled."""
        tracker = Tracker(
            host="special.example.com",
            url="udp://special.example.com:6969/announce",
            ips=["1.2.3.4"],
            latency=100,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=95,
            countries=["Cote d'Ivoire", "Sao Tome & Principe"],
            country_codes=["ci", "st"],
            networks=["ISP with 'quotes'", 'ISP with "double quotes"'],
            historic=deque([1, 0, 1], maxlen=1000),
            added=1704067200,
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        db.insert_new_tracker(tracker)
        trackers = db.get_all_data()

        assert trackers[0].countries == ["Cote d'Ivoire", "Sao Tome & Principe"]
        assert trackers[0].networks == [
            "ISP with 'quotes'",
            'ISP with "double quotes"',
        ]

    def test_roundtrip_unicode_characters(self, patched_db: sqlite3.Connection) -> None:
        """Verify Unicode characters are properly handled."""
        tracker = Tracker(
            host="unicode.example.com",
            url="udp://unicode.example.com:6969/announce",
            ips=["1.2.3.4"],
            latency=100,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=95,
            countries=["Deutschland", "Espana", "Nippon"],
            country_codes=["de", "es", "jp"],
            networks=["Telekom", "Telefonica", "NTT"],
            historic=deque([1, 1, 1], maxlen=1000),
            added=1704067200,
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        db.insert_new_tracker(tracker)
        trackers = db.get_all_data()

        assert trackers[0].countries == ["Deutschland", "Espana", "Nippon"]

    def test_roundtrip_large_historic_deque(self, patched_db: sqlite3.Connection) -> None:
        """Verify large historic deques are properly handled."""
        large_historic = [1] * 500 + [0] * 500
        tracker = Tracker(
            host="large.example.com",
            url="udp://large.example.com:6969/announce",
            ips=["1.2.3.4"],
            latency=100,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=50,
            countries=["US"],
            country_codes=["us"],
            networks=["ISP"],
            historic=deque(large_historic, maxlen=1000),
            added=1704067200,
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        db.insert_new_tracker(tracker)
        trackers = db.get_all_data()

        assert list(trackers[0].historic) == large_historic
        assert len(trackers[0].historic) == 1000

    def test_roundtrip_multiple_ipv4_and_ipv6(self, patched_db: sqlite3.Connection) -> None:
        """Verify multiple mixed IP addresses are properly handled."""
        mixed_ips = [
            "2001:db8::1",
            "2001:db8::2",
            "192.168.1.1",
            "10.0.0.1",
        ]
        tracker = Tracker(
            host="mixed.example.com",
            url="udp://mixed.example.com:6969/announce",
            ips=mixed_ips,
            latency=100,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=95,
            countries=["US", "US", "UK", "DE"],
            country_codes=["us", "us", "uk", "de"],
            networks=["ISP1", "ISP2", "ISP3", "ISP4"],
            historic=deque([1, 1, 1], maxlen=1000),
            added=1704067200,
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        db.insert_new_tracker(tracker)
        trackers = db.get_all_data()

        assert trackers[0].ips == mixed_ips
        assert trackers[0].countries is not None
        assert trackers[0].networks is not None
        assert len(trackers[0].countries) == 4
        assert len(trackers[0].networks) == 4

    def test_update_preserves_json_structure(
        self, patched_db: sqlite3.Connection, inserted_sample_tracker: dict[str, Any], sample_tracker_obj: Tracker
    ) -> None:
        """Verify update_tracker preserves JSON structure for list fields."""
        # Update with new list values
        sample_tracker_obj.ips = ["8.8.8.8", "8.8.4.4"]
        sample_tracker_obj.countries = ["United States", "United States"]
        sample_tracker_obj.country_codes = ["us", "us"]
        sample_tracker_obj.networks = ["Google", "Google"]
        sample_tracker_obj.historic = deque([0, 0, 1, 1, 1], maxlen=1000)

        db.update_tracker(sample_tracker_obj)
        trackers = db.get_all_data()

        assert trackers[0].ips == ["8.8.8.8", "8.8.4.4"]
        assert trackers[0].countries == ["United States", "United States"]
        assert trackers[0].country_codes == ["us", "us"]
        assert trackers[0].networks == ["Google", "Google"]
        assert list(trackers[0].historic) == [0, 0, 1, 1, 1]


class TestDatabaseCreation:
    """Tests for database creation functions."""

    def test_create_db_creates_file(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that create_db creates the database file."""
        db_path = tmp_path / "data" / "trackon.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(db, "db_file", str(db_path))

        db.create_db()

        assert db_path.exists()

    def test_create_db_creates_status_table(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that create_db creates the status table with correct schema."""
        db_path = tmp_path / "data" / "trackon.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(db, "db_file", str(db_path))

        db.create_db()

        # Verify table exists and has correct columns
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(status)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        expected_columns = {
            "host": "TEXT",
            "url": "TEXT",
            "ip": "TEXT",
            "latency": "INTEGER",
            "last_checked": "INTEGER",
            "interval": "INTEGER",
            "status": "INTEGER",
            "uptime": "INTEGER",
            "country": "TEXT",
            "country_code": "TEXT",
            "network": "TEXT",
            "added": "INTEGER",
            "historic": "TEXT",
            "last_downtime": "INTEGER",
            "last_uptime": "INTEGER",
        }
        assert columns == expected_columns

    def test_create_db_host_is_primary_key(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that host column is the primary key."""
        db_path = tmp_path / "data" / "trackon.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(db, "db_file", str(db_path))

        db.create_db()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(status)")
        # pk column (index 5) is non-zero for primary key columns
        pk_columns = [row[1] for row in cursor.fetchall() if row[5] != 0]
        conn.close()

        assert pk_columns == ["host"]

    def test_ensure_db_existence_creates_db_when_missing(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that ensure_db_existence calls create_db when file doesn't exist."""
        db_path = tmp_path / "data" / "trackon.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(db, "db_file", str(db_path))

        assert not db_path.exists()

        db.ensure_db_existence()

        assert db_path.exists()

    def test_ensure_db_existence_does_not_recreate_existing_db(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that ensure_db_existence doesn't recreate an existing database."""
        db_path = tmp_path / "data" / "trackon.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(db, "db_file", str(db_path))

        # Create db first
        db.create_db()

        # Insert some data
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO status (host, url) VALUES (?, ?)",
            ("test.host", "udp://test.host:6969"),
        )
        conn.commit()
        conn.close()

        # Call ensure_db_existence - should not recreate
        db.ensure_db_existence()

        # Verify data still exists
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT host FROM status")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "test.host"
