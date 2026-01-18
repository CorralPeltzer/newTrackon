"""Integration tests for end-to-end tracker workflows."""

import json
import sqlite3
from collections import deque
from time import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def shared_memory_db(monkeypatch):
    """Provide a shared in-memory SQLite database that persists across connections.

    Uses a URI-based connection with shared cache to allow multiple connections
    to the same in-memory database.
    """
    # Create the shared database with schema
    conn = sqlite3.connect("file::memory:?cache=shared", uri=True)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS status (
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

    original_connect = sqlite3.connect

    def patched_connect(database, *args, **kwargs):
        if database == "data/trackon.db":
            # Return a new connection to the shared memory database
            return original_connect("file::memory:?cache=shared", uri=True)
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr("sqlite3.connect", patched_connect)

    yield conn

    # Cleanup: drop table and close
    try:
        conn.execute("DROP TABLE IF EXISTS status")
        conn.commit()
        conn.close()
    except Exception:
        pass


class TestTrackerUpdateCycle:
    """Test end-to-end tracker update cycle combining multiple modules."""

    def test_update_status_with_successful_scrape(self, shared_memory_db, sample_tracker, reset_globals):
        """Insert tracker in DB, call update_status() with mocked scraper,
        verify status, uptime, historic updated, and db.update_tracker() persists changes.
        """
        from newTrackon import db

        # Ensure tracker has a recent last_uptime to avoid max_downtime deletion
        sample_tracker.last_uptime = int(time())

        # Insert tracker into DB
        shared_memory_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sample_tracker.host,
                sample_tracker.url,
                json.dumps(sample_tracker.ips),
                sample_tracker.latency,
                sample_tracker.last_checked,
                sample_tracker.interval,
                sample_tracker.status,
                sample_tracker.uptime,
                json.dumps(sample_tracker.countries),
                json.dumps(sample_tracker.country_codes),
                json.dumps(sample_tracker.networks),
                sample_tracker.added,
                json.dumps(list(sample_tracker.historic)),
                sample_tracker.last_downtime,
                sample_tracker.last_uptime,
            ),
        )
        shared_memory_db.commit()

        # Store initial state for comparison
        initial_historic_len = len(sample_tracker.historic)
        initial_last_checked = sample_tracker.last_checked

        # Mock scraper to return successful response
        mock_response = {"interval": 1800, "peers": [], "complete": 10, "incomplete": 5}

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(False, None)),
            patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 6969))]),
            patch("newTrackon.tracker.Tracker.ip_api", return_value="United States\nus\nExample ISP"),
            patch("newTrackon.scraper.announce_udp", return_value=(mock_response, "93.184.216.34")),
        ):
            sample_tracker.update_status()

        # Verify status is updated to UP
        assert sample_tracker.status == 1

        # Verify historic was updated (new entry added)
        assert len(sample_tracker.historic) == initial_historic_len + 1
        assert sample_tracker.historic[-1] == 1  # Last entry should be UP

        # Verify last_checked was updated
        assert sample_tracker.last_checked > initial_last_checked

        # Verify uptime was recalculated
        assert sample_tracker.uptime is not None

        # Verify interval from response
        assert sample_tracker.interval == 1800

        # Persist changes to DB
        db.update_tracker(sample_tracker)

        # Verify changes persisted in database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT status, interval, historic FROM status WHERE host = ?", (sample_tracker.host,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1  # status
        assert row[1] == 1800  # interval
        historic_from_db = json.loads(row[2])
        assert historic_from_db[-1] == 1  # Last historic entry

    def test_update_status_updates_latency(self, shared_memory_db, sample_tracker, reset_globals):
        """Verify latency is calculated and stored after successful scrape."""

        # Ensure tracker has a recent last_uptime to avoid max_downtime deletion
        sample_tracker.last_uptime = int(time())

        # Insert tracker into DB
        shared_memory_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sample_tracker.host,
                sample_tracker.url,
                json.dumps(sample_tracker.ips),
                sample_tracker.latency,
                sample_tracker.last_checked,
                sample_tracker.interval,
                sample_tracker.status,
                sample_tracker.uptime,
                json.dumps(sample_tracker.countries),
                json.dumps(sample_tracker.country_codes),
                json.dumps(sample_tracker.networks),
                sample_tracker.added,
                json.dumps(list(sample_tracker.historic)),
                sample_tracker.last_downtime,
                sample_tracker.last_uptime,
            ),
        )
        shared_memory_db.commit()

        mock_response = {"interval": 1800, "peers": [], "complete": 10, "incomplete": 5}

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(False, None)),
            patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 6969))]),
            patch("newTrackon.tracker.Tracker.ip_api", return_value="United States\nus\nExample ISP"),
            patch("newTrackon.scraper.announce_udp", return_value=(mock_response, "93.184.216.34")),
        ):
            sample_tracker.update_status()

        # Latency should be set (non-negative integer)
        assert sample_tracker.latency is not None
        assert isinstance(sample_tracker.latency, int)
        assert sample_tracker.latency >= 0


class TestTrackerGoesDown:
    """Test workflow when a tracker becomes unresponsive."""

    def test_tracker_goes_down_on_scraper_error(self, shared_memory_db, sample_tracker, reset_globals):
        """Insert working tracker, mock scraper to raise RuntimeError,
        verify status changes to 0 and last_downtime updated.
        """
        # Ensure tracker starts with status UP
        sample_tracker.status = 1
        sample_tracker.last_uptime = int(time())
        initial_last_downtime = sample_tracker.last_downtime

        # Insert tracker into DB
        shared_memory_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sample_tracker.host,
                sample_tracker.url,
                json.dumps(sample_tracker.ips),
                sample_tracker.latency,
                sample_tracker.last_checked,
                sample_tracker.interval,
                sample_tracker.status,
                sample_tracker.uptime,
                json.dumps(sample_tracker.countries),
                json.dumps(sample_tracker.country_codes),
                json.dumps(sample_tracker.networks),
                sample_tracker.added,
                json.dumps(list(sample_tracker.historic)),
                sample_tracker.last_downtime,
                sample_tracker.last_uptime,
            ),
        )
        shared_memory_db.commit()

        # Mock scraper to raise RuntimeError (simulating connection failure)
        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(False, None)),
            patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 6969))]),
            patch("newTrackon.tracker.Tracker.ip_api", return_value="United States\nus\nExample ISP"),
            patch("newTrackon.scraper.announce_udp", side_effect=RuntimeError("UDP timeout")),
        ):
            sample_tracker.update_status()

        # Verify status changed to DOWN
        assert sample_tracker.status == 0

        # Verify last_downtime was updated
        assert sample_tracker.last_downtime > initial_last_downtime
        assert sample_tracker.last_downtime >= int(time()) - 5  # Within 5 seconds of now

        # Verify historic records the down status
        assert sample_tracker.historic[-1] == 0

    def test_tracker_goes_down_updates_database(self, shared_memory_db, sample_tracker, reset_globals):
        """Verify that tracker going down is properly persisted to database."""
        from newTrackon import db

        sample_tracker.status = 1
        sample_tracker.last_uptime = int(time())

        # Insert tracker into DB
        shared_memory_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sample_tracker.host,
                sample_tracker.url,
                json.dumps(sample_tracker.ips),
                sample_tracker.latency,
                sample_tracker.last_checked,
                sample_tracker.interval,
                sample_tracker.status,
                sample_tracker.uptime,
                json.dumps(sample_tracker.countries),
                json.dumps(sample_tracker.country_codes),
                json.dumps(sample_tracker.networks),
                sample_tracker.added,
                json.dumps(list(sample_tracker.historic)),
                sample_tracker.last_downtime,
                sample_tracker.last_uptime,
            ),
        )
        shared_memory_db.commit()

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(False, None)),
            patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 6969))]),
            patch("newTrackon.tracker.Tracker.ip_api", return_value="United States\nus\nExample ISP"),
            patch("newTrackon.scraper.announce_udp", side_effect=RuntimeError("Connection refused")),
        ):
            sample_tracker.update_status()

        # Persist to database
        db.update_tracker(sample_tracker)

        # Verify in database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT status, last_downtime FROM status WHERE host = ?", (sample_tracker.host,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 0  # status is DOWN
        assert row[1] == sample_tracker.last_downtime

    def test_http_tracker_goes_down(self, shared_memory_db, sample_tracker_data, reset_globals):
        """Test HTTP tracker going down."""
        from newTrackon.tracker import Tracker

        # Create HTTP tracker
        sample_tracker_data["url"] = "http://tracker.example.com:80/announce"
        tracker = Tracker(
            host=sample_tracker_data["host"],
            url=sample_tracker_data["url"],
            ips=sample_tracker_data["ips"],
            latency=sample_tracker_data["latency"],
            last_checked=sample_tracker_data["last_checked"],
            interval=sample_tracker_data["interval"],
            status=1,
            uptime=sample_tracker_data["uptime"],
            countries=sample_tracker_data["countries"],
            country_codes=sample_tracker_data["country_codes"],
            networks=sample_tracker_data["networks"],
            historic=deque(sample_tracker_data["historic"], maxlen=1000),
            added=sample_tracker_data["added"],
            last_downtime=sample_tracker_data["last_downtime"],
            last_uptime=int(time()),
        )

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(False, None)),
            patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 80))]),
            patch("newTrackon.tracker.Tracker.ip_api", return_value="United States\nus\nExample ISP"),
            patch("newTrackon.scraper.announce_http", side_effect=RuntimeError("HTTP timeout")),
        ):
            tracker.update_status()

        assert tracker.status == 0
        assert tracker.historic[-1] == 0


class TestNewTrackerSubmissionFlow:
    """Test end-to-end new tracker submission workflow."""

    def test_add_tracker_to_submitted_deque(self, shared_memory_db, empty_deques):
        """Call add_one_tracker_to_submitted_deque with valid URL,
        verify tracker added to submitted_trackers deque.
        """
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://newtracker.example.com:6969/announce"

        # Mock Tracker.from_url to return a valid tracker
        mock_tracker = MagicMock(spec=Tracker)
        mock_tracker.url = test_url
        mock_tracker.host = "newtracker.example.com"
        mock_tracker.ips = ["5.6.7.8"]

        with (
            patch.object(Tracker, "from_url", return_value=mock_tracker),
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
        ):
            trackon.add_one_tracker_to_submitted_deque(test_url)

        # Verify tracker was added to submitted_trackers deque
        assert len(submitted_trackers) == 1
        assert submitted_trackers[0] == mock_tracker

    def test_tracker_ends_up_in_database_after_processing(self, shared_memory_db, empty_deques, reset_globals):
        """Verify tracker ends up in database after full submission processing."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://newtracker.example.com:6969/announce"

        # Create a real Tracker object (not a mock) for proper database insertion
        mock_tracker = Tracker(
            url=test_url,
            host="newtracker.example.com",
            ips=["5.6.7.8"],
            latency=50,
            last_checked=int(time()),
            interval=1800,
            status=1,
            uptime=100.0,
            countries=["United States"],
            country_codes=["us"],
            networks=["Example ISP"],
            historic=deque([1], maxlen=1000),
            added="18-1-2026",
            last_downtime=int(time()),
            last_uptime=int(time()),
        )

        # Mock attempt_submitted to return success
        mock_attempt_result = (1800, test_url, 50)

        # Add tracker to submitted_trackers deque
        submitted_trackers.append(mock_tracker)

        with (
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
        ):
            trackon.process_submitted_deque()

        # Verify tracker was inserted into database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host, url FROM status WHERE host = ?", (mock_tracker.host,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == mock_tracker.host
        assert row[1] == test_url

    def test_full_submission_flow_integration(self, shared_memory_db, empty_deques, reset_globals):
        """Test complete flow from URL submission to database insertion."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://complete-flow.example.com:6969/announce"

        # Create a real Tracker for the flow
        mock_tracker = Tracker(
            url=test_url,
            host="complete-flow.example.com",
            ips=["10.20.30.40"],
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added="18-1-2026",
            last_downtime=None,
            last_uptime=None,
        )

        mock_attempt_result = (1800, test_url, 50)

        with (
            patch.object(Tracker, "from_url", return_value=mock_tracker),
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
            patch.object(mock_tracker, "update_ipapi_data"),
        ):
            # Step 1: Add to submission deque
            trackon.add_one_tracker_to_submitted_deque(test_url)
            assert len(submitted_trackers) == 1

            # Step 2: Process the deque
            trackon.process_submitted_deque()

        # Verify empty deque after processing
        assert len(submitted_trackers) == 0

        # Verify tracker in database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host FROM status WHERE host = ?", ("complete-flow.example.com",))
        row = cursor.fetchone()
        assert row is not None


class TestDuplicateIPRejection:
    """Test rejection of trackers with duplicate IPs."""

    def test_reject_tracker_with_duplicate_ip(self, shared_memory_db, sample_tracker_data, empty_deques):
        """Insert tracker with IP 1.2.3.4, try to add new tracker that
        resolves to same IP, verify rejection.
        """
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        # Insert an existing tracker with known IP
        shared_memory_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sample_tracker_data["host"],
                sample_tracker_data["url"],
                json.dumps(["1.2.3.4"]),  # Known IP
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
        shared_memory_db.commit()

        # Try to add a new tracker that resolves to the same IP
        new_url = "udp://different-tracker.example.com:6969/announce"
        mock_tracker = MagicMock(spec=Tracker)
        mock_tracker.url = new_url
        mock_tracker.host = "different-tracker.example.com"
        mock_tracker.ips = ["1.2.3.4"]  # Same IP as existing tracker

        with patch.object(Tracker, "from_url", return_value=mock_tracker):
            trackon.add_one_tracker_to_submitted_deque(new_url)

        # Verify tracker was NOT added to submitted_trackers deque
        assert len(submitted_trackers) == 0

    def test_reject_tracker_with_overlapping_ips(self, shared_memory_db, sample_tracker_data, empty_deques):
        """Test rejection when new tracker has any IP overlapping with existing."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        # Insert existing tracker with multiple IPs
        shared_memory_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sample_tracker_data["host"],
                sample_tracker_data["url"],
                json.dumps(["1.2.3.4", "5.6.7.8"]),  # Multiple IPs
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
        shared_memory_db.commit()

        # New tracker with one overlapping IP
        new_url = "udp://another-tracker.example.com:6969/announce"
        mock_tracker = MagicMock(spec=Tracker)
        mock_tracker.url = new_url
        mock_tracker.host = "another-tracker.example.com"
        mock_tracker.ips = ["9.10.11.12", "5.6.7.8"]  # 5.6.7.8 overlaps

        with patch.object(Tracker, "from_url", return_value=mock_tracker):
            trackon.add_one_tracker_to_submitted_deque(new_url)

        # Should be rejected
        assert len(submitted_trackers) == 0

    def test_allow_tracker_with_unique_ip(self, shared_memory_db, sample_tracker_data, empty_deques):
        """Test that tracker with unique IP is allowed."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        # Insert existing tracker with known IP
        shared_memory_db.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sample_tracker_data["host"],
                sample_tracker_data["url"],
                json.dumps(["1.2.3.4"]),  # Existing IP
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
        shared_memory_db.commit()

        # New tracker with completely different IP
        new_url = "udp://unique-tracker.example.com:6969/announce"
        mock_tracker = MagicMock(spec=Tracker)
        mock_tracker.url = new_url
        mock_tracker.host = "unique-tracker.example.com"
        mock_tracker.ips = ["9.10.11.12"]  # Different IP

        with patch.object(Tracker, "from_url", return_value=mock_tracker):
            trackon.add_one_tracker_to_submitted_deque(new_url)

        # Should be allowed
        assert len(submitted_trackers) == 1
        assert submitted_trackers[0] == mock_tracker


class TestIntervalValidation:
    """Test interval validation during tracker submission."""

    def test_reject_tracker_with_interval_below_minimum(self, shared_memory_db, empty_deques, reset_globals):
        """Mock scraper to return interval < 300, verify tracker rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_data, submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://low-interval.example.com:6969/announce"

        mock_tracker = Tracker(
            url=test_url,
            host="low-interval.example.com",
            ips=["20.30.40.50"],
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added="18-1-2026",
            last_downtime=None,
            last_uptime=None,
        )

        # Interval of 200 is less than minimum of 300
        mock_attempt_result = (200, test_url, 50)

        # Pre-populate submitted_data with expected debug entry
        submitted_data.appendleft({"url": test_url, "time": int(time()), "status": 1, "info": ["Response data"]})

        submitted_trackers.append(mock_tracker)

        with (
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
            patch.object(mock_tracker, "update_ipapi_data"),
        ):
            trackon.process_submitted_deque()

        # Verify tracker was NOT inserted into database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host FROM status WHERE host = ?", ("low-interval.example.com",))
        row = cursor.fetchone()
        assert row is None

    def test_reject_tracker_with_interval_above_maximum(self, shared_memory_db, empty_deques, reset_globals):
        """Mock scraper to return interval > 10800, verify tracker rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_data, submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://high-interval.example.com:6969/announce"

        mock_tracker = Tracker(
            url=test_url,
            host="high-interval.example.com",
            ips=["30.40.50.60"],
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added="18-1-2026",
            last_downtime=None,
            last_uptime=None,
        )

        # Interval of 15000 is greater than maximum of 10800
        mock_attempt_result = (15000, test_url, 50)

        # Pre-populate submitted_data with expected debug entry
        submitted_data.appendleft({"url": test_url, "time": int(time()), "status": 1, "info": ["Response data"]})

        submitted_trackers.append(mock_tracker)

        with (
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
            patch.object(mock_tracker, "update_ipapi_data"),
        ):
            trackon.process_submitted_deque()

        # Verify tracker was NOT inserted into database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host FROM status WHERE host = ?", ("high-interval.example.com",))
        row = cursor.fetchone()
        assert row is None

    def test_accept_tracker_with_valid_interval(self, shared_memory_db, empty_deques, reset_globals):
        """Verify tracker with interval between 300 and 10800 is accepted."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://valid-interval.example.com:6969/announce"

        mock_tracker = Tracker(
            url=test_url,
            host="valid-interval.example.com",
            ips=["40.50.60.70"],
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added="18-1-2026",
            last_downtime=None,
            last_uptime=None,
        )

        # Valid interval of 1800 (30 minutes)
        mock_attempt_result = (1800, test_url, 50)

        submitted_trackers.append(mock_tracker)

        with (
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
            patch.object(mock_tracker, "update_ipapi_data"),
        ):
            trackon.process_submitted_deque()

        # Verify tracker WAS inserted into database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host, interval FROM status WHERE host = ?", ("valid-interval.example.com",))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "valid-interval.example.com"
        assert row[1] == 1800

    def test_accept_tracker_with_exactly_minimum_interval(self, shared_memory_db, empty_deques, reset_globals):
        """Interval of exactly 300 should be accepted (boundary condition).

        Per code logic: "300 > tracker_candidate.interval" means 300 is NOT rejected.
        """
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://boundary-low.example.com:6969/announce"

        mock_tracker = Tracker(
            url=test_url,
            host="boundary-low.example.com",
            ips=["50.60.70.80"],
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added="18-1-2026",
            last_downtime=None,
            last_uptime=None,
        )

        # Interval of exactly 300 - boundary condition
        mock_attempt_result = (300, test_url, 50)

        submitted_trackers.append(mock_tracker)

        with (
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
            patch.object(mock_tracker, "update_ipapi_data"),
        ):
            trackon.process_submitted_deque()

        # Based on "300 > interval" - 300 > 300 is False, so 300 should be accepted
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host FROM status WHERE host = ?", ("boundary-low.example.com",))
        row = cursor.fetchone()
        assert row is not None

    def test_accept_tracker_with_exactly_maximum_interval(self, shared_memory_db, empty_deques, reset_globals):
        """Interval of exactly 10800 should be accepted."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://boundary-high.example.com:6969/announce"

        mock_tracker = Tracker(
            url=test_url,
            host="boundary-high.example.com",
            ips=["60.70.80.90"],
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added="18-1-2026",
            last_downtime=None,
            last_uptime=None,
        )

        # Interval of exactly 10800 - boundary condition
        mock_attempt_result = (10800, test_url, 50)

        submitted_trackers.append(mock_tracker)

        with (
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
            patch.object(mock_tracker, "update_ipapi_data"),
        ):
            trackon.process_submitted_deque()

        # Based on "interval > 10800" - 10800 > 10800 is False, so accepted
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host, interval FROM status WHERE host = ?", ("boundary-high.example.com",))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == 10800

    def test_reject_tracker_with_missing_interval(self, shared_memory_db, empty_deques, reset_globals):
        """Verify tracker with missing interval is rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers
        from newTrackon.tracker import Tracker

        test_url = "udp://no-interval.example.com:6969/announce"

        mock_tracker = Tracker(
            url=test_url,
            host="no-interval.example.com",
            ips=["70.80.90.100"],
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added="18-1-2026",
            last_downtime=None,
            last_uptime=None,
        )

        # No interval returned (None)
        mock_attempt_result = (None, test_url, 50)

        submitted_trackers.append(mock_tracker)

        with (
            patch.object(trackon, "get_all_ips_tracked", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", return_value=mock_attempt_result),
            patch("newTrackon.trackon.save_deque_to_disk"),
            patch.object(mock_tracker, "update_ipapi_data"),
            patch("newTrackon.trackon.log_wrong_interval_denial"),  # Mock to avoid deque pop error
        ):
            trackon.process_submitted_deque()

        # Verify tracker was NOT inserted into database
        cursor = shared_memory_db.cursor()
        cursor.execute("SELECT host FROM status WHERE host = ?", ("no-interval.example.com",))
        row = cursor.fetchone()
        assert row is None


class TestTrackerDeletionWorkflow:
    """Test workflow for tracker deletion due to prolonged downtime."""

    def test_tracker_marked_for_deletion_after_max_downtime(self, shared_memory_db, sample_tracker_data, reset_globals):
        """Test that tracker is marked for deletion if last_uptime exceeds max_downtime."""
        from newTrackon.tracker import Tracker, max_downtime

        # Create tracker with last_uptime far in the past
        old_uptime = int(time()) - max_downtime - 1000  # Beyond max_downtime

        tracker = Tracker(
            host=sample_tracker_data["host"],
            url=sample_tracker_data["url"],
            ips=sample_tracker_data["ips"],
            latency=sample_tracker_data["latency"],
            last_checked=sample_tracker_data["last_checked"],
            interval=sample_tracker_data["interval"],
            status=1,
            uptime=sample_tracker_data["uptime"],
            countries=sample_tracker_data["countries"],
            country_codes=sample_tracker_data["country_codes"],
            networks=sample_tracker_data["networks"],
            historic=deque(sample_tracker_data["historic"], maxlen=1000),
            added=sample_tracker_data["added"],
            last_downtime=sample_tracker_data["last_downtime"],
            last_uptime=old_uptime,
        )

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(False, None)),
            patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 6969))]),
        ):
            tracker.update_status()

        # Tracker should be marked for deletion
        assert tracker.to_be_deleted is True


class TestTrackerIPResolutionFailure:
    """Test behavior when tracker IP resolution fails."""

    def test_tracker_cleared_on_ip_resolution_failure(self, shared_memory_db, sample_tracker, reset_globals):
        """Test that tracker is cleared when IP resolution fails."""
        sample_tracker.status = 1
        sample_tracker.last_uptime = int(time())

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(False, None)),
            patch("socket.getaddrinfo", side_effect=OSError("DNS resolution failed")),
        ):
            sample_tracker.update_status()

        # Tracker should be marked as down
        assert sample_tracker.status == 0
        assert sample_tracker.ips is None


class TestBEP34Integration:
    """Test BEP34 (DNS-based tracker discovery) integration."""

    def test_tracker_denied_by_bep34(self, shared_memory_db, sample_tracker, reset_globals):
        """Test tracker is marked for deletion when BEP34 denies connection."""
        sample_tracker.status = 1
        sample_tracker.last_uptime = int(time())

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(True, None)),  # Valid BEP34 but denies
        ):
            sample_tracker.update_status()

        # Tracker should be marked for deletion
        assert sample_tracker.to_be_deleted is True

    def test_tracker_updates_url_from_bep34(self, shared_memory_db, sample_tracker, reset_globals):
        """Test tracker URL is updated based on BEP34 preferences."""
        sample_tracker.status = 1
        sample_tracker.last_uptime = int(time())

        # BEP34 returns UDP preference on port 1337
        bep34_prefs = [("udp", 1337)]

        mock_response = {"interval": 1800, "peers": [], "complete": 10, "incomplete": 5}

        with (
            patch("newTrackon.scraper.get_bep_34", return_value=(True, bep34_prefs)),
            patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 1337))]),
            patch("newTrackon.tracker.Tracker.ip_api", return_value="United States\nus\nExample ISP"),
            patch("newTrackon.scraper.announce_udp", return_value=(mock_response, "93.184.216.34")),
        ):
            sample_tracker.update_status()

        # URL should be updated with BEP34 port
        assert ":1337" in sample_tracker.url
        assert sample_tracker.status == 1
