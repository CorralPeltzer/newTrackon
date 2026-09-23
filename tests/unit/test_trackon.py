"""Comprehensive tests for the trackon module."""

from __future__ import annotations

import logging
from collections import deque
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from newtrackon.persistence import HistoryData
from newtrackon.tracker import Tracker


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

    @pytest.mark.usefixtures("empty_queues")
    def test_enqueue_space_separated_urls(self) -> None:
        """Test parsing space-separated tracker URLs."""
        from newtrackon import ingest

        mock_tracker1 = MagicMock()
        mock_tracker1.url = "udp://tracker1.example.com:6969/announce"
        mock_tracker1.ips = ["1.2.3.4"]
        mock_tracker2 = MagicMock()
        mock_tracker2.url = "udp://tracker2.example.com:6969/announce"
        mock_tracker2.ips = ["5.6.7.8"]

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker1.example.com:6969 udp://tracker2.example.com:6969")

            assert mock_add.call_count == 2
            mock_add.assert_any_call("udp://tracker1.example.com:6969")
            mock_add.assert_any_call("udp://tracker2.example.com:6969")

    @pytest.mark.usefixtures("empty_queues")
    def test_enqueue_newline_separated_urls(self) -> None:
        """Test parsing newline-separated tracker URLs."""
        from newtrackon import ingest

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker1.example.com:6969\nudp://tracker2.example.com:6969")

            assert mock_add.call_count == 2
            mock_add.assert_any_call("udp://tracker1.example.com:6969")
            mock_add.assert_any_call("udp://tracker2.example.com:6969")

    @pytest.mark.usefixtures("empty_queues")
    def test_enqueue_tab_separated_urls(self) -> None:
        """Test parsing tab-separated tracker URLs."""
        from newtrackon import ingest

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker1.example.com:6969\tudp://tracker2.example.com:6969")

            assert mock_add.call_count == 2

    @pytest.mark.usefixtures("empty_queues")
    def test_enqueue_mixed_whitespace_urls(self) -> None:
        """Test parsing URLs with mixed whitespace separators."""
        from newtrackon import ingest

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers(
                "udp://tracker1.example.com:6969\n\tudp://tracker2.example.com:6969  udp://tracker3.example.com:6969"
            )

            assert mock_add.call_count == 3

    @pytest.mark.usefixtures("empty_queues")
    def test_enqueue_lowercases_urls(self) -> None:
        """Test that URLs are lowercased before processing."""
        from newtrackon import ingest

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("UDP://TRACKER.EXAMPLE.COM:6969")

            mock_add.assert_called_once_with("udp://tracker.example.com:6969")

    @pytest.mark.usefixtures("empty_queues")
    def test_enqueue_empty_string(self) -> None:
        """Test that empty string does not add any trackers."""
        from newtrackon import ingest

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("")

            mock_add.assert_not_called()

    @pytest.mark.usefixtures("empty_queues")
    def test_enqueue_single_url(self) -> None:
        """Test enqueueing a single URL."""
        from newtrackon import ingest

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "add_one_tracker_to_submitted_queue") as mock_add,
        ):
            ingest.enqueue_new_trackers("udp://tracker.example.com:6969")

            mock_add.assert_called_once_with("udp://tracker.example.com:6969")


class TestAddOneTrackerToSubmittedQueue:
    """Tests for add_one_tracker_to_submitted_queue function."""

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_ip_hostname_ipv4(self) -> None:
        """Test that URLs with IPv4 addresses as hostnames are rejected."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        with patch("newtrackon.ingest.db.get_all_data", return_value=[]):
            ingest.add_one_tracker_to_submitted_queue("udp://192.168.1.1:6969/announce")

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_ip_hostname_ipv6(self) -> None:
        """Test that URLs with IPv6 addresses as hostnames are rejected."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        with patch("newtrackon.ingest.db.get_all_data", return_value=[]):
            ingest.add_one_tracker_to_submitted_queue("udp://[2001:db8::1]:6969/announce")

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_already_queued_tracker(self) -> None:
        """Test that URLs already in the queue are rejected."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        # Add a tracker to the queue first
        existing_tracker = create_test_tracker(url="udp://tracker.example.com:6969/announce")
        submitted_queue.put_nowait(existing_tracker)

        with patch("newtrackon.ingest.Tracker.from_url") as mock_from_url:
            ingest.add_one_tracker_to_submitted_queue("udp://tracker.example.com:6969/announce")

            # Tracker.from_url should not be called since it's already queued
            mock_from_url.assert_not_called()

        # Should still have only the original tracker
        assert submitted_queue.qsize() == 1

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_already_tracked_tracker(self, sample_tracker: Tracker) -> None:
        """Test that URLs already being tracked are rejected."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        # sample_tracker has host="tracker.example.com"
        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[sample_tracker]),
            patch("newtrackon.ingest.Tracker.from_url") as mock_from_url,
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://tracker.example.com:6969/announce")

            # Tracker.from_url should not be called since host is already tracked
            mock_from_url.assert_not_called()

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_tracker_with_duplicate_ip(self) -> None:
        """Test that trackers with IPs already in the list are rejected."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

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
            patch("newtrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            patch("newtrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_accepts_valid_new_tracker(self) -> None:
        """Test that valid new trackers are added to the queue."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=["10.0.0.1"])

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch("newtrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 1
        with submitted_queue.mutex:
            queued = list(cast(deque[Tracker], submitted_queue.queue))
        assert queued[0] == new_tracker

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_handles_tracker_from_url_runtime_error(self) -> None:
        """Test that RuntimeError from Tracker.from_url is handled."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.Tracker.from_url",
                side_effect=RuntimeError("Invalid URL"),
            ),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://invalid.example.com:6969/announce")

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_handles_tracker_from_url_value_error(self) -> None:
        """Test that ValueError from Tracker.from_url is handled."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.Tracker.from_url",
                side_effect=ValueError("Bad value"),
            ),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://bad.example.com:6969/announce")

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_accepts_tracker_without_ips(self) -> None:
        """Test that trackers without IPs can still be added."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=None)

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch("newtrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 1

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_accepts_when_no_ips_tracked(self) -> None:
        """Test that trackers are accepted when no IPs are being tracked yet."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        new_tracker = create_test_tracker(url="udp://new.example.com:6969/announce", ips=["10.0.0.1"])

        # Return empty list - no trackers being tracked
        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch("newtrackon.ingest.Tracker.from_url", return_value=new_tracker),
        ):
            ingest.add_one_tracker_to_submitted_queue("udp://new.example.com:6969/announce")

        assert submitted_queue.qsize() == 1


class TestProcessNewTracker:
    """Tests for process_new_tracker function."""

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_interval_too_short(self) -> None:
        """Test that trackers with interval < 300 seconds are rejected."""
        from newtrackon import ingest
        from newtrackon.persistence import submitted_data

        # Add debug data for log_wrong_interval_denial
        submitted_data.appendleft(
            {"url": "udp://tracker.example.com:6969/announce", "time": 0, "status": 1, "ip": "10.0.0.1", "info": ["test info"]}
        )

        tracker_candidate = MagicMock()
        tracker_url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.url = tracker_url
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 299  # Less than 300

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(299, tracker_url, 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_not_called()

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_interval_too_long(self) -> None:
        """Test that trackers with interval > 10800 seconds are rejected."""
        from newtrackon import ingest
        from newtrackon.persistence import submitted_data

        # Add debug data for log_wrong_interval_denial
        submitted_data.appendleft(
            {"url": "udp://tracker.example.com:6969/announce", "time": 0, "status": 1, "ip": "10.0.0.1", "info": ["test info"]}
        )

        tracker_candidate = MagicMock()
        tracker_url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.url = tracker_url
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 10801  # More than 10800

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(10801, tracker_url, 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_not_called()

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_accepts_valid_interval_minimum(self) -> None:
        """Test that trackers with interval = 300 seconds are accepted."""
        from newtrackon import ingest

        tracker_candidate = MagicMock()
        tracker_url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.url = tracker_url
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 300

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(300, tracker_url, 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_called_once_with(tracker_candidate)

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_accepts_valid_interval_maximum(self) -> None:
        """Test that trackers with interval = 10800 seconds are accepted."""
        from newtrackon import ingest

        tracker_candidate = MagicMock()
        tracker_url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.url = tracker_url
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 10800

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(10800, tracker_url, 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_called_once_with(tracker_candidate)

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_duplicate_ip_during_processing(self) -> None:
        """Test that trackers with duplicate IPs are rejected during processing."""
        from newtrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["93.184.216.34"]
        existing_tracker.recent_ips = {"93.184.216.34": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["93.184.216.34"]  # Duplicate IP

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_not_called()

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_logs_duplicate_ip_current_during_processing(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that duplicate IPs log current IP conflicts during processing."""
        from newtrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["93.184.216.34"]
        existing_tracker.recent_ips = {"93.184.216.34": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["93.184.216.34"]

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            caplog.at_level(logging.INFO),
        ):
            ingest.process_new_tracker(tracker_candidate)

        assert "current IP overlap with existing.example.com" in caplog.text
        assert "ips=['93.184.216.34']" in caplog.text

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_logs_duplicate_ip_recent_during_processing(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that duplicate IPs log recent IP conflicts during processing."""
        from newtrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["10.0.0.2"]
        existing_tracker.recent_ips = {"10.0.0.1": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            caplog.at_level(logging.INFO),
        ):
            ingest.process_new_tracker(tracker_candidate)

        assert "recent IP overlap with existing.example.com" in caplog.text
        assert "ips=['10.0.0.1']" in caplog.text

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_logs_grouped_ips_for_same_tracker(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that multiple IPs for the same tracker are logged on one line."""
        from newtrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "existing.example.com"
        existing_tracker.ips = ["1.2.3.4", "5.6.7.8"]
        existing_tracker.recent_ips = {}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://new.example.com:6969/announce"
        tracker_candidate.ips = ["1.2.3.4", "5.6.7.8"]

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            caplog.at_level(logging.INFO),
        ):
            ingest.process_new_tracker(tracker_candidate)

        assert "current IP overlap with existing.example.com, ips=['1.2.3.4', '5.6.7.8']" in caplog.text
        assert caplog.text.count("current IP overlap with existing.example.com") == 1

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_already_tracked_host_during_processing(self) -> None:
        """Test that trackers with already tracked hosts are rejected during processing."""
        from newtrackon import ingest

        existing_tracker = MagicMock()
        existing_tracker.host = "tracker.example.com"
        existing_tracker.ips = ["10.0.0.1"]
        existing_tracker.recent_ips = {"10.0.0.1": 1700000000}

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.2"]  # Different IP but same host

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[existing_tracker]),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_not_called()

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_rejects_missing_interval(self) -> None:
        """Test that trackers with missing interval are rejected."""
        from newtrackon import ingest
        from newtrackon.persistence import submitted_data

        # Add debug data for log_wrong_interval_denial
        submitted_data.appendleft(
            {"url": "udp://tracker.example.com:6969/announce", "time": 0, "status": 1, "ip": "10.0.0.1", "info": ["test info"]}
        )

        tracker_candidate = MagicMock()
        tracker_url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.url = tracker_url
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = None

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(None, tracker_url, 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_not_called()

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_handles_attempt_submitted_runtime_error(self) -> None:
        """Test that RuntimeError from attempt_submitted is handled."""
        from newtrackon import ingest

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch("newtrackon.ingest.attempt_submitted", side_effect=RuntimeError("Fail")),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_not_called()

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_handles_attempt_submitted_value_error(self) -> None:
        """Test that ValueError from attempt_submitted is handled."""
        from newtrackon import ingest

        tracker_candidate = MagicMock()
        tracker_candidate.url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.ips = ["10.0.0.1"]

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch("newtrackon.ingest.attempt_submitted", side_effect=ValueError("Fail")),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_not_called()

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_successful_tracker_insertion(self) -> None:
        """Test successful insertion of a new tracker."""
        from newtrackon import ingest

        mock_ipapi = MagicMock()
        mock_is_up = MagicMock()
        mock_uptime = MagicMock()
        tracker_candidate = MagicMock(update_ipapi_data=mock_ipapi, is_up=mock_is_up, update_uptime=mock_uptime)
        tracker_url = "udp://tracker.example.com:6969/announce"
        tracker_candidate.url = tracker_url
        tracker_candidate.ips = ["10.0.0.1"]
        tracker_candidate.interval = 1800

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(1800, tracker_url, 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
        ):
            ingest.process_new_tracker(tracker_candidate)

            mock_insert.assert_called_once_with(tracker_candidate)
            mock_ipapi.assert_called_once()
            mock_is_up.assert_called_once()
            mock_uptime.assert_called_once()


class TestProcessSubmittedQueue:
    """Tests for process_submitted_queue function."""

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_processes_all_queued_trackers(self) -> None:
        """Test that all queued trackers are processed."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")

        submitted_queue.put_nowait(tracker1)
        submitted_queue.put_nowait(tracker2)

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "process_new_tracker") as mock_process,
            patch("newtrackon.ingest.save_deque_to_disk"),
        ):
            ingest.process_submitted_queue()

            assert mock_process.call_count == 2
            mock_process.assert_any_call(tracker1)
            mock_process.assert_any_call(tracker2)

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_empties_queue(self) -> None:
        """Test that the queue is emptied after processing."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")
        submitted_queue.put_nowait(tracker1)
        submitted_queue.put_nowait(tracker2)

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "process_new_tracker"),
            patch("newtrackon.ingest.save_deque_to_disk"),
        ):
            ingest.process_submitted_queue()

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_saves_history_to_disk_after_each_tracker(self) -> None:
        """Test that history is saved to disk after processing each tracker."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        tracker1 = create_test_tracker(url="udp://tracker1.example.com:6969/announce")
        tracker2 = create_test_tracker(url="udp://tracker2.example.com:6969/announce")
        submitted_queue.put_nowait(tracker1)
        submitted_queue.put_nowait(tracker2)

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch.object(ingest, "process_new_tracker"),
            patch("newtrackon.ingest.save_deque_to_disk") as mock_save,
        ):
            ingest.process_submitted_queue()

            assert mock_save.call_count == 2


class TestWarnOfIpConflicts:
    """Current duplicates and historical overlaps should produce distinct warnings."""

    @pytest.mark.parametrize(
        ("tracker_data", "expected_messages"),
        [
            pytest.param(
                [("b.example", ["1.2.3.4"], ["1.2.3.4"]), ("a.example", ["1.2.3.4"], ["1.2.3.4"])],
                ["IP 1.2.3.4 is currently shared by a.example, b.example"],
                id="current-duplicate-without-historical-echoes",
            ),
            pytest.param(
                [
                    ("a.example", ["1.2.3.4"], list[str]()),
                    ("b.example", ["1.2.3.4"], list[str]()),
                    ("c.example", None, list[str]()),
                ],
                ["IP 1.2.3.4 is currently shared by a.example, b.example"],
                id="current-duplicate-without-history",
            ),
            pytest.param(
                [("a.example", ["1.2.3.4"], ["1.2.3.4"]), ("b.example", ["5.6.7.8"], ["1.2.3.4", "5.6.7.8"])],
                ["IP 1.2.3.4 currently used by a.example was recently seen on b.example"],
                id="historical-overlap",
            ),
            pytest.param(
                [
                    ("b.example", ["1.2.3.4"], ["1.2.3.4"]),
                    ("a.example", ["1.2.3.4"], ["1.2.3.4"]),
                    ("d.example", None, ["1.2.3.4"]),
                    ("c.example", None, ["1.2.3.4"]),
                ],
                [
                    "IP 1.2.3.4 is currently shared by a.example, b.example",
                    "IP 1.2.3.4 currently used by a.example, b.example was recently seen on c.example, d.example",
                ],
                id="mixed-current-and-historical-overlaps",
            ),
            pytest.param(
                [
                    ("a.example", ["1.2.3.4", "5.6.7.8"], list[str]()),
                    ("b.example", ["1.2.3.4", "5.6.7.8"], list[str]()),
                ],
                [
                    "IP 1.2.3.4 is currently shared by a.example, b.example",
                    "IP 5.6.7.8 is currently shared by a.example, b.example",
                ],
                id="multiple-shared-ips",
            ),
            pytest.param(
                [("a.example", ["1.2.3.4", "1.2.3.4"], ["1.2.3.4"]), ("b.example", ["5.6.7.8"], ["5.6.7.8"])],
                [],
                id="no-overlap-between-hosts",
            ),
            pytest.param(
                [("a.example", None, ["1.2.3.4"]), ("b.example", list[str](), ["1.2.3.4"])],
                [],
                id="historical-ip-with-no-current-users",
            ),
            pytest.param([], [], id="no-trackers"),
        ],
    )
    def test_conflict_warnings(
        self,
        tracker_data: list[tuple[str, list[str] | None, list[str]]],
        expected_messages: list[str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from newtrackon import trackon

        trackers: list[Tracker] = []
        for host, ips, recent_ips in tracker_data:
            tracker = create_test_tracker(f"udp://{host}:6969/announce", ips=ips)
            tracker.recent_ips = dict.fromkeys(recent_ips, 1700000000)
            trackers.append(tracker)

        with (
            patch("newtrackon.trackon.db.get_all_data", return_value=trackers),
            caplog.at_level(logging.WARNING, logger="newtrackon"),
        ):
            trackon.warn_of_ip_conflicts()

        assert caplog.messages == expected_messages


class TestLogWrongIntervalDenial:
    """Tests for log_wrong_interval_denial function."""

    @pytest.mark.usefixtures("empty_queues")
    def test_updates_submitted_data_with_rejection(self) -> None:
        """Test that log_wrong_interval_denial updates submitted_data correctly."""
        from newtrackon import ingest
        from newtrackon.persistence import submitted_data

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

    @pytest.mark.usefixtures("empty_queues")
    def test_preserves_original_info(self) -> None:
        """Test that original info is preserved in the updated entry."""
        from newtrackon import ingest
        from newtrackon.persistence import submitted_data

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

        from newtrackon import ingest

        assert isinstance(ingest.list_lock, type(Lock()))


class TestIntegration:
    """Integration tests for the trackon module."""

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_full_enqueue_and_process_flow(self) -> None:
        """Test the full flow from enqueueing to processing."""
        from newtrackon import ingest
        from newtrackon.ingest import submitted_queue

        mock_tracker = MagicMock()
        tracker_url = "udp://tracker.example.com:6969/announce"
        mock_tracker.url = tracker_url
        mock_tracker.ips = ["10.0.0.1"]
        mock_tracker.interval = 1800

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch("newtrackon.ingest.Tracker.from_url", return_value=mock_tracker),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(1800, tracker_url, 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
            patch("newtrackon.ingest.save_deque_to_disk"),
        ):
            ingest.enqueue_new_trackers("udp://tracker.example.com:6969")
            ingest.process_submitted_queue()

            mock_insert.assert_called_once_with(mock_tracker)

        assert submitted_queue.qsize() == 0

    @pytest.mark.usefixtures("empty_queues", "mock_db_connection")
    def test_multiple_trackers_enqueue_and_process(self) -> None:
        """Test enqueueing and processing multiple trackers."""
        from newtrackon import ingest

        trackers: list[MagicMock] = []
        for i in range(3):
            t = MagicMock()
            t.url = f"udp://tracker{i}.example.com:6969/announce"
            t.ips = [f"10.0.0.{i}"]
            t.interval = 1800
            trackers.append(t)

        tracker_index = [0]

        def create_tracker(_url: str) -> MagicMock:
            idx = tracker_index[0]
            tracker_index[0] += 1
            return trackers[idx]

        with (
            patch("newtrackon.ingest.db.get_all_data", return_value=[]),
            patch("newtrackon.ingest.Tracker.from_url", side_effect=create_tracker),
            patch(
                "newtrackon.ingest.attempt_submitted",
                return_value=(1800, "", 50),
            ),
            patch("newtrackon.ingest.db.insert_new_tracker") as mock_insert,
            patch("newtrackon.ingest.save_deque_to_disk"),
        ):
            ingest.enqueue_new_trackers(
                "udp://tracker0.example.com:6969 udp://tracker1.example.com:6969 udp://tracker2.example.com:6969"
            )
            ingest.process_submitted_queue()

            assert mock_insert.call_count == 3


class TestUpdateOutdatedTrackers:
    """Tests for update_outdated_trackers function."""

    @pytest.mark.usefixtures("mock_db_connection")
    def test_no_outdated_trackers(self) -> None:
        """Test that no trackers are updated when all are recent."""
        from newtrackon import trackon

        # Create a tracker that was checked recently (now - last_checked < interval)
        mock_update_status = MagicMock()
        recent_tracker = MagicMock(update_status=mock_update_status)
        recent_tracker.url = "udp://tracker.example.com:6969/announce"
        recent_tracker.last_checked = 1000  # Checked at time 1000
        recent_tracker.interval = 300  # 5 minute interval
        recent_tracker.to_be_deleted = False

        with (
            patch("newtrackon.trackon.time", return_value=1100),  # Now is 1100, so 100 seconds passed < 300 interval
            patch("newtrackon.trackon.db.get_all_data", return_value=[recent_tracker]),
            patch("newtrackon.trackon.db.update_tracker") as mock_update,
            patch("newtrackon.trackon.db.delete_tracker") as mock_delete,
            patch("newtrackon.trackon.save_deque_to_disk") as mock_save,
            patch("newtrackon.trackon.sleep", side_effect=StopIteration),  # Break the infinite loop
        ):
            try:
                trackon.update_outdated_trackers()
            except StopIteration:
                pass  # Expected to break the loop

            # No trackers should be updated since none are outdated
            mock_update_status.assert_not_called()
            mock_update.assert_not_called()
            mock_delete.assert_not_called()
            mock_save.assert_not_called()

    @pytest.mark.usefixtures("mock_db_connection")
    def test_outdated_tracker_gets_updated(self) -> None:
        """Test that outdated tracker gets updated (not deleted)."""
        from newtrackon import trackon

        # Create a tracker that is outdated (now - last_checked > interval)
        mock_update_status = MagicMock()
        outdated_tracker = MagicMock(update_status=mock_update_status)
        outdated_tracker.url = "udp://tracker.example.com:6969/announce"
        outdated_tracker.last_checked = 1000  # Checked at time 1000
        outdated_tracker.interval = 300  # 5 minute interval
        outdated_tracker.to_be_deleted = False  # Should NOT be deleted

        with (
            patch("newtrackon.trackon.time", return_value=1500),  # Now is 1500, so 500 seconds passed > 300 interval
            patch("newtrackon.trackon.db.get_all_data", return_value=[outdated_tracker]),
            patch("newtrackon.trackon.db.update_tracker") as mock_update,
            patch("newtrackon.trackon.db.delete_tracker") as mock_delete,
            patch("newtrackon.trackon.save_deque_to_disk") as mock_save,
            patch("newtrackon.trackon.sleep", side_effect=StopIteration),  # Break the infinite loop
        ):
            try:
                trackon.update_outdated_trackers()
            except StopIteration:
                pass  # Expected to break the loop

            # Tracker should be updated
            mock_update_status.assert_called_once()
            mock_update.assert_called_once_with(outdated_tracker)
            mock_delete.assert_not_called()
            mock_save.assert_called_once()

    @pytest.mark.usefixtures("mock_db_connection")
    def test_outdated_tracker_gets_deleted(self) -> None:
        """Test that outdated tracker marked for deletion gets deleted."""
        from newtrackon import trackon

        # Create a tracker that is outdated and marked for deletion
        mock_update_status = MagicMock()
        outdated_tracker = MagicMock(update_status=mock_update_status)
        outdated_tracker.url = "udp://tracker.example.com:6969/announce"
        outdated_tracker.last_checked = 1000  # Checked at time 1000
        outdated_tracker.interval = 300  # 5 minute interval
        outdated_tracker.to_be_deleted = True  # Should be deleted

        with (
            patch("newtrackon.trackon.time", return_value=1500),  # Now is 1500, so 500 seconds passed > 300 interval
            patch("newtrackon.trackon.db.get_all_data", return_value=[outdated_tracker]),
            patch("newtrackon.trackon.db.update_tracker") as mock_update,
            patch("newtrackon.trackon.db.delete_tracker") as mock_delete,
            patch("newtrackon.trackon.save_deque_to_disk") as mock_save,
            patch("newtrackon.trackon.sleep", side_effect=StopIteration),  # Break the infinite loop
        ):
            try:
                trackon.update_outdated_trackers()
            except StopIteration:
                pass  # Expected to break the loop

            # Tracker should be deleted, not updated
            mock_update_status.assert_called_once()
            mock_delete.assert_called_once_with(outdated_tracker)
            mock_update.assert_not_called()
            mock_save.assert_called_once()


class TestWarnOfIpConflictsPeriodic:
    """Tests for periodic IP conflict warnings."""

    @pytest.mark.usefixtures("mock_db_connection")
    def test_warn_of_ip_conflicts_uses_single_db_snapshot(self) -> None:
        """Current and historical comparisons should use the same database snapshot."""
        from newtrackon import trackon

        trackers = [create_test_tracker("udp://tracker.example.com:6969/announce", ips=["1.2.3.4"])]

        with patch("newtrackon.trackon.db.get_all_data", return_value=trackers) as mock_get:
            trackon.warn_of_ip_conflicts()

        mock_get.assert_called_once()

    @pytest.mark.usefixtures("mock_db_connection")
    def test_warn_of_ip_conflicts_periodically_runs_every_120_seconds(self) -> None:
        """warn_of_ip_conflicts_periodically should run loop body every 120 seconds."""
        from newtrackon import trackon

        with (
            patch("newtrackon.trackon.warn_of_ip_conflicts") as mock_warn,
            patch("newtrackon.trackon.sleep", side_effect=StopIteration) as mock_sleep,
        ):
            try:
                trackon.warn_of_ip_conflicts_periodically()
            except StopIteration:
                pass

        mock_warn.assert_called_once()
        mock_sleep.assert_called_once_with(120)
