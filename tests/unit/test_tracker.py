"""Comprehensive tests for the Tracker class in newTrackon.tracker module."""

import socket
from collections import deque
from time import time
from unittest.mock import MagicMock, patch

import pytest

from newTrackon.tracker import Tracker, max_downtime


class TestTrackerInit:
    """Tests for Tracker.__init__ method."""

    def test_init_with_all_fields(self):
        """Test that __init__ correctly assigns all fields."""
        tracker = Tracker(
            url="udp://tracker.example.com:6969/announce",
            host="tracker.example.com",
            ips=["93.184.216.34"],
            latency=50,
            last_checked=1700000000,
            interval=1800,
            status=1,
            uptime=95,
            countries=["United States"],
            country_codes=["us"],
            networks=["Example ISP"],
            historic=deque([1] * 100, maxlen=1000),
            added="01-01-2024",
            last_downtime=1699990000,
            last_uptime=1700000000,
        )

        assert tracker.url == "udp://tracker.example.com:6969/announce"
        assert tracker.host == "tracker.example.com"
        assert tracker.ips == ["93.184.216.34"]
        assert tracker.latency == 50
        assert tracker.last_checked == 1700000000
        assert tracker.interval == 1800
        assert tracker.status == 1
        assert tracker.uptime == 95
        assert tracker.countries == ["United States"]
        assert tracker.country_codes == ["us"]
        assert tracker.networks == ["Example ISP"]
        assert len(tracker.historic) == 100
        assert tracker.added == "01-01-2024"
        assert tracker.last_downtime == 1699990000
        assert tracker.last_uptime == 1700000000
        assert tracker.to_be_deleted is False

    def test_init_with_none_values(self):
        """Test that __init__ handles None values for optional fields."""
        tracker = Tracker(
            url="udp://tracker.example.com:6969/announce",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )

        assert tracker.url == "udp://tracker.example.com:6969/announce"
        assert tracker.host is None
        assert tracker.ips is None
        assert tracker.to_be_deleted is False


class TestValidateUrl:
    """Tests for Tracker.validate_url method."""

    def test_validate_url_udp_scheme(self, mock_network):
        """Test that UDP scheme is accepted."""
        tracker = Tracker(
            url="udp://tracker.example.com:6969",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        tracker.validate_url()
        assert tracker.url == "udp://tracker.example.com:6969/announce"

    def test_validate_url_http_scheme(self, mock_network):
        """Test that HTTP scheme is accepted."""
        tracker = Tracker(
            url="http://tracker.example.com:80",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        tracker.validate_url()
        assert tracker.url == "http://tracker.example.com:80/announce"

    def test_validate_url_https_scheme(self, mock_network):
        """Test that HTTPS scheme is accepted."""
        tracker = Tracker(
            url="https://tracker.example.com:443",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        tracker.validate_url()
        assert tracker.url == "https://tracker.example.com:443/announce"

    def test_validate_url_invalid_scheme_ws(self, mock_network):
        """Test that WebSocket scheme is rejected."""
        tracker = Tracker(
            url="ws://tracker.example.com:6969",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        with pytest.raises(RuntimeError, match="Tracker URLs have to start with"):
            tracker.validate_url()

    def test_validate_url_invalid_scheme_ftp(self, mock_network):
        """Test that FTP scheme is rejected."""
        tracker = Tracker(
            url="ftp://tracker.example.com:21",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        with pytest.raises(RuntimeError, match="Tracker URLs have to start with"):
            tracker.validate_url()

    def test_validate_url_adds_announce_path(self, mock_network):
        """Test that /announce path is added to URL."""
        tracker = Tracker(
            url="udp://tracker.example.com:6969/something/else",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        tracker.validate_url()
        assert tracker.url == "udp://tracker.example.com:6969/announce"

    def test_validate_url_replaces_existing_path(self, mock_network):
        """Test that existing path is replaced with /announce."""
        tracker = Tracker(
            url="http://tracker.example.com:80/custom/path",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        tracker.validate_url()
        assert "/announce" in tracker.url

    def test_validate_url_invalid_characters_in_netloc(self, mock_network):
        """Test that invalid characters in netloc are rejected."""
        tracker = Tracker(
            url="udp://tracker<script>.example.com:6969",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        with pytest.raises(RuntimeError, match="Invalid announce URL"):
            tracker.validate_url()

    def test_validate_url_with_spaces(self, mock_network):
        """Test that spaces in URL are rejected."""
        tracker = Tracker(
            url="udp://tracker example.com:6969",
            host=None,
            ips=None,
            latency=None,
            last_checked=None,
            interval=None,
            status=None,
            uptime=None,
            countries=[],
            country_codes=[],
            networks=[],
            historic=None,
            added=None,
            last_downtime=None,
            last_uptime=None,
        )
        with pytest.raises(RuntimeError, match="Invalid announce URL"):
            tracker.validate_url()


class TestFromUrl:
    """Tests for Tracker.from_url class method."""

    def test_from_url_creates_tracker(self, mock_network):
        """Test that from_url creates a Tracker with correct initial values."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969)),
        ]

        tracker = Tracker.from_url("udp://tracker.example.com:6969")

        assert tracker.url == "udp://tracker.example.com:6969/announce"
        assert tracker.host == "tracker.example.com"
        assert tracker.ips == ["93.184.216.34"]
        assert isinstance(tracker.historic, deque)
        assert tracker.historic.maxlen == 1000
        assert tracker.added is not None

    def test_from_url_resolves_ipv4(self, mock_network):
        """Test that from_url resolves IPv4 addresses."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("1.2.3.4", 6969)),
        ]

        tracker = Tracker.from_url("udp://tracker.example.com:6969")

        assert tracker.ips is not None
        assert "1.2.3.4" in tracker.ips

    def test_from_url_resolves_ipv6(self, mock_network):
        """Test that from_url resolves IPv6 addresses."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET6, socket.SOCK_DGRAM, 17, "", ("2001:db8::1", 6969, 0, 0)),
        ]

        tracker = Tracker.from_url("udp://tracker.example.com:6969")

        assert tracker.ips is not None
        assert "2001:db8::1" in tracker.ips

    def test_from_url_orders_ipv6_first(self, mock_network):
        """Test that from_url orders IPv6 addresses before IPv4."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("1.2.3.4", 6969)),
            (socket.AF_INET6, socket.SOCK_DGRAM, 17, "", ("2001:db8::1", 6969, 0, 0)),
        ]

        tracker = Tracker.from_url("udp://tracker.example.com:6969")

        assert tracker.ips is not None
        assert tracker.ips[0] == "2001:db8::1"
        assert tracker.ips[1] == "1.2.3.4"

    def test_from_url_invalid_scheme_raises(self, mock_network):
        """Test that from_url raises RuntimeError for invalid scheme."""
        with pytest.raises(RuntimeError, match="Tracker URLs have to start with"):
            Tracker.from_url("ftp://tracker.example.com:21")

    def test_from_url_dns_failure_raises(self, mock_network):
        """Test that from_url raises RuntimeError when DNS resolution fails."""
        mock_network["getaddrinfo"].side_effect = OSError("Name resolution failed")

        with pytest.raises(RuntimeError, match="Can't resolve IP"):
            Tracker.from_url("udp://nonexistent.tracker.com:6969")

    def test_from_url_sets_added_date(self, mock_network):
        """Test that from_url sets the added date."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("1.2.3.4", 6969)),
        ]

        tracker = Tracker.from_url("udp://tracker.example.com:6969")

        assert tracker.added is not None
        # Check format is day-month-year
        parts = tracker.added.split("-")
        assert len(parts) == 3


class TestUpdateUptime:
    """Tests for Tracker.update_uptime method."""

    def test_update_uptime_all_up(self, sample_tracker):
        """Test uptime calculation when all entries are up."""
        sample_tracker.historic = deque([1] * 100, maxlen=1000)
        sample_tracker.update_uptime()
        assert sample_tracker.uptime == 100.0

    def test_update_uptime_all_down(self, sample_tracker):
        """Test uptime calculation when all entries are down."""
        sample_tracker.historic = deque([0] * 100, maxlen=1000)
        sample_tracker.update_uptime()
        assert sample_tracker.uptime == 0.0

    def test_update_uptime_mixed(self, sample_tracker):
        """Test uptime calculation with mixed up/down entries."""
        sample_tracker.historic = deque([1, 0] * 50, maxlen=1000)  # 50% uptime
        sample_tracker.update_uptime()
        assert sample_tracker.uptime == 50.0

    def test_update_uptime_75_percent(self, sample_tracker):
        """Test uptime calculation with 75% uptime."""
        sample_tracker.historic = deque([1, 1, 1, 0] * 25, maxlen=1000)  # 75% uptime
        sample_tracker.update_uptime()
        assert sample_tracker.uptime == 75.0

    def test_update_uptime_single_entry_up(self, sample_tracker):
        """Test uptime calculation with single up entry."""
        sample_tracker.historic = deque([1], maxlen=1000)
        sample_tracker.update_uptime()
        assert sample_tracker.uptime == 100.0

    def test_update_uptime_single_entry_down(self, sample_tracker):
        """Test uptime calculation with single down entry."""
        sample_tracker.historic = deque([0], maxlen=1000)
        sample_tracker.update_uptime()
        assert sample_tracker.uptime == 0.0


class TestIsUpIsDown:
    """Tests for Tracker.is_up and is_down methods."""

    def test_is_up_sets_status(self, sample_tracker):
        """Test that is_up sets status to 1."""
        sample_tracker.status = 0
        sample_tracker.is_up()
        assert sample_tracker.status == 1

    def test_is_up_sets_last_uptime(self, sample_tracker):
        """Test that is_up sets last_uptime to current time."""
        before = int(time())
        sample_tracker.is_up()
        after = int(time())
        assert before <= sample_tracker.last_uptime <= after

    def test_is_up_appends_to_historic(self, sample_tracker):
        """Test that is_up appends 1 to historic."""
        initial_len = len(sample_tracker.historic)
        sample_tracker.is_up()
        assert len(sample_tracker.historic) == initial_len + 1
        assert sample_tracker.historic[-1] == 1

    def test_is_down_sets_status(self, sample_tracker):
        """Test that is_down sets status to 0."""
        sample_tracker.status = 1
        sample_tracker.is_down()
        assert sample_tracker.status == 0

    def test_is_down_sets_last_downtime(self, sample_tracker):
        """Test that is_down sets last_downtime to current time."""
        before = int(time())
        sample_tracker.is_down()
        after = int(time())
        assert before <= sample_tracker.last_downtime <= after

    def test_is_down_appends_to_historic(self, sample_tracker):
        """Test that is_down appends 0 to historic."""
        initial_len = len(sample_tracker.historic)
        sample_tracker.is_down()
        assert len(sample_tracker.historic) == initial_len + 1
        assert sample_tracker.historic[-1] == 0


class TestUpdateIps:
    """Tests for Tracker.update_ips method."""

    def test_update_ips_resolves_ipv4(self, sample_tracker, mock_network):
        """Test that update_ips resolves IPv4 addresses."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("192.168.1.1", 6969)),
        ]

        sample_tracker.update_ips()

        assert sample_tracker.ips == ["192.168.1.1"]

    def test_update_ips_resolves_ipv6(self, sample_tracker, mock_network):
        """Test that update_ips resolves IPv6 addresses."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET6, socket.SOCK_DGRAM, 17, "", ("2001:db8::1", 6969, 0, 0)),
        ]

        sample_tracker.update_ips()

        assert sample_tracker.ips == ["2001:db8::1"]

    def test_update_ips_orders_ipv6_before_ipv4(self, sample_tracker, mock_network):
        """Test that update_ips orders IPv6 addresses before IPv4."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("192.168.1.1", 6969)),
            (socket.AF_INET6, socket.SOCK_DGRAM, 17, "", ("2001:db8::1", 6969, 0, 0)),
        ]

        sample_tracker.update_ips()

        assert sample_tracker.ips == ["2001:db8::1", "192.168.1.1"]

    def test_update_ips_deduplicates(self, sample_tracker, mock_network):
        """Test that update_ips removes duplicate IPs."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("192.168.1.1", 6969)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 6969)),
        ]

        sample_tracker.update_ips()

        assert sample_tracker.ips == ["192.168.1.1"]

    def test_update_ips_dns_failure_raises(self, sample_tracker, mock_network):
        """Test that update_ips raises RuntimeError on DNS failure."""
        mock_network["getaddrinfo"].side_effect = OSError("DNS failure")

        with pytest.raises(RuntimeError, match="Can't resolve IP"):
            sample_tracker.update_ips()

        assert sample_tracker.ips is None

    def test_update_ips_empty_result_raises(self, sample_tracker, mock_network):
        """Test that update_ips raises RuntimeError when no IPs returned."""
        mock_network["getaddrinfo"].return_value = []

        with pytest.raises(RuntimeError, match="Can't resolve IP"):
            sample_tracker.update_ips()


class TestUpdateStatus:
    """Tests for Tracker.update_status method."""

    def test_update_status_udp_success(self, sample_tracker, reset_globals):
        """Test update_status with successful UDP announce."""
        # Set last_uptime to recent time to avoid deletion check
        sample_tracker.last_uptime = int(time())

        mock_getaddrinfo_return = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969)),
        ]

        with (
            patch("newTrackon.tracker.scraper.get_bep_34", return_value=(False, None)),
            patch("newTrackon.tracker.scraper.announce_udp") as mock_announce,
            patch("newTrackon.tracker.scraper.redact_origin", return_value="mocked"),
            patch("newTrackon.tracker.persistence.raw_data", deque()),
            patch("newTrackon.tracker.socket.getaddrinfo", return_value=mock_getaddrinfo_return),
            patch.object(sample_tracker, "update_ipapi_data"),
        ):
            mock_announce.return_value = ({"interval": 1800, "seeds": 100, "leechers": 50, "peers": []}, "93.184.216.34")

            sample_tracker.update_status()

            assert sample_tracker.status == 1
            assert sample_tracker.interval == 1800
            assert sample_tracker.latency is not None

    def test_update_status_http_success(self, sample_tracker, reset_globals):
        """Test update_status with successful HTTP announce."""
        sample_tracker.url = "http://tracker.example.com:80/announce"
        # Set last_uptime to recent time to avoid deletion check
        sample_tracker.last_uptime = int(time())

        mock_getaddrinfo_return = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 80)),
        ]

        with (
            patch("newTrackon.tracker.scraper.get_bep_34", return_value=(False, None)),
            patch("newTrackon.tracker.scraper.announce_http") as mock_announce,
            patch("newTrackon.tracker.scraper.redact_origin", return_value="mocked"),
            patch("newTrackon.tracker.persistence.raw_data", deque()),
            patch("newTrackon.tracker.socket.getaddrinfo", return_value=mock_getaddrinfo_return),
            patch.object(sample_tracker, "update_ipapi_data"),
        ):
            mock_announce.return_value = {"interval": 1800, "complete": 100, "incomplete": 50, "peers": []}

            sample_tracker.update_status()

            assert sample_tracker.status == 1
            assert sample_tracker.interval == 1800

    def test_update_status_announce_failure(self, sample_tracker, mock_network, reset_globals):
        """Test update_status when announce fails."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969)),
        ]

        with (
            patch("newTrackon.tracker.scraper.get_bep_34", return_value=(False, None)),
            patch("newTrackon.tracker.scraper.announce_udp") as mock_announce,
            patch("newTrackon.tracker.persistence.raw_data", deque()),
            patch.object(sample_tracker, "update_ipapi_data"),
        ):
            mock_announce.side_effect = RuntimeError("UDP timeout")

            sample_tracker.update_status()

            assert sample_tracker.status == 0

    def test_update_status_marks_old_tracker_for_deletion(self, sample_tracker, mock_network, reset_globals):
        """Test that tracker unresponsive for too long is marked for deletion."""
        sample_tracker.last_uptime = int(time()) - max_downtime - 1

        with patch("newTrackon.tracker.persistence.raw_data", deque()):
            sample_tracker.update_status()

            assert sample_tracker.to_be_deleted is True
            assert sample_tracker.status == 0

    def test_update_status_dns_failure(self, sample_tracker, mock_network, reset_globals):
        """Test update_status handles DNS resolution failure."""
        mock_network["getaddrinfo"].side_effect = OSError("DNS failure")

        with (
            patch("newTrackon.tracker.scraper.get_bep_34", return_value=(False, None)),
            patch("newTrackon.tracker.persistence.raw_data", deque()),
        ):
            sample_tracker.update_status()

            assert sample_tracker.status == 0

    def test_update_status_sets_interval_when_uptime_zero(self, sample_tracker, mock_network, reset_globals):
        """Test that interval is set to 10800 when uptime is 0."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969)),
        ]

        with (
            patch("newTrackon.tracker.scraper.get_bep_34", return_value=(False, None)),
            patch("newTrackon.tracker.scraper.announce_udp") as mock_announce,
            patch("newTrackon.tracker.persistence.raw_data", deque()),
            patch.object(sample_tracker, "update_ipapi_data"),
        ):
            mock_announce.side_effect = RuntimeError("UDP timeout")
            sample_tracker.historic = deque([0] * 10, maxlen=1000)

            sample_tracker.update_status()

            assert sample_tracker.interval == 10800


class TestUpdateSchemeFromBep34:
    """Tests for Tracker.update_scheme_from_bep_34 method."""

    def test_bep34_denies_connection(self, sample_tracker):
        """Test that BEP34 denial marks tracker for deletion."""
        with patch("newTrackon.tracker.scraper.get_bep_34", return_value=(True, None)):
            with pytest.raises(RuntimeError, match="Host denied connection"):
                sample_tracker.update_scheme_from_bep_34()

            assert sample_tracker.to_be_deleted is True

    def test_bep34_updates_scheme_to_udp(self, sample_tracker):
        """Test that BEP34 can update scheme to UDP."""
        sample_tracker.url = "http://tracker.example.com:80/announce"

        with patch("newTrackon.tracker.scraper.get_bep_34", return_value=(True, [("udp", 6969)])):
            sample_tracker.update_scheme_from_bep_34()

            assert sample_tracker.url.startswith("udp://")
            assert ":6969" in sample_tracker.url

    def test_bep34_updates_port(self, sample_tracker):
        """Test that BEP34 updates port."""
        with patch("newTrackon.tracker.scraper.get_bep_34", return_value=(True, [("tcp", 8080)])):
            sample_tracker.update_scheme_from_bep_34()

            assert ":8080" in sample_tracker.url

    def test_bep34_no_valid_record(self, sample_tracker):
        """Test that no BEP34 record doesn't modify URL."""
        original_url = sample_tracker.url

        with patch("newTrackon.tracker.scraper.get_bep_34", return_value=(False, None)):
            sample_tracker.update_scheme_from_bep_34()

            assert sample_tracker.url == original_url


class TestClearTracker:
    """Tests for Tracker.clear_tracker method."""

    def test_clear_tracker_sets_status_down(self, sample_tracker, reset_globals):
        """Test that clear_tracker marks tracker as down."""
        sample_tracker.status = 1

        with patch("newTrackon.tracker.persistence.raw_data", deque()):
            sample_tracker.clear_tracker("Test reason")

            assert sample_tracker.status == 0

    def test_clear_tracker_clears_geo_data(self, sample_tracker, reset_globals):
        """Test that clear_tracker clears geolocation data."""
        with patch("newTrackon.tracker.persistence.raw_data", deque()):
            sample_tracker.clear_tracker("Test reason")

            assert sample_tracker.countries is None
            assert sample_tracker.networks is None
            assert sample_tracker.country_codes is None

    def test_clear_tracker_clears_latency(self, sample_tracker, reset_globals):
        """Test that clear_tracker clears latency."""
        sample_tracker.latency = 100

        with patch("newTrackon.tracker.persistence.raw_data", deque()):
            sample_tracker.clear_tracker("Test reason")

            assert sample_tracker.latency is None

    def test_clear_tracker_sets_last_checked(self, sample_tracker, reset_globals):
        """Test that clear_tracker updates last_checked."""
        before = int(time())

        with patch("newTrackon.tracker.persistence.raw_data", deque()):
            sample_tracker.clear_tracker("Test reason")

        after = int(time())
        assert before <= sample_tracker.last_checked <= after

    def test_clear_tracker_appends_to_raw_data(self, sample_tracker, reset_globals):
        """Test that clear_tracker appends debug info to raw_data."""
        raw_data = deque()

        with patch("newTrackon.tracker.persistence.raw_data", raw_data):
            sample_tracker.clear_tracker("Test reason")

            assert len(raw_data) == 1
            assert raw_data[0]["status"] == 0
            assert raw_data[0]["info"] == "Test reason"


class TestUpdateIpapiData:
    """Tests for Tracker.update_ipapi_data method."""

    def test_update_ipapi_data_single_ip(self, sample_tracker):
        """Test that update_ipapi_data fetches data for single IP."""
        sample_tracker.ips = ["93.184.216.34"]

        with patch.object(Tracker, "ip_api", return_value="United States\nus\nExample ISP"):
            sample_tracker.update_ipapi_data()

            assert sample_tracker.countries == ["United States"]
            assert sample_tracker.country_codes == ["us"]
            assert sample_tracker.networks == ["Example ISP"]

    def test_update_ipapi_data_multiple_ips(self, sample_tracker):
        """Test that update_ipapi_data fetches data for multiple IPs."""
        sample_tracker.ips = ["93.184.216.34", "2001:db8::1"]

        def mock_ip_api(ip):
            if ip == "93.184.216.34":
                return "United States\nus\nISP1"
            return "Germany\nde\nISP2"

        with patch.object(Tracker, "ip_api", side_effect=mock_ip_api):
            sample_tracker.update_ipapi_data()

            assert sample_tracker.countries == ["United States", "Germany"]
            assert sample_tracker.country_codes == ["us", "de"]
            assert sample_tracker.networks == ["ISP1", "ISP2"]

    def test_update_ipapi_data_no_ips(self, sample_tracker):
        """Test that update_ipapi_data handles None IPs."""
        sample_tracker.ips = None

        sample_tracker.update_ipapi_data()

        assert sample_tracker.countries == []
        assert sample_tracker.country_codes == []
        assert sample_tracker.networks == []

    def test_update_ipapi_data_invalid_response(self, sample_tracker):
        """Test that update_ipapi_data handles invalid API response."""
        sample_tracker.ips = ["93.184.216.34"]

        with patch.object(Tracker, "ip_api", return_value="Error"):
            sample_tracker.update_ipapi_data()

            # Should not add data when response is invalid (not 3 lines)
            assert sample_tracker.countries == []


class TestIpApi:
    """Tests for Tracker.ip_api static method."""

    def test_ip_api_success(self):
        """Test successful IP API query."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"United States\nus\nExample ISP"

        with patch("urllib.request.urlopen", return_value=mock_response), patch("time.sleep"):
            result = Tracker.ip_api("93.184.216.34")

            assert result == "United States\nus\nExample ISP"

    def test_ip_api_network_error(self):
        """Test IP API query with network error."""
        with patch("urllib.request.urlopen", side_effect=OSError("Network error")):
            result = Tracker.ip_api("93.184.216.34")

            assert result == "Error"


class TestMaxDowntimeConstant:
    """Tests for max_downtime constant."""

    def test_max_downtime_value(self):
        """Test that max_downtime is approximately 1.5 years in seconds."""
        # 1.5 years = 1.5 * 365.25 * 24 * 60 * 60 = 47335380 seconds
        # The constant is 47304000, which is approximately 1.5 years
        expected_approx = 1.5 * 365 * 24 * 60 * 60
        assert abs(max_downtime - expected_approx) < 100000  # Within ~1 day tolerance


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_tracker_with_ip_as_hostname_in_url(self, mock_network):
        """Test tracker creation with IP address as hostname."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("192.168.1.1", 6969)),
        ]

        # IP address as hostname should work (getaddrinfo resolves it)
        tracker = Tracker.from_url("udp://192.168.1.1:6969")

        assert tracker.host == "192.168.1.1"
        assert tracker.ips == ["192.168.1.1"]

    def test_empty_historic_deque(self, sample_tracker):
        """Test update_uptime with empty historic deque raises."""
        sample_tracker.historic = deque(maxlen=1000)

        with pytest.raises(ZeroDivisionError):
            sample_tracker.update_uptime()

    def test_tracker_url_without_port(self, mock_network):
        """Test tracker URL without explicit port."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 80)),
        ]

        tracker = Tracker.from_url("http://tracker.example.com")

        assert tracker.url == "http://tracker.example.com/announce"

    def test_update_ips_with_multiple_address_families(self, sample_tracker, mock_network):
        """Test update_ips handles multiple address families correctly."""
        mock_network["getaddrinfo"].return_value = [
            (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("1.2.3.4", 6969)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.2.3.4", 6969)),
            (socket.AF_INET6, socket.SOCK_DGRAM, 17, "", ("2001:db8::1", 6969, 0, 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::1", 6969, 0, 0)),
        ]

        sample_tracker.update_ips()

        # Should deduplicate and order IPv6 first
        assert sample_tracker.ips == ["2001:db8::1", "1.2.3.4"]
