"""Comprehensive tests for newTrackon.utils module."""

from typing import Any
from unittest.mock import MagicMock
from urllib.parse import urlparse

from freezegun import freeze_time

from newTrackon.utils import (
    add_api_headers,
    build_httpx_url,
    dict_factory,
    format_list,
    format_time,
    format_uptime_and_downtime_time,
    process_txt_prefs,
    remove_ipvx_only_trackers,
)


class TestAddApiHeaders:
    """Tests for add_api_headers function."""

    def test_adds_cors_header(self):
        """Should add Access-Control-Allow-Origin header with wildcard."""
        resp = MagicMock()
        resp.headers = {}

        result = add_api_headers(resp)

        assert result.headers["Access-Control-Allow-Origin"] == "*"

    def test_sets_mimetype_to_text_plain(self):
        """Should set mimetype to text/plain."""
        resp = MagicMock()
        resp.headers = {}

        result = add_api_headers(resp)

        assert result.mimetype == "text/plain"

    def test_returns_same_response_object(self):
        """Should return the same response object passed in."""
        resp = MagicMock()
        resp.headers = {}

        result = add_api_headers(resp)

        assert result is resp

    def test_overwrites_existing_cors_header(self):
        """Should overwrite any existing CORS header."""
        resp = MagicMock()
        resp.headers = {"Access-Control-Allow-Origin": "https://example.com"}

        result = add_api_headers(resp)

        assert result.headers["Access-Control-Allow-Origin"] == "*"


def _make_mock_row(values: tuple[Any, ...]) -> MagicMock:  # pyright: ignore[reportExplicitAny]
    """Create a MagicMock that behaves like sqlite3.Row (supports indexing and len)."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: values[i]  # pyright: ignore[reportUnknownLambdaType]
    row.__len__ = lambda self: len(values)  # pyright: ignore[reportUnknownLambdaType]
    return row


class TestDictFactory:
    """Tests for dict_factory SQLite row factory."""

    def test_creates_dict_from_cursor_and_row(self):
        """Should create a dictionary mapping column names to row values."""
        cursor = MagicMock()
        cursor.description = [("id",), ("name",), ("value",)]
        row = _make_mock_row((1, "test", 42))

        result = dict_factory(cursor, row)

        assert result == {"id": 1, "name": "test", "value": 42}

    def test_empty_row(self):
        """Should handle empty rows."""
        cursor = MagicMock()
        cursor.description = []
        row = _make_mock_row(())

        result = dict_factory(cursor, row)

        assert result == {}

    def test_single_column(self):
        """Should handle single column rows."""
        cursor = MagicMock()
        cursor.description = [("count",)]
        row = _make_mock_row((100,))

        result = dict_factory(cursor, row)

        assert result == {"count": 100}

    def test_preserves_none_values(self):
        """Should preserve None values in the row."""
        cursor = MagicMock()
        cursor.description = [("id",), ("nullable_col",)]
        row = _make_mock_row((1, None))

        result = dict_factory(cursor, row)

        assert result == {"id": 1, "nullable_col": None}

    def test_various_data_types(self):
        """Should handle various SQLite data types."""
        cursor = MagicMock()
        cursor.description = [("int_col",), ("float_col",), ("text_col",), ("blob_col",)]
        row = _make_mock_row((42, 3.14, "hello", b"binary"))

        result = dict_factory(cursor, row)

        assert result == {
            "int_col": 42,
            "float_col": 3.14,
            "text_col": "hello",
            "blob_col": b"binary",
        }


class TestFormatTime:
    """Tests for format_time function."""

    @freeze_time("2024-01-15 12:00:00")
    def test_singular_second(self):
        """Should return '1 second' for 1 second ago."""
        from time import time

        last_time = time() - 1

        result = format_time(last_time)

        assert result == "1 second"

    @freeze_time("2024-01-15 12:00:00")
    def test_plural_seconds(self):
        """Should return 'X seconds' for less than 60 seconds."""
        from time import time

        last_time = time() - 30

        result = format_time(last_time)

        assert result == "30 seconds"

    @freeze_time("2024-01-15 12:00:00")
    def test_zero_seconds(self):
        """Should return '0 seconds' for current time."""
        from time import time

        last_time = time()

        result = format_time(last_time)

        assert result == "0 seconds"

    @freeze_time("2024-01-15 12:00:00")
    def test_singular_minute(self):
        """Should return '1 minute' for 1 minute ago."""
        from time import time

        last_time = time() - 60

        result = format_time(last_time)

        assert result == "1 minute"

    @freeze_time("2024-01-15 12:00:00")
    def test_plural_minutes(self):
        """Should return 'X minutes' for less than 60 minutes."""
        from time import time

        last_time = time() - (30 * 60)

        result = format_time(last_time)

        assert result == "30 minutes"

    @freeze_time("2024-01-15 12:00:00")
    def test_singular_hour(self):
        """Should return '1 hour' for 1 hour ago."""
        from time import time

        last_time = time() - 3600

        result = format_time(last_time)

        assert result == "1 hour"

    @freeze_time("2024-01-15 12:00:00")
    def test_plural_hours(self):
        """Should return 'X hours' for less than 24 hours."""
        from time import time

        last_time = time() - (12 * 3600)

        result = format_time(last_time)

        assert result == "12 hours"

    @freeze_time("2024-01-15 12:00:00")
    def test_singular_day(self):
        """Should return '1 day' for 1 day ago."""
        from time import time

        last_time = time() - 86400

        result = format_time(last_time)

        assert result == "1 day"

    @freeze_time("2024-01-15 12:00:00")
    def test_plural_days(self):
        """Should return 'X days' for less than 31 days."""
        from time import time

        last_time = time() - (15 * 86400)

        result = format_time(last_time)

        assert result == "15 days"

    @freeze_time("2024-01-15 12:00:00")
    def test_singular_month(self):
        """Should return '1 month' for approximately 1 month ago."""
        from time import time

        # 31 days triggers month calculation (days >= 31)
        last_time = time() - (31 * 86400)

        result = format_time(last_time)

        assert result == "1 month"

    @freeze_time("2024-01-15 12:00:00")
    def test_plural_months(self):
        """Should return 'X months' for less than 12 months."""
        from time import time

        last_time = time() - (6 * 2592000)

        result = format_time(last_time)

        assert result == "6 months"

    @freeze_time("2024-01-15 12:00:00")
    def test_singular_year(self):
        """Should return '1 year' for 1 year ago."""
        from time import time

        last_time = time() - 31536000  # 365 days in seconds

        result = format_time(last_time)

        assert result == "1 year"

    @freeze_time("2024-01-15 12:00:00")
    def test_plural_years(self):
        """Should return 'X years' for multiple years."""
        from time import time

        last_time = time() - (3 * 31536000)

        result = format_time(last_time)

        assert result == "3 years"

    @freeze_time("2024-01-15 12:00:00")
    def test_boundary_59_seconds(self):
        """Should return seconds at 59 second boundary."""
        from time import time

        last_time = time() - 59

        result = format_time(last_time)

        assert result == "59 seconds"

    @freeze_time("2024-01-15 12:00:00")
    def test_boundary_59_minutes(self):
        """Should return minutes at 59 minute boundary."""
        from time import time

        last_time = time() - (59 * 60)

        result = format_time(last_time)

        assert result == "59 minutes"

    @freeze_time("2024-01-15 12:00:00")
    def test_boundary_23_hours(self):
        """Should return hours at 23 hour boundary."""
        from time import time

        last_time = time() - (23 * 3600)

        result = format_time(last_time)

        assert result == "23 hours"

    @freeze_time("2024-01-15 12:00:00")
    def test_boundary_30_days(self):
        """Should return days at 30 day boundary."""
        from time import time

        last_time = time() - (30 * 86400)

        result = format_time(last_time)

        assert result == "30 days"

    @freeze_time("2024-01-15 12:00:00")
    def test_boundary_11_months(self):
        """Should return months at 11 month boundary."""
        from time import time

        last_time = time() - (11 * 2592000)

        result = format_time(last_time)

        assert result == "11 months"


class TestFormatUptimeAndDowntimeTime:
    """Tests for format_uptime_and_downtime_time function."""

    @freeze_time("2024-01-15 12:00:00")
    def test_working_tracker_with_last_downtime(self):
        """Should format working tracker with downtime history."""
        from time import time

        tracker = MagicMock()
        tracker.status = 1
        tracker.last_downtime = time() - 3600  # 1 hour ago

        result = format_uptime_and_downtime_time([tracker])

        assert result[0].status_readable == "Working for 1 hour"
        assert result[0].status_epoch == tracker.last_downtime

    @freeze_time("2024-01-15 12:00:00")
    def test_working_tracker_never_down(self):
        """Should show 'Working' for tracker that was never down."""
        tracker = MagicMock()
        tracker.status = 1
        tracker.last_downtime = None

        result = format_uptime_and_downtime_time([tracker])

        assert result[0].status_readable == "Working"
        assert result[0].status_epoch is None

    @freeze_time("2024-01-15 12:00:00")
    def test_working_tracker_with_zero_downtime(self):
        """Should show 'Working' when last_downtime is 0 (falsy)."""
        tracker = MagicMock()
        tracker.status = 1
        tracker.last_downtime = 0

        result = format_uptime_and_downtime_time([tracker])

        assert result[0].status_readable == "Working"

    @freeze_time("2024-01-15 12:00:00")
    def test_down_tracker_with_last_uptime(self):
        """Should format down tracker with uptime history."""
        import sys
        from time import time

        tracker = MagicMock()
        tracker.status = 0
        tracker.last_uptime = time() - (2 * 86400)  # 2 days ago

        result = format_uptime_and_downtime_time([tracker])

        assert result[0].status_readable == "Down for 2 days"
        assert result[0].status_epoch == sys.maxsize

    @freeze_time("2024-01-15 12:00:00")
    def test_down_tracker_never_up(self):
        """Should show 'Down' for tracker that was never up."""
        import sys

        tracker = MagicMock()
        tracker.status = 0
        tracker.last_uptime = None

        result = format_uptime_and_downtime_time([tracker])

        assert result[0].status_readable == "Down"
        assert result[0].status_epoch == sys.maxsize

    @freeze_time("2024-01-15 12:00:00")
    def test_down_tracker_with_zero_uptime(self):
        """Should show 'Down' when last_uptime is 0 (falsy)."""
        tracker = MagicMock()
        tracker.status = 0
        tracker.last_uptime = 0

        result = format_uptime_and_downtime_time([tracker])

        assert result[0].status_readable == "Down"

    @freeze_time("2024-01-15 12:00:00")
    def test_multiple_trackers(self):
        """Should process multiple trackers correctly."""
        from time import time

        tracker1 = MagicMock()
        tracker1.status = 1
        tracker1.last_downtime = time() - 3600

        tracker2 = MagicMock()
        tracker2.status = 0
        tracker2.last_uptime = time() - 7200

        result = format_uptime_and_downtime_time([tracker1, tracker2])

        assert result[0].status_readable == "Working for 1 hour"
        assert result[1].status_readable == "Down for 2 hours"

    def test_empty_list(self):
        """Should handle empty tracker list."""
        result = format_uptime_and_downtime_time([])

        assert result == []

    def test_returns_same_list(self) -> None:
        """Should return the same list object passed in."""
        trackers: list[Any] = []  # pyright: ignore[reportExplicitAny]

        result = format_uptime_and_downtime_time(trackers)  # pyright: ignore[reportUnknownArgumentType]

        assert result is trackers


class TestRemoveIpvxOnlyTrackers:
    """Tests for remove_ipvx_only_trackers function."""

    def test_remove_ipv4_only_when_version_6(self):
        """Should remove IPv4-only trackers when requesting IPv6."""
        raw_list = [
            ("udp://tracker1.example.com:6969", ["192.168.1.1"]),
            ("udp://tracker2.example.com:6969", ["2001:db8::1"]),
            ("udp://tracker3.example.com:6969", ["192.168.1.2", "2001:db8::2"]),
        ]

        result = remove_ipvx_only_trackers(raw_list, version=6)

        # Should keep only trackers with IPv4 addresses (to keep for IPv6 filtering)
        # When version=6, ip_type_to_keep is IPv4Address, so it keeps trackers that have IPv4
        urls = [url for url, _ in result]
        assert "udp://tracker1.example.com:6969" in urls
        assert "udp://tracker3.example.com:6969" in urls
        assert "udp://tracker2.example.com:6969" not in urls

    def test_remove_ipv6_only_when_version_4(self):
        """Should remove IPv6-only trackers when requesting IPv4."""
        raw_list = [
            ("udp://tracker1.example.com:6969", ["192.168.1.1"]),
            ("udp://tracker2.example.com:6969", ["2001:db8::1"]),
            ("udp://tracker3.example.com:6969", ["192.168.1.2", "2001:db8::2"]),
        ]

        result = remove_ipvx_only_trackers(raw_list, version=4)

        # When version=4, ip_type_to_keep is IPv6Address, so it keeps trackers that have IPv6
        urls = [url for url, _ in result]
        assert "udp://tracker2.example.com:6969" in urls
        assert "udp://tracker3.example.com:6969" in urls
        assert "udp://tracker1.example.com:6969" not in urls

    def test_dual_stack_tracker_kept_for_both_versions(self):
        """Dual-stack trackers should be kept regardless of version filter."""
        raw_list = [
            ("udp://dualstack.example.com:6969", ["192.168.1.1", "2001:db8::1"]),
        ]

        result_v4 = remove_ipvx_only_trackers(raw_list, version=4)
        result_v6 = remove_ipvx_only_trackers(raw_list, version=6)

        assert len(result_v4) == 1
        assert len(result_v6) == 1

    def test_empty_list(self):
        """Should handle empty input list."""
        result = remove_ipvx_only_trackers([], version=4)

        assert result == []

    def test_tracker_with_empty_ips_list(self) -> None:
        """Should filter out trackers with empty IP lists."""
        raw_list: list[tuple[str, list[str]]] = [
            ("udp://tracker1.example.com:6969", []),
            ("udp://tracker2.example.com:6969", ["192.168.1.1"]),
        ]

        result = remove_ipvx_only_trackers(raw_list, version=6)

        # Empty IP list should be filtered out
        assert len(result) == 1
        assert result[0][0] == "udp://tracker2.example.com:6969"

    def test_tracker_with_none_ips_treated_as_falsy(self):
        """Trackers with falsy IP lists should be filtered out."""
        raw_list = [
            ("udp://tracker1.example.com:6969", None),
            ("udp://tracker2.example.com:6969", ["192.168.1.1"]),
        ]

        result = remove_ipvx_only_trackers(raw_list, version=6)  # type: ignore[arg-type]

        assert len(result) == 1
        assert result[0][0] == "udp://tracker2.example.com:6969"

    def test_preserves_ip_list_in_result(self):
        """Should preserve the IP list in the result tuples."""
        raw_list = [
            ("udp://tracker.example.com:6969", ["192.168.1.1", "2001:db8::1"]),
        ]

        result = remove_ipvx_only_trackers(raw_list, version=4)

        assert result[0][1] == ["192.168.1.1", "2001:db8::1"]

    def test_multiple_ipv4_addresses(self):
        """Should handle trackers with multiple IPv4 addresses."""
        raw_list = [
            ("udp://tracker.example.com:6969", ["192.168.1.1", "192.168.1.2", "10.0.0.1"]),
        ]

        result = remove_ipvx_only_trackers(raw_list, version=6)

        assert len(result) == 1

    def test_multiple_ipv6_addresses(self):
        """Should handle trackers with multiple IPv6 addresses."""
        raw_list = [
            ("udp://tracker.example.com:6969", ["2001:db8::1", "2001:db8::2", "fe80::1"]),
        ]

        result = remove_ipvx_only_trackers(raw_list, version=4)

        assert len(result) == 1


class TestFormatList:
    """Tests for format_list function."""

    def test_single_tracker(self):
        """Should format single tracker with double newline."""
        raw_list = [("udp://tracker.example.com:6969", ["192.168.1.1"])]

        result = format_list(raw_list)

        assert result == "udp://tracker.example.com:6969\n\n"

    def test_multiple_trackers(self):
        """Should format multiple trackers with double newlines."""
        raw_list = [
            ("udp://tracker1.example.com:6969", ["192.168.1.1"]),
            ("udp://tracker2.example.com:6969", ["192.168.1.2"]),
            ("http://tracker3.example.com/announce", ["192.168.1.3"]),
        ]

        result = format_list(raw_list)

        expected = (
            "udp://tracker1.example.com:6969\n\nudp://tracker2.example.com:6969\n\nhttp://tracker3.example.com/announce\n\n"
        )
        assert result == expected

    def test_empty_list(self):
        """Should return empty string for empty list."""
        result = format_list([])

        assert result == ""

    def test_ignores_ip_list(self):
        """Should only use URL, ignoring IP list."""
        raw_list = [("udp://tracker.example.com:6969", ["1.1.1.1", "2.2.2.2", "3.3.3.3"])]

        result = format_list(raw_list)

        assert "1.1.1.1" not in result
        assert result == "udp://tracker.example.com:6969\n\n"

    def test_preserves_url_exactly(self) -> None:
        """Should preserve URL exactly as provided."""
        url = "http://tracker.example.com:8080/announce?passkey=abc123"
        raw_list: list[tuple[str, list[str]]] = [(url, [])]

        result = format_list(raw_list)

        assert result == f"{url}\n\n"


class TestProcessTxtPrefs:
    """Tests for process_txt_prefs function."""

    def test_basic_udp_record(self):
        """Should parse basic UDP record."""
        txt_record = "BITTORRENT UDP:6969"

        result = process_txt_prefs(txt_record)

        assert result == [("udp", 6969)]

    def test_basic_tcp_record(self):
        """Should parse basic TCP record."""
        txt_record = "BITTORRENT TCP:80"

        result = process_txt_prefs(txt_record)

        assert result == [("tcp", 80)]

    def test_multiple_protocols(self):
        """Should parse multiple protocol entries."""
        txt_record = "BITTORRENT UDP:6969 TCP:80 UDP:1337"

        result = process_txt_prefs(txt_record)

        assert result == [("udp", 6969), ("tcp", 80), ("udp", 1337)]

    def test_mixed_case_protocol(self):
        """Should only match uppercase protocol prefixes."""
        txt_record = "BITTORRENT udp:6969 Tcp:80 UDP:1337"

        result = process_txt_prefs(txt_record)

        # Only UDP:1337 should match (uppercase)
        assert result == [("udp", 1337)]

    def test_ignores_first_word(self):
        """Should ignore the BITTORRENT prefix word."""
        txt_record = "BITTORRENT UDP:6969"

        result = process_txt_prefs(txt_record)

        assert ("bittorrent", None) not in result
        assert result == [("udp", 6969)]

    def test_limits_to_10_entries(self):
        """Should limit to first 10 entries to prevent DoS."""
        entries = " ".join([f"UDP:{6969 + i}" for i in range(15)])
        txt_record = f"BITTORRENT {entries}"

        result = process_txt_prefs(txt_record)

        assert len(result) == 10

    def test_invalid_port_non_numeric(self):
        """Should ignore entries with non-numeric ports."""
        txt_record = "BITTORRENT UDP:abc TCP:80"

        result = process_txt_prefs(txt_record)

        assert result == [("tcp", 80)]

    def test_empty_port(self):
        """Should ignore entries with empty port."""
        txt_record = "BITTORRENT UDP: TCP:80"

        result = process_txt_prefs(txt_record)

        assert result == [("tcp", 80)]

    def test_malformed_entries(self):
        """Should ignore malformed entries."""
        txt_record = "BITTORRENT UDP6969 TCP80 UDP:6969"

        result = process_txt_prefs(txt_record)

        assert result == [("udp", 6969)]

    def test_empty_record(self):
        """Should handle empty record."""
        txt_record = ""

        result = process_txt_prefs(txt_record)

        assert result == []

    def test_only_bittorrent_prefix(self):
        """Should handle record with only BITTORRENT prefix."""
        txt_record = "BITTORRENT"

        result = process_txt_prefs(txt_record)

        assert result == []

    def test_extra_whitespace(self):
        """Should handle extra whitespace between entries."""
        txt_record = "BITTORRENT   UDP:6969    TCP:80"

        result = process_txt_prefs(txt_record)

        # split() handles multiple spaces
        assert result == [("udp", 6969), ("tcp", 80)]

    def test_port_with_leading_zeros(self):
        """Should handle ports with leading zeros."""
        txt_record = "BITTORRENT UDP:0080"

        result = process_txt_prefs(txt_record)

        assert result == [("udp", 80)]

    def test_unknown_protocol_ignored(self):
        """Should ignore unknown protocols."""
        txt_record = "BITTORRENT UDP:6969 WS:8080 TCP:80"

        result = process_txt_prefs(txt_record)

        assert result == [("udp", 6969), ("tcp", 80)]


class TestBuildHttpxUrl:
    """Tests for build_httpx_url function."""

    def test_https_with_port(self):
        """Should build HTTPS URL preserving explicit port."""
        submitted_url = urlparse("https://tracker.example.com:8443/announce")

        result = build_httpx_url(submitted_url, tls=True)

        assert result == "https://tracker.example.com:8443/announce"

    def test_https_without_port(self):
        """Should build HTTPS URL with default port 443."""
        submitted_url = urlparse("https://tracker.example.com/announce")

        result = build_httpx_url(submitted_url, tls=True)

        assert result == "https://tracker.example.com:443/announce"

    def test_http_with_port(self):
        """Should build HTTP URL preserving explicit port."""
        submitted_url = urlparse("http://tracker.example.com:8080/announce")

        result = build_httpx_url(submitted_url, tls=False)

        assert result == "http://tracker.example.com:8080/announce"

    def test_http_without_port(self):
        """Should build HTTP URL with default port 80."""
        submitted_url = urlparse("http://tracker.example.com/announce")

        result = build_httpx_url(submitted_url, tls=False)

        assert result == "http://tracker.example.com:80/announce"

    def test_tls_true_forces_https(self):
        """Should use HTTPS scheme when tls=True regardless of input."""
        submitted_url = urlparse("http://tracker.example.com:8080/announce")

        result = build_httpx_url(submitted_url, tls=True)

        assert result.startswith("https://")

    def test_tls_false_forces_http(self):
        """Should use HTTP scheme when tls=False regardless of input."""
        submitted_url = urlparse("https://tracker.example.com:8443/announce")

        result = build_httpx_url(submitted_url, tls=False)

        assert result.startswith("http://")

    def test_always_appends_announce_path(self):
        """Should always append /announce path."""
        submitted_url = urlparse("http://tracker.example.com:6969")

        result = build_httpx_url(submitted_url, tls=False)

        assert result.endswith("/announce")

    def test_replaces_original_path_with_announce(self):
        """Should replace original path with /announce."""
        submitted_url = urlparse("http://tracker.example.com:6969/custom/path")

        result = build_httpx_url(submitted_url, tls=False)

        assert result == "http://tracker.example.com:6969/announce"
        assert "/custom/path" not in result

    def test_ipv4_host(self):
        """Should handle IPv4 address as host."""
        submitted_url = urlparse("http://192.168.1.1:6969/announce")

        result = build_httpx_url(submitted_url, tls=False)

        assert result == "http://192.168.1.1:6969/announce"

    def test_ipv6_host(self):
        """Should handle IPv6 address as host."""
        submitted_url = urlparse("http://[2001:db8::1]:6969/announce")

        result = build_httpx_url(submitted_url, tls=False)

        assert result == "http://[2001:db8::1]:6969/announce"

    def test_standard_https_port_443(self):
        """Should handle explicit port 443 for HTTPS."""
        submitted_url = urlparse("https://tracker.example.com:443/announce")

        result = build_httpx_url(submitted_url, tls=True)

        assert result == "https://tracker.example.com:443/announce"

    def test_standard_http_port_80(self):
        """Should handle explicit port 80 for HTTP."""
        submitted_url = urlparse("http://tracker.example.com:80/announce")

        result = build_httpx_url(submitted_url, tls=False)

        assert result == "http://tracker.example.com:80/announce"

    def test_subdomain_host(self):
        """Should preserve subdomain in host."""
        submitted_url = urlparse("http://tracker.cdn.example.com:6969/announce")

        result = build_httpx_url(submitted_url, tls=False)

        assert "tracker.cdn.example.com" in result
