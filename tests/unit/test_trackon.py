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
        added="1-1-2024",
        last_downtime=0,
        last_uptime=0,
    )


class TestEnqueueNewTrackers:
    """Tests for enqueue_new_trackers function."""

    def test_enqueue_space_separated_urls(self, empty_deques: ModuleType) -> None:
        """Test parsing space-separated tracker URLs."""
        from newTrackon import trackon

        mock_tracker1 = MagicMock()
        mock_tracker1.url = "udp://tracker1.example.com:6969/announce"
        mock_tracker1.ips = ["1.2.3.4"]
        mock_tracker2 = MagicMock()
        mock_tracker2.url = "udp://tracker2.example.com:6969/announce"
        mock_tracker2.ips = ["5.6.7.8"]

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque") as mock_add,
            patch.object(trackon, "process_submitted_deque"),
        ):
            trackon.enqueue_new_trackers("udp://tracker1.example.com:6969 udp://tracker2.example.com:6969")

            assert mock_add.call_count == 2  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker1.example.com:6969")  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker2.example.com:6969")  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_newline_separated_urls(self, empty_deques: ModuleType) -> None:
        """Test parsing newline-separated tracker URLs."""
        from newTrackon import trackon

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque") as mock_add,
            patch.object(trackon, "process_submitted_deque"),
        ):
            trackon.enqueue_new_trackers("udp://tracker1.example.com:6969\nudp://tracker2.example.com:6969")

            assert mock_add.call_count == 2  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker1.example.com:6969")  # pyright: ignore[reportUnknownMemberType]
            mock_add.assert_any_call("udp://tracker2.example.com:6969")  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_tab_separated_urls(self, empty_deques: ModuleType) -> None:
        """Test parsing tab-separated tracker URLs."""
        from newTrackon import trackon

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque") as mock_add,
            patch.object(trackon, "process_submitted_deque"),
        ):
            trackon.enqueue_new_trackers("udp://tracker1.example.com:6969\tudp://tracker2.example.com:6969")

            assert mock_add.call_count == 2  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_mixed_whitespace_urls(self, empty_deques: ModuleType) -> None:
        """Test parsing URLs with mixed whitespace separators."""
        from newTrackon import trackon

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque") as mock_add,
            patch.object(trackon, "process_submitted_deque"),
        ):
            trackon.enqueue_new_trackers(
                "udp://tracker1.example.com:6969\n\tudp://tracker2.example.com:6969  udp://tracker3.example.com:6969"
            )

            assert mock_add.call_count == 3  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_lowercases_urls(self, empty_deques: ModuleType) -> None:
        """Test that URLs are lowercased before processing."""
        from newTrackon import trackon

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque") as mock_add,
            patch.object(trackon, "process_submitted_deque"),
        ):
            trackon.enqueue_new_trackers("UDP://TRACKER.EXAMPLE.COM:6969")

            mock_add.assert_called_once_with("udp://tracker.example.com:6969")  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_empty_string(self, empty_deques: ModuleType) -> None:
        """Test that empty string does not add any trackers."""
        from newTrackon import trackon

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque") as mock_add,
            patch.object(trackon, "process_submitted_deque"),
        ):
            trackon.enqueue_new_trackers("")

            mock_add.assert_not_called()  # pyright: ignore[reportUnknownMemberType]
            # process_submitted_deque is still called if processing_trackers is False
            # But since no trackers were added, it won't do much

    def test_enqueue_triggers_processing_when_not_processing(self, empty_deques: ModuleType) -> None:
        """Test that process_submitted_deque is called when not already processing."""
        from newTrackon import trackon

        trackon.processing_trackers = False

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque"),
            patch.object(trackon, "process_submitted_deque") as mock_process,
        ):
            trackon.enqueue_new_trackers("udp://tracker.example.com:6969")

            mock_process.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

    def test_enqueue_skips_processing_when_already_processing(self, empty_deques: ModuleType) -> None:
        """Test that process_submitted_deque is not called when already processing."""
        from newTrackon import trackon

        trackon.processing_trackers = True

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque"),
            patch.object(trackon, "process_submitted_deque") as mock_process,
        ):
            trackon.enqueue_new_trackers("udp://tracker.example.com:6969")

            mock_process.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

        # Reset
        trackon.processing_trackers = False

    def test_enqueue_single_url(self, empty_deques: ModuleType) -> None:
        """Test enqueueing a single URL."""
        from newTrackon import trackon

        with (
            patch.object(trackon, "add_one_tracker_to_submitted_deque") as mock_add,
            patch.object(trackon, "process_submitted_deque"),
        ):
            trackon.enqueue_new_trackers("udp://tracker.example.com:6969")

            mock_add.assert_called_once_with("udp://tracker.example.com:6969")  # pyright: ignore[reportUnknownMemberType]


class TestAddOneTrackerToSubmittedDeque:
    """Tests for add_one_tracker_to_submitted_deque function."""

    def test_rejects_ip_hostname_ipv4(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that URLs with IPv4 addresses as hostnames are rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        with patch("newTrackon.trackon.db.get_all_data", return_value=[]):
            trackon.add_one_tracker_to_submitted_deque("udp://192.168.1.1:6969/announce")

        assert len(submitted_trackers) == 0

    def test_rejects_ip_hostname_ipv6(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that URLs with IPv6 addresses as hostnames are rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        with patch("newTrackon.trackon.db.get_all_data", return_value=[]):
            trackon.add_one_tracker_to_submitted_deque("udp://[2001:db8::1]:6969/announce")

        assert len(submitted_trackers) == 0

    def test_rejects_already_queued_tracker(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that URLs already in the queue are rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        # Add a tracker to the queue first
        existing_tracker = create_test_tracker(url="udp://tracker.example.com:6969/announce")
        submitted_trackers.append(existing_tracker)

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.Tracker.from_url") as mock_from_url,
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://tracker.example.com:6969/announce")

            # Tracker.from_url should not be called since it's already queued
            mock_from_url.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

        # Should still have only the original tracker
        assert len(submitted_trackers) == 1

    def test_rejects_already_tracked_tracker(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection, sample_tracker: Tracker
    ) -> None:
        """Test that URLs already being tracked are rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        # sample_tracker has host="tracker.example.com"
        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[sample_tracker]),
            patch("newTrackon.trackon.Tracker.from_url") as mock_from_url,
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://tracker.example.com:6969/announce")

            # Tracker.from_url should not be called since host is already tracked
            mock_from_url.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

        assert len(submitted_trackers) == 0

    def test_rejects_tracker_with_duplicate_ip(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with IPs already in the list are rejected."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

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
            patch("newTrackon.trackon.db.get_all_data", return_value=[existing_tracker]),
            patch("newTrackon.trackon.Tracker.from_url", return_value=new_tracker),
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://new.example.com:6969/announce")

        assert len(submitted_trackers) == 0

    def test_accepts_valid_new_tracker(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that valid new trackers are added to the queue."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=["10.0.0.1"])

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.Tracker.from_url", return_value=new_tracker),
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://new.example.com:6969/announce")

        assert len(submitted_trackers) == 1
        assert submitted_trackers[0] == new_tracker

    def test_handles_tracker_from_url_runtime_error(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that RuntimeError from Tracker.from_url is handled."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.Tracker.from_url",
                side_effect=RuntimeError("Invalid URL"),
            ),
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://invalid.example.com:6969/announce")

        assert len(submitted_trackers) == 0

    def test_handles_tracker_from_url_value_error(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that ValueError from Tracker.from_url is handled."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.Tracker.from_url",
                side_effect=ValueError("Bad value"),
            ),
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://bad.example.com:6969/announce")

        assert len(submitted_trackers) == 0

    def test_accepts_tracker_without_ips(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers without IPs can still be added."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=None)

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.Tracker.from_url", return_value=new_tracker),
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://new.example.com:6969/announce")

        assert len(submitted_trackers) == 1

    def test_accepts_when_no_ips_tracked(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers are accepted when no IPs are being tracked yet."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=["10.0.0.1"])

        # Return empty list - no trackers being tracked
        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.Tracker.from_url", return_value=new_tracker),
        ):
            trackon.add_one_tracker_to_submitted_deque("udp://new.example.com:6969/announce")

        assert len(submitted_trackers) == 1


class TestProcessNewTracker:
    """Tests for process_new_tracker function."""

    def test_rejects_interval_too_short(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval < 300 seconds are rejected."""
        from newTrackon import trackon
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
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(299, tracker_candidate.url, 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_rejects_interval_too_long(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval > 10800 seconds are rejected."""
        from newTrackon import trackon
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
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(10801, tracker_candidate.url, 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_accepts_valid_interval_minimum(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval = 300 seconds are accepted."""
        from newTrackon import trackon

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 300

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(300, tracker_candidate.url, 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_called_once_with(tracker_candidate)

    def test_accepts_valid_interval_maximum(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with interval = 10800 seconds are accepted."""
        from newTrackon import trackon

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 10800

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(10800, tracker_candidate.url, 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_called_once_with(tracker_candidate)

    def test_rejects_duplicate_ip_during_processing(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that trackers with duplicate IPs are rejected during processing."""
        from newTrackon import trackon

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["93.184.216.34"]

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["93.184.216.34"]  # Duplicate IP

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[existing_tracker]),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_rejects_already_tracked_host_during_processing(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that trackers with already tracked hosts are rejected during processing."""
        from newTrackon import trackon

        existing_tracker = MagicMock()
        existing_tracker.host = "tracker.example.com"
        existing_tracker.ips = ["10.0.0.1"]

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.2"]  # Different IP but same host

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[existing_tracker]),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_rejects_missing_interval(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with missing interval are rejected."""
        from newTrackon import trackon
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
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(None, tracker_candidate.url, 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_handles_attempt_submitted_runtime_error(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that RuntimeError from attempt_submitted is handled."""
        from newTrackon import trackon

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", side_effect=RuntimeError("Fail")),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_handles_attempt_submitted_value_error(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that ValueError from attempt_submitted is handled."""
        from newTrackon import trackon

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.attempt_submitted", side_effect=ValueError("Fail")),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_not_called()

    def test_successful_tracker_insertion(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test successful insertion of a new tracker."""
        from newTrackon import trackon

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 1800

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(1800, tracker_candidate.url, 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
        ):
            trackon.process_new_tracker(tracker_candidate)  # pyright: ignore[reportUnknownArgumentType]

            mock_insert.assert_called_once_with(tracker_candidate)
            tracker_candidate.update_ipapi_data.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
            tracker_candidate.is_up.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
            tracker_candidate.update_uptime.assert_called_once()  # pyright: ignore[reportUnknownMemberType]


class TestProcessSubmittedDeque:
    """Tests for process_submitted_deque function."""

    def test_processes_all_queued_trackers(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that all queued trackers are processed."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")

        submitted_trackers.append(tracker1)
        submitted_trackers.append(tracker2)

        with (
            patch.object(trackon, "process_new_tracker") as mock_process,
            patch("newTrackon.trackon.save_deque_to_disk"),
        ):
            trackon.process_submitted_deque()

            assert mock_process.call_count == 2  # pyright: ignore[reportUnknownMemberType]
            mock_process.assert_any_call(tracker1)  # pyright: ignore[reportUnknownMemberType]
            mock_process.assert_any_call(tracker2)  # pyright: ignore[reportUnknownMemberType]

    def test_sets_processing_flag(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that processing_trackers flag is set and unset correctly."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        tracker = create_test_tracker(url="udp://tracker.example.com:6969/announce")
        submitted_trackers.append(tracker)

        processing_states: list[bool] = []

        def capture_state(t: Tracker) -> None:
            processing_states.append(trackon.processing_trackers)

        with (
            patch.object(trackon, "process_new_tracker", side_effect=capture_state),
            patch("newTrackon.trackon.save_deque_to_disk"),
        ):
            trackon.process_submitted_deque()

        # Should have been True during processing
        assert processing_states == [True]
        # Should be False after processing
        assert trackon.processing_trackers is False

    def test_empties_deque(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test that the deque is emptied after processing."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")
        submitted_trackers.append(tracker1)
        submitted_trackers.append(tracker2)

        with (
            patch.object(trackon, "process_new_tracker"),
            patch("newTrackon.trackon.save_deque_to_disk"),
        ):
            trackon.process_submitted_deque()

        assert len(submitted_trackers) == 0

    def test_saves_deque_to_disk_after_each_tracker(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test that deque is saved to disk after processing each tracker."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")
        submitted_trackers.append(tracker1)
        submitted_trackers.append(tracker2)

        with (
            patch.object(trackon, "process_new_tracker"),
            patch("newTrackon.trackon.save_deque_to_disk") as mock_save,
        ):
            trackon.process_submitted_deque()

            assert mock_save.call_count == 2  # pyright: ignore[reportUnknownMemberType]


class TestGetAllIpsTracked:
    """Tests for get_all_ips_tracked function."""

    def test_returns_all_ips_from_database(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that all IPs from tracked trackers are returned."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4", "5.6.7.8"]
        tracker2 = MagicMock()
        tracker2.ips = ["9.10.11.12"]

        with patch("newTrackon.trackon.db.get_all_data", return_value=[tracker1, tracker2]):
            result = trackon.get_all_ips_tracked()

        assert result == ["1.2.3.4", "5.6.7.8", "9.10.11.12"]

    def test_returns_empty_list_when_no_trackers(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that empty list is returned when no trackers exist."""
        from newTrackon import trackon

        with patch("newTrackon.trackon.db.get_all_data", return_value=[]):
            result = trackon.get_all_ips_tracked()

        assert result == []

    def test_handles_trackers_without_ips(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers without IPs are handled correctly."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4"]
        tracker2 = MagicMock()
        tracker2.ips = None
        tracker3 = MagicMock()
        tracker3.ips = ["5.6.7.8"]

        with patch(
            "newTrackon.trackon.db.get_all_data",
            return_value=[tracker1, tracker2, tracker3],
        ):
            result = trackon.get_all_ips_tracked()

        assert result == ["1.2.3.4", "5.6.7.8"]

    def test_handles_empty_ip_list(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that trackers with empty IP lists are handled correctly."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = []
        tracker2 = MagicMock()
        tracker2.ips = ["1.2.3.4"]

        with patch("newTrackon.trackon.db.get_all_data", return_value=[tracker1, tracker2]):
            result = trackon.get_all_ips_tracked()

        assert result == ["1.2.3.4"]

    def test_returns_ipv6_addresses(self, mock_db_connection: sqlite3.Connection) -> None:
        """Test that IPv6 addresses are included in results."""
        from newTrackon import trackon

        tracker = MagicMock()
        tracker.ips = ["2001:db8::1", "1.2.3.4"]

        with patch("newTrackon.trackon.db.get_all_data", return_value=[tracker]):
            result = trackon.get_all_ips_tracked()

        assert result == ["2001:db8::1", "1.2.3.4"]


class TestWarnOfDuplicateIps:
    """Tests for warn_of_duplicate_ips function."""

    def test_detects_duplicate_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that duplicate IPs are detected and logged."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4"]
        tracker2 = MagicMock()
        tracker2.ips = ["1.2.3.4"]  # Duplicate

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[tracker1, tracker2]),
            caplog.at_level(logging.WARNING),
        ):
            trackon.warn_of_duplicate_ips()

        assert "1.2.3.4 is duplicated" in caplog.text

    def test_detects_multiple_duplicate_ips(
        self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that multiple duplicate IPs are detected."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4", "5.6.7.8"]
        tracker2 = MagicMock()
        tracker2.ips = ["1.2.3.4"]  # Duplicate
        tracker3 = MagicMock()
        tracker3.ips = ["5.6.7.8"]  # Another duplicate

        with (
            patch(
                "newTrackon.trackon.db.get_all_data",
                return_value=[tracker1, tracker2, tracker3],
            ),
            caplog.at_level(logging.WARNING),
        ):
            trackon.warn_of_duplicate_ips()

        assert "1.2.3.4 is duplicated" in caplog.text
        assert "5.6.7.8 is duplicated" in caplog.text

    def test_no_warning_for_unique_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that no warning is logged when all IPs are unique."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4"]
        tracker2 = MagicMock()
        tracker2.ips = ["5.6.7.8"]

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[tracker1, tracker2]),
            caplog.at_level(logging.WARNING),
        ):
            trackon.warn_of_duplicate_ips()

        assert "duplicated" not in caplog.text

    def test_no_warning_when_no_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test that no warning is logged when there are no IPs."""
        from newTrackon import trackon

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            caplog.at_level(logging.WARNING),
        ):
            trackon.warn_of_duplicate_ips()

        assert "duplicated" not in caplog.text

    def test_handles_trackers_with_no_ips(self, mock_db_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture) -> None:
        """Test duplicate detection when some trackers have no IPs."""
        from newTrackon import trackon

        tracker1 = MagicMock()
        tracker1.ips = ["1.2.3.4"]
        tracker2 = MagicMock()
        tracker2.ips = None
        tracker3 = MagicMock()
        tracker3.ips = ["1.2.3.4"]  # Duplicate

        with (
            patch(
                "newTrackon.trackon.db.get_all_data",
                return_value=[tracker1, tracker2, tracker3],
            ),
            caplog.at_level(logging.WARNING),
        ):
            trackon.warn_of_duplicate_ips()

        assert "1.2.3.4 is duplicated" in caplog.text


class TestLogWrongIntervalDenial:
    """Tests for log_wrong_interval_denial function."""

    def test_updates_submitted_data_with_rejection(self, empty_deques: ModuleType) -> None:
        """Test that log_wrong_interval_denial updates submitted_data correctly."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_data

        debug_entry: HistoryData = {
            "url": "udp://tracker.example.com:6969/announce",
            "time": 0,
            "status": 1,
            "ip": "10.0.0.1",
            "info": ["original info"],
        }
        submitted_data.appendleft(debug_entry)

        trackon.log_wrong_interval_denial("test reason")

        updated_entry = submitted_data[0]
        assert updated_entry["status"] == 0
        assert updated_entry["info"][0] == "original info"
        assert "Tracker rejected for test reason" in updated_entry["info"][1]

    def test_preserves_original_info(self, empty_deques: ModuleType) -> None:
        """Test that original info is preserved in the updated entry."""
        from newTrackon import trackon
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

        trackon.log_wrong_interval_denial("having too short interval")

        updated_entry = submitted_data[0]
        assert updated_entry["info"][0] == original_info


class TestGlobalState:
    """Tests for global state management."""

    def test_processing_trackers_initial_value(self, reset_globals: None) -> None:
        """Test that processing_trackers starts as False."""
        from newTrackon import trackon

        assert trackon.processing_trackers is False

    def test_locks_exist(self) -> None:
        """Test that threading locks are properly initialized."""
        from threading import Lock

        from newTrackon import trackon

        assert isinstance(trackon.deque_lock, type(Lock()))
        assert isinstance(trackon.list_lock, type(Lock()))


class TestIntegration:
    """Integration tests for the trackon module."""

    def test_full_enqueue_and_process_flow(self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection) -> None:
        """Test the full flow from enqueueing to processing."""
        from newTrackon import trackon
        from newTrackon.persistence import submitted_trackers

        mock_tracker = MagicMock()
        mock_tracker.url = "udp://tracker.example.com:6969/announce"
        mock_tracker.ips = ["10.0.0.1"]
        mock_tracker.interval = 1800

        with (
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.Tracker.from_url", return_value=mock_tracker),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(1800, mock_tracker.url, 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
            patch("newTrackon.trackon.save_deque_to_disk"),
        ):
            trackon.enqueue_new_trackers("udp://tracker.example.com:6969")

            mock_insert.assert_called_once_with(mock_tracker)

        assert len(submitted_trackers) == 0
        assert trackon.processing_trackers is False

    def test_multiple_trackers_enqueue_and_process(
        self, empty_deques: ModuleType, mock_db_connection: sqlite3.Connection
    ) -> None:
        """Test enqueueing and processing multiple trackers."""
        from newTrackon import trackon

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
            patch("newTrackon.trackon.db.get_all_data", return_value=[]),
            patch("newTrackon.trackon.Tracker.from_url", side_effect=create_tracker),
            patch(
                "newTrackon.trackon.attempt_submitted",
                return_value=(1800, "", 50),
            ),
            patch("newTrackon.trackon.db.insert_new_tracker") as mock_insert,
            patch("newTrackon.trackon.save_deque_to_disk"),
        ):
            trackon.enqueue_new_trackers(
                "udp://tracker0.example.com:6969 udp://tracker1.example.com:6969 udp://tracker2.example.com:6969"
            )

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
            patch("newTrackon.trackon.warn_of_duplicate_ips") as mock_warn,
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
            mock_warn.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

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
            patch("newTrackon.trackon.warn_of_duplicate_ips") as mock_warn,
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
            mock_warn.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

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
            patch("newTrackon.trackon.warn_of_duplicate_ips") as mock_warn,
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
            mock_warn.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
