"""Comprehensive tests for the trackon module."""

from __future__ import annotations

import logging
import sqlite3
from collections import deque
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from newTrackon.persistence import HistoryData
from newTrackon.tracker import Tracker


def create_test_tracker(
    url: str,
    host: str | None = None,
    ips: list[str] | None = None,
) -> Tracker:
    """Create a minimal Tracker object for testing."""
    if host is None:
        # Extract host from URL
        from urllib.parse import urlparse

        host = urlparse(url).hostname or "example.com"
    return Tracker(
        url=url,
        host=host,
        ips=ips,
        latency=None,
        last_checked=0,
        interval=10800,
        status=0,
        uptime=0.0,
        countries=None,
        country_codes=None,
        networks=None,
        historic=deque(maxlen=1000),
        added=1704067200,
        last_downtime=0,
        last_uptime=0,
    )


class TestEnqueueNewTrackers:
    """Tests for enqueue_new_trackers function."""

    def test_enqueue_space_separated_urls(self, empty_queues: ModuleType) -> None:
        """Test parsing space-separated tracker URLs."""
        from newTrackon import ingest

        mock_tracker1 = MagicMock()
        mock_tracker1.url = "udp://tracker1.example.com:6969/announce"
        mock_tracker1.ips = ["1.2.3.4"]
        mock_tracker2 = MagicMock()
        mock_tracker2.url = "udp://tracker2.example.com:6969/announce"
        mock_tracker2.ips = ["5.6.7.8"]

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker1.example.com:6969 udp://tracker2.example.com:6969")

            assert mock_add.call_count == 2  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker1.example.com:6969")  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker2.example.com:6969")  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_newline_separated_urls(self, empty_queues: ModuleType) -> None:
        """Test parsing newline-separated tracker URLs."""
        from newTrackon import ingest

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker1.example.com:6969\nudp://tracker2.example.com:6969")

            assert mock_add.call_count == 2  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker1.example.com:6969")  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker2.example.com:6969")  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_tab_separated_urls(self, empty_queues: ModuleType) -> None:
        """Test parsing tab-separated tracker URLs."""
        from newTrackon import ingest

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker1.example.com:6969\tudp://tracker2.example.com:6969")

            assert mock_add.call_count == 2  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_mixed_whitespace_urls(self, empty_queues: ModuleType) -> None:
        """Test parsing URLs with mixed whitespace separators."""
        from newTrackon import ingest

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers(
                "udp://tracker1.example.com:6969\n\tudp://tracker2.example.com:6969  udp://tracker3.example.com:6969"
            )

            assert mock_add.call_count == 3  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_lowercases_urls(self, empty_queues: ModuleType) -> None:
        """Test that URLs are lowercased before processing."""
        from newTrackon import ingest

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("UDP://TRACKER.EXAMPLE.COM:6969")

            mock_add.assert_called_once_with("udp://tracker.example.com:6969")  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_empty_string(self, empty_queues: ModuleType) -> None:
        """Test that empty string does not add any trackers."""
        from newTrackon import ingest

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("")

            mock_add.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_single_url(self, empty_queues: ModuleType) -> None:
        """Test enqueueing a single URL."""
        from newTrackon import ingest

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker.example.com:6969")

            mock_add.assert_called_once_with("udp://tracker.example.com:6969")  # pyright: ignore[reportUnknownMemberType]


class TestAddOneTrackerToSubmittedQueue:
    """Tests for add_one_tracker_to_submitted_queue function."""

    def test_rejects_ip_hostname_ipv4(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that URLs with IPv4 addresses as hostnames are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        with patch("newTrackon.ingest.db.get_all_data", return_value=[]):
            ingest.add_one_tracker_to_submitted_queue("udp://192.168.1.1:6969/announce")

        assert submitted_queue.qsize() == 0

    def test_rejects_ip_hostname_ipv6(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that URLs with IPv6 addresses as hostnames are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        with patch("newTrackon.ingest.db.get_all_data", return_value=[]):
            ingest.add_one_tracker_to_submitted_queue("udp://[2001:db8::1]:6969/announce")

        assert submitted_queue.qsize() == 0

    def test_rejects_already_queued_tracker(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that URLs already in the queue are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        # Add a tracker to the queue first
        existing_tracker = create_test_tracker(url="udp://tracker.example.com:6969/announce")
        submitted_queue.put_nowait(existing_tracker)

        with patch("newTrackon.ingest.Tracker.from_url") as mock_from_url:
            ingest.add_one_tracker_to_submitted_queue("udp://tracker.example.com:6969/announce")

            # Tracker.from_url should not be called since it's already queued
            mock_from_url.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

        # Should still have only the original tracker
        assert submitted_queue.qsize() == 1

    def test_rejects_already_tracked_tracker(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection, sample_tracker: Tracker
    ) -> None:
        """Test that URLs already being tracked are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        # sample_tracker has host="tracker.example.com"
        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[sample_tracker]),
            patch("newTrackon.ingest.Tracker.from_url") as mock_from_url,
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://tracker.example.com:6969/announce")

            # Tracker.from_url should not be called since host is already tracked
            mock_from_url.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

        assert submitted_queue.qsize() == 0

    def test_rejects_tracker_with_duplicate_ip(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with IPs already in the list are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        # Create a tracked tracker with a specific IP
        existing_tracker = create_test_tracker(
            url="udp://existing.example.com:6969/announce",
            host="existing.example.com",
            ips=["93.184.216.34"],
        )

        # Create a new tracker candidate with the same IP
        new_tracker = create_test_tracker(
            url="udp://new.example.com:6969/announce",
            ips=["93.184.216.34"],  # Same IP
        )

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            patch("newTrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 0

    def test_accepts_valid_new_tracker(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that valid new trackers are added to the queue."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=["10.0.0.1"])

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch("newTrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 1
        with submitted_queue.mutex:
            queued = list(submitted_queue.queue)
        assert queued[0] == new_tracker

    def test_handles_tracker_from_url_runtime_error(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that RuntimeError from Tracker.from_url is handled."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.Tracker.from_url",
                side_effect=RuntimeError("Invalid URL"),
            ),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://invalid.example.com:6969/announce")

        assert submitted_queue.qsize() == 0

    def test_handles_tracker_from_url_value_error(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that ValueError from Tracker.from_url is handled."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.Tracker.from_url",
                side_effect=ValueError("Bad value"),
            ),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://bad.example.com:6969/announce")

        assert submitted_queue.qsize() == 0

    def test_accepts_tracker_without_ips(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers without IPs can still be added."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=None)

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch("newTrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 1

    def test_accepts_when_no_ips_tracked(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers are accepted when no IPs are being tracked yet."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=["10.0.0.1"])

        # Return empty list - no trackers being tracked
        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch("newTrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 1


class TestProcessNewTracker:
    """Tests for process_new_tracker function."""

    def test_rejects_interval_too_short(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval < 300 seconds are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_data

        # Add debug data for log_wrong_interval_denial
        submitted_data.appendleft(
            {"url": "udp://tracker.example.com:6969/announce", "time": 0, "status": 1, "ip": "10.0.0.1", "info": ["test info"]}
        )

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 299  # Less than 300

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(299, tracker_candidate.url, 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_rejects_interval_too_long(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval > 10800 seconds are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_data

        # Add debug data for log_wrong_interval_denial
        submitted_data.appendleft(
            {"url": "udp://tracker.example.com:6969/announce", "time": 0, "status": 1, "ip": "10.0.0.1", "info": ["test info"]}
        )

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 10801  # More than 10800

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(10801, tracker_candidate.url, 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_accepts_valid_interval_minimum(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval = 300 seconds are accepted."""
        from newTrackon import ingest

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 300

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(300, tracker_candidate.url, 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_called_once_with(tracker_candidate)

    def test_accepts_valid_interval_maximum(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval = 10800 seconds are accepted."""
        from newTrackon import ingest

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 10800

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(10800, tracker_candidate.url, 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_called_once_with(tracker_candidate)

    def test_rejects_duplicate_ip_during_processing(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that trackers with duplicate IPs are rejected during processing."""
        from newTrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["93.184.216.34"]
        existing_tracker.recent_ips = {"93.184.216.34": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["93.184.216.34"]  # Duplicate IP

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_logs_duplicate_ip_current_during_processing(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that duplicate IPs log current IP conflicts during processing."""
        from newTrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["93.184.216.34"]
        existing_tracker.recent_ips = {"93.184.216.34": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["93.184.216.34"]

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            caplog.at_level(logging.INFO),
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

        assert "current IP overlap with existing.example.com" in caplog.text
        assert "ips=['93.184.216.34']" in caplog.text

    def test_logs_duplicate_ip_recent_during_processing(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that duplicate IPs log recent IP conflicts during processing."""
        from newTrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["10.0.0.2"]
        existing_tracker.recent_ips = {"10.0.0.1": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            caplog.at_level(logging.INFO),
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

        assert "recent IP overlap with existing.example.com" in caplog.text
        assert "ips=['10.0.0.1']" in caplog.text

    def test_logs_grouped_ips_for_same_tracker(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that multiple IPs for the same tracker are logged on one line."""
        from newTrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["1.2.3.4", "5.6.7.8"]
        existing_tracker.recent_ips = {}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["1.2.3.4", "5.6.7.8"]

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            caplog.at_level(logging.INFO),
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

        assert "current IP overlap with existing.example.com, ips=['1.2.3.4', '5.6.7.8']" in caplog.text
        assert caplog.text.count("current IP overlap with existing.example.com") == 1

    def test_rejects_already_tracked_host_during_processing(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that trackers with already tracked hosts are rejected during processing."""
        from newTrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "tracker.example.com"
        existing_tracker.ips = ["10.0.0.1"]
        existing_tracker.recent_ips = {"10.0.0.1": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.2"]  # Different IP but same host

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_rejects_missing_interval(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with missing interval are rejected."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_data

        # Add debug data for log_wrong_interval_denial
        submitted_data.appendleft(
            {"url": "udp://tracker.example.com:6969/announce", "time": 0, "status": 1, "ip": "10.0.0.1", "info": ["test info"]}
        )

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = None

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(None, tracker_candidate.url, 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_handles_attempt_submitted_runtime_error(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that RuntimeError from attempt_submitted is handled."""
        from newTrackon import ingest

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch("newTrackon.ingest.attempt_submitted", side_effect=RuntimeError("Fail")),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_handles_attempt_submitted_value_error(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that ValueError from attempt_submitted is handled."""
        from newTrackon import ingest

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch("newTrackon.ingest.attempt_submitted", side_effect=ValueError("Fail")),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_successful_tracker_insertion(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test successful insertion of a new tracker."""
        from newTrackon import ingest

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 1800

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(1800, tracker_candidate.url, 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_called_once_with(tracker_candidate)
            tracker_candidate.update_ipapi_data.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
            tracker_candidate.is_up.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
            tracker_candidate.update_uptime.assert_called_once()  # pyright: ignore[reportUnknownMemberType]


class TestProcessSubmittedQueue:
    """Tests for process_submitted_queue function."""

    def test_processes_all_queued_trackers(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that all queued trackers are processed."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")

        submitted_queue.put_nowait(tracker1)
        submitted_queue.put_nowait(tracker2)

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "process_new_tracker") as mock_process,
            patch("newTrackon.ingest.save_deque_to_disk"),
        ):
            ingest.process_submitted_queue()

            assert mock_process.call_count == 2  # pyright: ignore[reportUnknownMemberType]
            mock_process.assert_any_call(tracker1)  # pyright: ignore[reportUnknownMemberType]
            mock_process.assert_any_call(tracker2)  # pyright: ignore[reportUnknownMemberType]

    def test_empties_queue(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that the queue is emptied after processing."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")
        submitted_queue.put_nowait(tracker1)
        submitted_queue.put_nowait(tracker2)

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "process_new_tracker"),
            patch("newTrackon.ingest.save_deque_to_disk"),
        ):
            ingest.process_submitted_queue()

        assert submitted_queue.qsize() == 0

    def test_saves_history_to_disk_after_each_tracker(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that history is saved to disk after processing each tracker."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")
        submitted_queue.put_nowait(tracker1)
        submitted_queue.put_nowait(tracker2)

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "process_new_tracker"),
            patch("newTrackon.ingest.save_deque_to_disk") as mock_save,
        ):
            ingest.process_submitted_queue()

            assert mock_save.call_count == 2  # pyright: ignore[reportUnknownMemberType]


class TestWarnOfDuplicateIps:
    """Tests for warn_of_duplicate_ips function."""

    def test_detects_duplicate_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that duplicate IPs are detected and logged."""
        from newTrackon import trackon

        all_ips = ["1.2.3.4", "1.2.3.4"]

        with caplog.at_level(logging.WARNING):
            trackon.warn_of_duplicate_ips(all_ips)

        assert "1.2.3.4 is duplicated" in caplog.text

    def test_detects_multiple_duplicate_ips(
        self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that multiple duplicate IPs are detected."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4", "5.6.7.8"]
        tracker1.recent_ips = {"1.2.3.4": 1700000000, "5.6.7.8": 1700000000}
        tracker2 = MagicMock()
        tracker2.ips = ["1.2.3.4"]  # Duplicate
        tracker2.recent_ips = {"1.2.3.4": 1700000000}
        tracker3 = MagicMock()
        tracker3.ips = ["5.6.7.8"]  # Another duplicate
        tracker3.recent_ips = {"5.6.7.8": 1700000000}
        all_ips, _ = trackon.build_ip_indexes([tracker1, tracker2, tracker3])

        with caplog.at_level(logging.WARNING):
            trackon.warn_of_duplicate_ips(all_ips)

        assert "1.2.3.4 is duplicated" in caplog.text
        assert "5.6.7.8 is duplicated" in caplog.text

    def test_no_warning_for_unique_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that no warning is logged when all IPs are unique."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4"]
        tracker1.recent_ips = {"1.2.3.4": 1700000000}
        tracker2 = MagicMock()
        tracker2.ips = ["5.6.7.8"]
        tracker2.recent_ips = {"5.6.7.8": 1700000000}
        all_ips, _ = trackon.build_ip_indexes([tracker1, tracker2])

        with caplog.at_level(logging.WARNING):
            trackon.warn_of_duplicate_ips(all_ips)

        assert "duplicated" not in caplog.text

    def test_no_warning_when_no_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that no warning is logged when there are no IPs."""
        from newTrackon import trackon

        with caplog.at_level(logging.WARNING):
            trackon.warn_of_duplicate_ips([])

        assert "duplicated" not in caplog.text

    def test_handles_trackers_with_no_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test duplicate detection when some trackers have no IPs."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4"]
        tracker1.recent_ips = {"1.2.3.4": 1700000000}
        tracker2 = MagicMock()
        tracker2.ips = None
        tracker2.recent_ips = {}
        tracker3 = MagicMock()
        tracker3.ips = ["1.2.3.4"]  # Duplicate
        tracker3.recent_ips = {"1.2.3.4": 1700000000}
        all_ips, _ = trackon.build_ip_indexes([tracker1, tracker2, tracker3])

        with caplog.at_level(logging.WARNING):
            trackon.warn_of_duplicate_ips(all_ips)

        assert "1.2.3.4 is duplicated" in caplog.text


class TestWarnOfRecentIpOverlaps:
    """Tests for warn_of_recent_ip_overlaps function."""

    def test_detects_recent_ip_overlap(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that recent IP overlaps are detected and logged."""
        from newTrackon import trackon

        tracker1 = create_test_tracker("udp://tracker1.example.com:6969/announce", ips=["9.9.9.9"])
        tracker1.recent_ips = {"1.2.3.4": 1700000000}

        tracker2 = create_test_tracker("udp://tracker2.example.com:6969/announce", ips=["1.2.3.4"])
        tracker2.recent_ips = {}
        trackers = [tracker1, tracker2]
        _, recent_index = trackon.build_ip_indexes(trackers)

        with caplog.at_level(logging.WARNING):
            trackon.warn_of_recent_ip_overlaps(trackers, recent_index)

        assert "Tracker tracker2.example.com resolved to IP 1.2.3.4 recently seen on tracker1.example.com" in caplog.text

    def test_no_warning_for_no_overlap(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that no warning is logged when there is no recent IP overlap."""
        from newTrackon import trackon

        tracker1 = create_test_tracker("udp://tracker1.example.com:6969/announce", ips=["1.2.3.4"])
        tracker1.recent_ips = {"1.2.3.4": 1700000000}

        tracker2 = create_test_tracker("udp://tracker2.example.com:6969/announce", ips=["5.6.7.8"])
        tracker2.recent_ips = {}
        trackers = [tracker1, tracker2]
        _, recent_index = trackon.build_ip_indexes(trackers)

        with caplog.at_level(logging.WARNING):
            trackon.warn_of_recent_ip_overlaps(trackers, recent_index)

        assert "recently seen on" not in caplog.text


class TestLogWrongIntervalDenial:
    """Tests for log_wrong_interval_denial function."""

    def test_updates_submitted_data_with_rejection(self, empty_queues: ModuleType) -> None:
        """Test that log_wrong_interval_denial updates submitted_data correctly."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_data

        debug_entry: HistoryData = {
            "url": "udp://tracker.example.com:6969/announce",
            "time": 0,
            "status": 1,
            "ip": "10.0.0.1",
            "info": ["original info"],
        }
        submitted_data.appendleft(debug_entry)

        ingest.log_wrong_interval_denial("test reason")

        updated_entry = submitted_data[0]
        assert updated_entry["status"] == 0
        assert updated_entry["info"][0] == "original info"
        assert "Tracker rejected for test reason" in updated_entry["info"][1]

    def test_preserves_original_info(self, empty_queues: ModuleType) -> None:
        """Test that original info is preserved in the updated entry."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_data

        original_info = "{'interval': 100, 'peers': []}"
        debug_entry: HistoryData = {
            "url": "udp://tracker.example.com:6969/announce",
            "time": 0,
            "status": 1,
            "ip": "10.0.0.1",
            "info": [original_info],
        }
        submitted_data.appendleft(debug_entry)

        ingest.log_wrong_interval_denial("having too short interval")

        updated_entry = submitted_data[0]
        assert updated_entry["info"][0] == original_info


class TestGlobalState:
    """Tests for global state management."""

    def test_locks_exist(self) -> None:
        """Test that threading locks are properly initialized."""
        from threading import Lock

        from newTrackon import ingest

        assert isinstance(ingest.list_lock, type(Lock()))


class TestIntegration:
    """Integration tests for the trackon module."""

    def test_full_enqueue_and_process_flow(self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test the full flow from enqueueing to processing."""
        from newTrackon import ingest
        from newTrackon.persistence import submitted_queue

        mock_tracker = MagicMock()
        mock_tracker.url = "udp://tracker.example.com:6969/announce"
        mock_tracker.ips = ["10.0.0.1"]
        mock_tracker.interval = 1800

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch("newTrackon.ingest.Tracker.from_url", return_value=mock_tracker),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(1800, mock_tracker.url, 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
            patch("newTrackon.ingest.save_deque_to_disk"),
        ):
            ingest.enqueue_new_trackers("udp://tracker.example.com:6969")
            ingest.process_submitted_queue()

            mock_insert.assert_called_once_with(mock_tracker)

        assert submitted_queue.qsize() == 0

    def test_multiple_trackers_enqueue_and_process(
        self, empty_queues: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test enqueueing and processing multiple trackers."""
        from newTrackon import ingest

        trackers: list[MagicMock] = []
        for i in range(3):
            t = MagicMock()
            t.url = f"udp://tracker{i}.example.com:6969/announce"
            t.ips = [f"10.0.0.{i}"]
            t.interval = 1800
            trackers.append(t)

        tracker_index = [0]

        def create_tracker(url: str) -> MagicMock:
            idx = tracker_index[0]
            tracker_index[0] += 1
            return trackers[idx]

        with (
            patch("newTrackon.ingest.db.get_all_data", return_value=[]),
            patch("newTrackon.ingest.Tracker.from_url", side_effect=create_tracker),
            patch(
                "newTrackon.ingest.attempt_submitted",
                return_value=(1800, "", 50),
            ),
            patch("newTrackon.ingest.db.insert_new_tracker") as mock_insert,
            patch("newTrackon.ingest.save_deque_to_disk"),
        ):
            ingest.enqueue_new_trackers(
                "udp://tracker0.example.com:6969 udp://tracker1.example.com:6969 udp://tracker2.example.com:6969"
            )
            ingest.process_submitted_queue()

            assert mock_insert.call_count == 3  # pyright: ignore[reportUnknownMemberType]


class TestUpdateOutdatedTrackers:
    """Tests for update_outdated_trackers function."""

    def test_no_outdated_trackers(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that no trackers are updated when all are recent."""
        from newTrackon import trackon

        # Create a tracker that was checked recently (now - last_checked < interval)
        recent_tracker = MagicMock()
        recent_tracker.url = "udp://tracker.example.com:6969/announce"
        recent_tracker.last_checked = 1000  # Checked at time 1000
        recent_tracker.interval = 300  # 5 minute interval
        recent_tracker.to_be_deleted = False

        with (
            patch("newTrackon.trackon.time", return_value=1100),  # Now is 1100, so 100 seconds passed < 300 interval
            patch("newTrackon.trackon.db.get_all_data", return_value=[recent_tracker]),
            patch("newTrackon.trackon.db.update_tracker") as mock_update,
            patch("newTrackon.trackon.db.delete_tracker") as mock_delete,
            patch("newTrackon.trackon.save_deque_to_disk") as mock_save,
            patch("newTrackon.trackon.sleep", side_effect=StopIteration),  # Break the infinite loop
        ):
            try:
                trackon.update_outdated_trackers()
            except StopIteration:
                pass  # Expected to break the loop

            # No trackers should be updated since none are outdated
            recent_tracker.update_status.assert_not_called()  # pyright: ignore[reportUnknownMemberType]
            mock_update.assert_not_called()
            mock_delete.assert_not_called()
            mock_save.assert_not_called()

    def test_outdated_tracker_gets_updated(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that outdated tracker gets updated (not deleted)."""
        from newTrackon import trackon

        # Create a tracker that is outdated (now - last_checked > interval)
        outdated_tracker = MagicMock()
        outdated_tracker.url = "udp://tracker.example.com:6969/announce"
        outdated_tracker.last_checked = 1000  # Checked at time 1000
        outdated_tracker.interval = 300  # 5 minute interval
        outdated_tracker.to_be_deleted = False  # Should NOT be deleted

        with (
            patch("newTrackon.trackon.time", return_value=1500),  # Now is 1500, so 500 seconds passed > 300 interval
            patch("newTrackon.trackon.db.get_all_data", return_value=[outdated_tracker]),
            patch("newTrackon.trackon.db.update_tracker") as mock_update,
            patch("newTrackon.trackon.db.delete_tracker") as mock_delete,
            patch("newTrackon.trackon.save_deque_to_disk") as mock_save,
            patch("newTrackon.trackon.sleep", side_effect=StopIteration),  # Break the infinite loop
        ):
            try:
                trackon.update_outdated_trackers()
            except StopIteration:
                pass  # Expected to break the loop

            # Tracker should be updated
            outdated_tracker.update_status.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
            mock_update.assert_called_once_with(outdated_tracker)
            mock_delete.assert_not_called()
            mock_save.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

    def test_outdated_tracker_gets_deleted(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that outdated tracker marked for deletion gets deleted."""
        from newTrackon import trackon

        # Create a tracker that is outdated and marked for deletion
        outdated_tracker = MagicMock()
        outdated_tracker.url = "udp://tracker.example.com:6969/announce"
        outdated_tracker.last_checked = 1000  # Checked at time 1000
        outdated_tracker.interval = 300  # 5 minute interval
        outdated_tracker.to_be_deleted = True  # Should be deleted

        with (
            patch("newTrackon.trackon.time", return_value=1500),  # Now is 1500, so 500 seconds passed > 300 interval
            patch("newTrackon.trackon.db.get_all_data", return_value=[outdated_tracker]),
            patch("newTrackon.trackon.db.update_tracker") as mock_update,
            patch("newTrackon.trackon.db.delete_tracker") as mock_delete,
            patch("newTrackon.trackon.save_deque_to_disk") as mock_save,
            patch("newTrackon.trackon.sleep", side_effect=StopIteration),  # Break the infinite loop
        ):
            try:
                trackon.update_outdated_trackers()
            except StopIteration:
                pass  # Expected to break the loop

            # Tracker should be deleted, not updated
            outdated_tracker.update_status.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
            mock_delete.assert_called_once_with(outdated_tracker)
            mock_update.assert_not_called()
            mock_save.assert_called_once()  # pyright: ignore[reportUnknownMemberType]


class TestWarnOfIpConflictsPeriodic:
    """Tests for periodic IP conflict warnings."""

    def test_warn_of_ip_conflicts_uses_single_db_snapshot(self, mock_db_connection: sqlite3.Connection) -> None:
        """warn_of_ip_conflicts should fetch data once and fan out to both warning paths."""
        from newTrackon import trackon

        trackers = [MagicMock()]

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=trackers) as mock_get,
            patch("newTrackon.trackon.warn_of_duplicate_ips") as mock_duplicates,
            patch("newTrackon.trackon.warn_of_recent_ip_overlaps") as mock_recent,
        ):
            trackon.warn_of_ip_conflicts()

        mock_get.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
        mock_duplicates.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
        mock_recent.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

    def test_warn_of_ip_conflicts_periodically_runs_every_120_seconds(self, mock_db_connection: sqlite3.Connection) -> None:
        """warn_of_ip_conflicts_periodically should run loop body every 120 seconds."""
        from newTrackon import trackon

        with (
            patch("newTrackon.trackon.warn_of_ip_conflicts") as mock_warn,
            patch("newTrackon.trackon.sleep", side_effect=StopIteration) as mock_sleep,
        ):
            try:
                trackon.warn_of_ip_conflicts_periodically()
            except StopIteration:
                pass

        mock_warn.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
        mock_sleep.assert_called_once_with(120)  # pyright: ignore[reportUnknownMemberType]
