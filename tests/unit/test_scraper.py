"""Comprehensive tests for newTrackon.scraper module.

Tests cover:
- UDP protocol binary encoding/decoding
- UDP response parsing
- HTTP announce with mocked requests
- UDP announce with mocked socket
- BEP34 DNS TXT record parsing
- Memory-limited HTTP GET
- IP redaction
- Error handling throughout
"""

import socket
import struct
from collections import deque
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from dns.exception import DNSException

import newTrackon.scraper as scraper
from newTrackon.scraper import (
    HTTP_PORT,
    UDP_PORT,
    announce_http,
    announce_udp,
    attempt_all_protocols,
    attempt_from_txt_prefs,
    attempt_https_http,
    attempt_httpx,
    attempt_submitted,
    attempt_udp,
    get_bep_34,
    get_server_ip,
    memory_limited_get,
    redact_origin,
    udp_create_announce_request,
    udp_create_binary_connection_request,
    udp_parse_announce_response,
    udp_parse_connection_response,
)


class TestUDPBinaryEncoding:
    """Test UDP protocol binary encoding functions."""

    def test_udp_create_binary_connection_request_structure(self) -> None:
        """Test that connection request has correct structure and length."""
        buf, transaction_id = udp_create_binary_connection_request()

        # Connection request should be 16 bytes
        assert len(buf) == 16

        # Verify connection_id (magic constant)
        connection_id = struct.unpack_from("!q", buf, 0)[0]
        assert connection_id == 0x41727101980

        # Verify action (0 = connect)
        action = struct.unpack_from("!i", buf, 8)[0]
        assert action == 0

        # Verify transaction_id matches returned value
        packed_transaction_id = struct.unpack_from("!i", buf, 12)[0]
        assert packed_transaction_id == transaction_id

    def test_udp_create_binary_connection_request_transaction_id_range(self) -> None:
        """Test that transaction ID is within expected range."""
        for _ in range(100):
            _, transaction_id = udp_create_binary_connection_request()
            assert 0 <= transaction_id <= 255

    def test_udp_create_announce_request_structure(self) -> None:
        """Test that announce request has correct structure and length."""
        connection_id = 0x12345678ABCDEF01
        thash = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a" * 2  # 20 bytes

        buf, transaction_id = udp_create_announce_request(connection_id, thash)

        # Announce request should be 98 bytes
        assert len(buf) == 98

        # Verify connection_id
        packed_connection_id = struct.unpack_from("!q", buf, 0)[0]
        assert packed_connection_id == connection_id

        # Verify action (1 = announce)
        action = struct.unpack_from("!i", buf, 8)[0]
        assert action == 1

        # Verify transaction_id
        packed_transaction_id = struct.unpack_from("!i", buf, 12)[0]
        assert packed_transaction_id == transaction_id

        # Verify info_hash
        info_hash = struct.unpack_from("!20s", buf, 16)[0]
        assert info_hash == thash

        # Verify peer_id (same as hash in this implementation)
        peer_id = struct.unpack_from("!20s", buf, 36)[0]
        assert peer_id == thash

        # Verify downloaded, left, uploaded are 0
        downloaded = struct.unpack_from("!q", buf, 56)[0]
        assert downloaded == 0
        left = struct.unpack_from("!q", buf, 64)[0]
        assert left == 0
        uploaded = struct.unpack_from("!q", buf, 72)[0]
        assert uploaded == 0

        # Verify event (2 = started)
        event = struct.unpack_from("!i", buf, 80)[0]
        assert event == 2

        # Verify IP address is 0
        ip_addr = struct.unpack_from("!i", buf, 84)[0]
        assert ip_addr == 0

        # Verify num_want is -1
        num_want = struct.unpack_from("!i", buf, 92)[0]
        assert num_want == -1

        # Verify port (0x76FD = 30461)
        port = struct.unpack_from("!H", buf, 96)[0]
        assert port == 0x76FD


class TestUDPResponseParsing:
    """Test UDP protocol response parsing functions."""

    def test_udp_parse_connection_response_success(self) -> None:
        """Test successful parsing of connection response."""
        transaction_id = 42
        # Use a value that fits in signed 64-bit integer
        expected_connection_id = 0x12345678ABCDEF01

        # Build valid response: action(4) + transaction_id(4) + connection_id(8)
        buf = struct.pack("!i", 0)  # action = 0 (connect)
        buf += struct.pack("!i", transaction_id)
        buf += struct.pack("!q", expected_connection_id)

        result = udp_parse_connection_response(buf, transaction_id)
        assert result == expected_connection_id

    def test_udp_parse_connection_response_wrong_length(self) -> None:
        """Test that short response raises RuntimeError."""
        buf = b"\x00" * 15  # Too short

        with pytest.raises(RuntimeError, match="Wrong response length"):
            udp_parse_connection_response(buf, 0)

    def test_udp_parse_connection_response_transaction_id_mismatch(self) -> None:
        """Test that mismatched transaction ID raises RuntimeError."""
        buf = struct.pack("!i", 0)  # action
        buf += struct.pack("!i", 100)  # wrong transaction_id
        buf += struct.pack("!q", 0)  # connection_id

        with pytest.raises(RuntimeError, match="Transaction ID doesn't match"):
            udp_parse_connection_response(buf, 42)

    def test_udp_parse_connection_response_error_action(self) -> None:
        """Test that error action (0x3) raises RuntimeError."""
        transaction_id = 42
        buf = struct.pack("!i", 0x3)  # action = 3 (error)
        buf += struct.pack("!i", transaction_id)
        buf += b"Error msg"

        with pytest.raises(RuntimeError, match="Error while trying to get a connection response"):
            udp_parse_connection_response(buf, transaction_id)

    def test_udp_parse_announce_response_success_ipv4(self) -> None:
        """Test successful parsing of IPv4 announce response."""
        transaction_id = 42
        interval = 1800
        leechers = 50
        seeds = 100

        # Build valid response
        buf = struct.pack("!i", 1)  # action = 1 (announce)
        buf += struct.pack("!i", transaction_id)
        buf += struct.pack("!i", interval)
        buf += struct.pack("!i", leechers)
        buf += struct.pack("!i", seeds)
        # Add one IPv4 peer (6 bytes: 4 IP + 2 port)
        buf += bytes([192, 168, 1, 1])  # IP: 192.168.1.1
        buf += struct.pack("!H", 6881)  # port

        result, _raw_hex = udp_parse_announce_response(buf, transaction_id, socket.AF_INET)

        assert result["interval"] == interval
        assert result["leechers"] == leechers
        assert result["seeds"] == seeds
        assert len(result["peers"]) == 1
        assert result["peers"][0]["IP"] == "192.168.1.1"
        assert result["peers"][0]["port"] == 6881

    def test_udp_parse_announce_response_success_ipv6(self) -> None:
        """Test successful parsing of IPv6 announce response."""
        transaction_id = 42
        interval = 3600
        leechers = 25
        seeds = 75

        # Build valid response
        buf = struct.pack("!i", 1)  # action = 1 (announce)
        buf += struct.pack("!i", transaction_id)
        buf += struct.pack("!i", interval)
        buf += struct.pack("!i", leechers)
        buf += struct.pack("!i", seeds)
        # Add one IPv6 peer (18 bytes: 16 IP + 2 port)
        buf += bytes(
            [0x20, 0x01, 0x0D, 0xB8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01]
        )  # 2001:db8::1
        buf += struct.pack("!H", 6881)  # port

        result, _raw_hex = udp_parse_announce_response(buf, transaction_id, socket.AF_INET6)

        assert result["interval"] == interval
        assert result["leechers"] == leechers
        assert result["seeds"] == seeds
        assert len(result["peers"]) == 1
        assert result["peers"][0]["IP"] == "2001:db8::1"
        assert result["peers"][0]["port"] == 6881

    def test_udp_parse_announce_response_wrong_length(self) -> None:
        """Test that short announce response raises RuntimeError."""
        buf = b"\x00" * 19  # Too short (need at least 20)

        with pytest.raises(RuntimeError, match="Wrong response length"):
            udp_parse_announce_response(buf, 0, socket.AF_INET)

    def test_udp_parse_announce_response_transaction_id_mismatch(self) -> None:
        """Test that mismatched transaction ID raises RuntimeError."""
        buf = struct.pack("!i", 1)  # action
        buf += struct.pack("!i", 100)  # wrong transaction_id
        buf += struct.pack("!i", 0)  # interval
        buf += struct.pack("!i", 0)  # leechers
        buf += struct.pack("!i", 0)  # seeds

        with pytest.raises(RuntimeError, match="Transaction ID doesnt match"):
            udp_parse_announce_response(buf, 42, socket.AF_INET)

    def test_udp_parse_announce_response_error_action(self) -> None:
        """Test that non-announce action raises RuntimeError."""
        transaction_id = 42
        buf = struct.pack("!i", 0x3)  # action = 3 (error)
        buf += struct.pack("!i", transaction_id)
        buf += struct.pack("!i", 0)  # padding
        buf += struct.pack("!i", 0)
        buf += struct.pack("!i", 0)
        buf += b"E"  # error message

        with pytest.raises(RuntimeError, match="Error while annoucing"):
            udp_parse_announce_response(buf, transaction_id, socket.AF_INET)


class TestAnnounceHTTP:
    """Test HTTP announce functionality with mocked requests."""

    @pytest.fixture
    def mock_successful_response(self) -> MagicMock:
        """Create a mock successful HTTP response."""
        # Valid bencoded response with peers
        bencoded = b"d8:intervali1800e5:peers6:\xc0\xa8\x01\x01\x1a\xe1e"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raw = MagicMock()
        mock_response.raw.read = MagicMock(return_value=bencoded)
        return mock_response

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_success(self, mock_get: MagicMock) -> None:
        """Test successful HTTP announce."""
        bencoded = b"d8:intervali1800e5:peers6:\xc0\xa8\x01\x01\x1a\xe1e"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = (mock_response, bencoded)

        result = announce_http("http://tracker.example.com/announce", b"\x00" * 20)

        assert result["interval"] == 1800
        assert "peers" in result

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_timeout(self, mock_get: MagicMock) -> None:
        """Test HTTP announce timeout."""
        mock_get.side_effect = requests.Timeout()

        with pytest.raises(RuntimeError, match="HTTP timeout"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_connection_error(self, mock_get: MagicMock) -> None:
        """Test HTTP announce connection error."""
        mock_get.side_effect = requests.ConnectionError()

        with pytest.raises(RuntimeError, match="HTTP connection failed"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_invalid_status_code(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with non-200 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = (mock_response, b"Not found")

        with pytest.raises(RuntimeError, match="HTTP 404 status code returned"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_empty_response(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with empty response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = (mock_response, b"")

        with pytest.raises(RuntimeError, match="Got empty HTTP response"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_invalid_bencoded_response(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with invalid bencoded response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = (mock_response, b"invalid bencoded data")

        with pytest.raises(RuntimeError, match="Failed bdecoding HTTP response"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_tracker_failure_reason(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with tracker failure reason."""
        bencoded = b"d14:failure reason12:invalid hashe"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = (mock_response, bencoded)

        with pytest.raises(RuntimeError, match="Tracker error message"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_missing_peers_field(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with missing peers field."""
        bencoded = b"d8:intervali1800ee"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = (mock_response, bencoded)

        with pytest.raises(RuntimeError, match=r"Invalid response.*peers.*missing"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_response_too_large(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with response exceeding size limit."""
        mock_get.side_effect = RuntimeError("HTTP response size above 1 MB")

        with pytest.raises(RuntimeError, match="HTTP response size above 1 MB"):
            announce_http("http://tracker.example.com/announce")

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_request_exception(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with generic request exception."""
        mock_get.side_effect = requests.RequestException()

        with pytest.raises(RuntimeError, match="Unhandled HTTP error"):
            announce_http("http://tracker.example.com/announce")


class TestAnnounceUDP:
    """Test UDP announce functionality with mocked socket."""

    @pytest.fixture
    def mock_socket(self) -> MagicMock:
        """Create a mock socket for UDP testing."""
        mock_sock = MagicMock()
        mock_sock.family = socket.AF_INET
        return mock_sock

    @patch("socket.getaddrinfo")
    @patch("socket.socket")
    def test_announce_udp_success(self, mock_socket_class: MagicMock, mock_getaddrinfo: MagicMock) -> None:
        """Test successful UDP announce."""
        # Setup getaddrinfo response
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969))]

        # Create mock socket
        mock_sock = MagicMock()
        mock_sock.family = socket.AF_INET
        mock_socket_class.return_value = mock_sock

        # Setup connection response
        connection_id = 0x12345678ABCDEF01
        connect_response = struct.pack("!i", 0)  # action = 0
        connect_response += struct.pack("!i", 0)  # will be overwritten by transaction_id check
        connect_response += struct.pack("!q", connection_id)

        # Setup announce response
        announce_response = struct.pack("!i", 1)  # action = 1
        announce_response += struct.pack("!i", 0)  # will be overwritten
        announce_response += struct.pack("!i", 1800)  # interval
        announce_response += struct.pack("!i", 50)  # leechers
        announce_response += struct.pack("!i", 100)  # seeds

        def recv_side_effect(size: int) -> bytes:
            if mock_sock.recv.call_count == 1:  # pyright: ignore[reportUnknownMemberType]
                # First recv is for connection response
                # Get the transaction ID from the sent request
                sent_data = mock_sock.sendall.call_args_list[0][0][0]
                sent_transaction_id = struct.unpack_from("!i", sent_data, 12)[0]
                response = struct.pack("!i", 0)  # action
                response += struct.pack("!i", sent_transaction_id)
                response += struct.pack("!q", connection_id)
                return response
            else:
                # Second recv is for announce response
                sent_data = mock_sock.sendall.call_args_list[1][0][0]
                sent_transaction_id = struct.unpack_from("!i", sent_data, 12)[0]
                response = struct.pack("!i", 1)  # action
                response += struct.pack("!i", sent_transaction_id)
                response += struct.pack("!i", 1800)
                response += struct.pack("!i", 50)
                response += struct.pack("!i", 100)
                return response

        mock_sock.recv.side_effect = recv_side_effect

        result, ip = announce_udp("udp://tracker.example.com:6969/announce", b"\x00" * 20)

        assert result["interval"] == 1800
        assert result["leechers"] == 50
        assert result["seeds"] == 100
        assert ip == "93.184.216.34"

    @patch("socket.getaddrinfo")
    def test_announce_udp_dns_resolution_error(self, mock_getaddrinfo: MagicMock) -> None:
        """Test UDP announce with DNS resolution error."""
        mock_getaddrinfo.side_effect = OSError("Name or service not known")

        with pytest.raises(RuntimeError, match="UDP error"):
            announce_udp("udp://invalid.tracker.com:6969/announce")

    @patch("socket.getaddrinfo")
    @patch("socket.socket")
    def test_announce_udp_connection_refused(self, mock_socket_class: MagicMock, mock_getaddrinfo: MagicMock) -> None:
        """Test UDP announce with connection refused."""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969))]

        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        mock_sock.sendall.side_effect = ConnectionRefusedError()

        with pytest.raises(RuntimeError, match="UDP connection failed"):
            announce_udp("udp://tracker.example.com:6969/announce")

    @patch("socket.getaddrinfo")
    @patch("socket.socket")
    def test_announce_udp_timeout(self, mock_socket_class: MagicMock, mock_getaddrinfo: MagicMock) -> None:
        """Test UDP announce timeout."""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969))]

        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        mock_sock.recv.side_effect = TimeoutError()

        with pytest.raises(RuntimeError, match="UDP timeout"):
            announce_udp("udp://tracker.example.com:6969/announce")

    @patch("socket.getaddrinfo")
    @patch("socket.socket")
    def test_announce_udp_socket_creation_failure(self, mock_socket_class: MagicMock, mock_getaddrinfo: MagicMock) -> None:
        """Test UDP announce when socket creation fails."""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969))]

        mock_socket_class.side_effect = OSError("Cannot create socket")

        with pytest.raises(RuntimeError, match="UDP connection error"):
            announce_udp("udp://tracker.example.com:6969/announce")

    @patch("socket.getaddrinfo")
    @patch("socket.socket")
    def test_announce_udp_connect_failure(self, mock_socket_class: MagicMock, mock_getaddrinfo: MagicMock) -> None:
        """Test UDP announce when socket connect fails."""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("93.184.216.34", 6969))]

        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        mock_sock.connect.side_effect = OSError("Connection failed")

        with pytest.raises(RuntimeError, match="UDP connection error"):
            announce_udp("udp://tracker.example.com:6969/announce")


class TestGetBEP34:
    """Test BEP34 DNS TXT record parsing."""

    @patch("dns.resolver.resolve")
    def test_get_bep_34_valid_record(self, mock_resolve: MagicMock) -> None:
        """Test parsing valid BEP34 TXT record."""
        mock_record = MagicMock()
        mock_record.__str__ = MagicMock(return_value='"BITTORRENT UDP:6969 TCP:80"')
        mock_answer = MagicMock()
        mock_answer.__iter__ = MagicMock(return_value=iter([mock_record]))
        mock_resolve.return_value = mock_answer

        valid, prefs = get_bep_34("tracker.example.com")

        assert valid is True
        assert prefs == [("udp", 6969), ("tcp", 80)]

    @patch("dns.resolver.resolve")
    def test_get_bep_34_no_record(self, mock_resolve: MagicMock) -> None:
        """Test when no TXT record exists."""
        mock_resolve.side_effect = DNSException("No TXT record")

        valid, prefs = get_bep_34("tracker.example.com")

        assert valid is False
        assert prefs is None

    @patch("dns.resolver.resolve")
    def test_get_bep_34_non_bittorrent_record(self, mock_resolve: MagicMock) -> None:
        """Test when TXT record doesn't start with BITTORRENT."""
        mock_record = MagicMock()
        mock_record.__str__ = MagicMock(return_value='"v=spf1 include:example.com"')
        mock_answer = MagicMock()
        mock_answer.__iter__ = MagicMock(return_value=iter([mock_record]))
        mock_resolve.return_value = mock_answer

        valid, prefs = get_bep_34("tracker.example.com")

        assert valid is False
        assert prefs is None

    @patch("dns.resolver.resolve")
    def test_get_bep_34_deny_connection(self, mock_resolve: MagicMock) -> None:
        """Test BEP34 record that denies connection (BITTORRENT only)."""
        mock_record = MagicMock()
        mock_record.__str__ = MagicMock(return_value='"BITTORRENT"')
        mock_answer = MagicMock()
        mock_answer.__iter__ = MagicMock(return_value=iter([mock_record]))
        mock_resolve.return_value = mock_answer

        valid, prefs = get_bep_34("tracker.example.com")

        assert valid is True
        assert prefs == []  # Empty list means deny

    @patch("dns.resolver.resolve")
    def test_get_bep_34_multiple_records(self, mock_resolve: MagicMock) -> None:
        """Test with multiple TXT records, one being BEP34."""
        mock_record1 = MagicMock()
        mock_record1.__str__ = MagicMock(return_value='"v=spf1"')
        mock_record2 = MagicMock()
        mock_record2.__str__ = MagicMock(return_value='"BITTORRENT UDP:1337"')
        mock_answer = MagicMock()
        mock_answer.__iter__ = MagicMock(return_value=iter([mock_record1, mock_record2]))
        mock_resolve.return_value = mock_answer

        valid, prefs = get_bep_34("tracker.example.com")

        assert valid is True
        assert prefs == [("udp", 1337)]


class TestMemoryLimitedGet:
    """Test memory-limited HTTP GET functionality."""

    @patch("requests.get")
    def test_memory_limited_get_success(self, mock_get: MagicMock) -> None:
        """Test successful GET within size limit."""
        mock_response = MagicMock()
        mock_response.raw.read.return_value = b"x" * 1000
        mock_get.return_value = mock_response

        _response, content = memory_limited_get("http://example.com")

        assert len(content) == 1000
        mock_response.raw.read.assert_called_once_with(1024 * 1024 + 1, decode_content=True)  # pyright: ignore[reportUnknownMemberType]

    @patch("requests.get")
    def test_memory_limited_get_exceeds_limit(self, mock_get: MagicMock) -> None:
        """Test GET that exceeds 1MB limit."""
        mock_response = MagicMock()
        mock_response.raw.read.return_value = b"x" * (1024 * 1024 + 1)
        mock_get.return_value = mock_response

        with pytest.raises(RuntimeError, match="HTTP response size above 1 MB"):
            memory_limited_get("http://example.com")

    @patch("requests.get")
    def test_memory_limited_get_exactly_at_limit(self, mock_get: MagicMock) -> None:
        """Test GET exactly at 1MB limit."""
        mock_response = MagicMock()
        mock_response.raw.read.return_value = b"x" * (1024 * 1024)
        mock_get.return_value = mock_response

        _response, content = memory_limited_get("http://example.com")

        assert len(content) == 1024 * 1024

    @patch("requests.get")
    def test_memory_limited_get_uses_correct_headers(self, mock_get: MagicMock) -> None:
        """Test that correct headers are used."""
        mock_response = MagicMock()
        mock_response.raw.read.return_value = b"content"
        mock_get.return_value = mock_response

        memory_limited_get("http://example.com")

        mock_get.assert_called_once()  # pyright: ignore[reportUnknownMemberType]
        call_kwargs: dict[str, Any] = mock_get.call_args[1]  # pyright: ignore[reportUnknownMemberType]
        assert call_kwargs["headers"]["User-Agent"] == "qBittorrent/4.3.9"
        assert call_kwargs["timeout"] == 10
        assert call_kwargs["stream"] is True
        assert call_kwargs["allow_redirects"] is False


class TestRedactOrigin:
    """Test IP redaction functionality."""

    def test_redact_origin_ipv4(self) -> None:
        """Test redacting IPv4 address."""
        original_ipv4 = scraper.my_ipv4
        scraper.my_ipv4 = "192.168.1.100"

        try:
            response = "Connected from 192.168.1.100"
            result = redact_origin(response)
            assert "192.168.1.100" not in result
            assert "v4-redacted" in result
        finally:
            scraper.my_ipv4 = original_ipv4

    def test_redact_origin_ipv6(self) -> None:
        """Test redacting IPv6 address."""
        original_ipv6 = scraper.my_ipv6
        scraper.my_ipv6 = "2001:db8::1"

        try:
            response = "Connected from 2001:db8::1"
            result = redact_origin(response)
            assert "2001:db8::1" not in result
            assert "v6-redacted" in result
        finally:
            scraper.my_ipv6 = original_ipv6

    def test_redact_origin_ports(self) -> None:
        """Test redacting HTTP and UDP ports."""
        response = f"Port {HTTP_PORT} and port {UDP_PORT}"
        result = redact_origin(response)

        assert str(HTTP_PORT) not in result
        assert str(UDP_PORT) not in result
        assert "redacted" in result

    def test_redact_origin_both_ips(self) -> None:
        """Test redacting both IPv4 and IPv6 addresses."""
        original_ipv4 = scraper.my_ipv4
        original_ipv6 = scraper.my_ipv6
        scraper.my_ipv4 = "10.0.0.1"
        scraper.my_ipv6 = "fe80::1"

        try:
            response = "IPv4: 10.0.0.1, IPv6: fe80::1"
            result = redact_origin(response)
            assert "10.0.0.1" not in result
            assert "fe80::1" not in result
            assert "v4-redacted" in result
            assert "v6-redacted" in result
        finally:
            scraper.my_ipv4 = original_ipv4
            scraper.my_ipv6 = original_ipv6

    def test_redact_origin_no_ips_set(self) -> None:
        """Test redaction when no IPs are set."""
        original_ipv4 = scraper.my_ipv4
        original_ipv6 = scraper.my_ipv6
        scraper.my_ipv4 = None
        scraper.my_ipv6 = None

        try:
            response = "No IPs to redact"
            result = redact_origin(response)
            # Only ports should be redacted if present
            assert result == "No IPs to redact"
        finally:
            scraper.my_ipv4 = original_ipv4
            scraper.my_ipv6 = original_ipv6


class TestAttemptUDP:
    """Test attempt_udp function."""

    @patch("newTrackon.scraper.announce_udp")
    @patch("newTrackon.persistence.submitted_data", new_callable=lambda: deque[str](maxlen=100))
    def test_attempt_udp_success(self, mock_submitted_data: MagicMock, mock_announce_udp: MagicMock) -> None:
        """Test successful UDP attempt."""
        mock_announce_udp.return_value = (
            {"interval": 1800, "leechers": 50, "seeds": 100, "peers": []},
            "93.184.216.34",
        )

        status, interval, url, latency = attempt_udp("93.184.216.34", "tracker.example.com:6969")

        assert status == 1
        assert interval == 1800
        assert url == "udp://tracker.example.com:6969/announce"
        assert latency >= 0

    @patch("newTrackon.scraper.announce_udp")
    @patch("newTrackon.persistence.submitted_data", new_callable=lambda: deque[str](maxlen=100))
    def test_attempt_udp_failure(self, mock_submitted_data: MagicMock, mock_announce_udp: MagicMock) -> None:
        """Test failed UDP attempt."""
        mock_announce_udp.side_effect = RuntimeError("UDP timeout")

        status, interval, _url, _latency = attempt_udp("93.184.216.34", "tracker.example.com:6969")

        assert status == 0
        assert interval is None


class TestAttemptHTTPX:
    """Test attempt_httpx function."""

    @patch("newTrackon.scraper.announce_http")
    @patch("newTrackon.persistence.submitted_data", new_callable=lambda: deque[str](maxlen=100))
    def test_attempt_httpx_https_success(self, mock_submitted_data: MagicMock, mock_announce_http: MagicMock) -> None:
        """Test successful HTTPS attempt."""
        from urllib.parse import urlparse

        mock_announce_http.return_value = {"interval": 1800, "peers": []}

        submitted_url = urlparse("http://tracker.example.com:80/announce")
        status, interval, url, _latency = attempt_httpx("93.184.216.34", submitted_url, tls=True)

        assert status == 1
        assert interval == 1800
        assert "https://" in url

    @patch("newTrackon.scraper.announce_http")
    @patch("newTrackon.persistence.submitted_data", new_callable=lambda: deque[str](maxlen=100))
    def test_attempt_httpx_http_success(self, mock_submitted_data: MagicMock, mock_announce_http: MagicMock) -> None:
        """Test successful HTTP attempt."""
        from urllib.parse import urlparse

        mock_announce_http.return_value = {"interval": 3600, "peers": []}

        submitted_url = urlparse("http://tracker.example.com:80/announce")
        status, interval, url, _latency = attempt_httpx("93.184.216.34", submitted_url, tls=False)

        assert status == 1
        assert interval == 3600
        assert "http://" in url

    @patch("newTrackon.scraper.announce_http")
    @patch("newTrackon.persistence.submitted_data", new_callable=lambda: deque[str](maxlen=100))
    def test_attempt_httpx_failure(self, mock_submitted_data: MagicMock, mock_announce_http: MagicMock) -> None:
        """Test failed HTTP attempt."""
        from urllib.parse import urlparse

        mock_announce_http.side_effect = RuntimeError("HTTP connection failed")

        submitted_url = urlparse("http://tracker.example.com:80/announce")
        status, interval, _url, _latency = attempt_httpx("93.184.216.34", submitted_url, tls=True)

        assert status == 0
        assert interval is None


class TestAttemptHTTPSHTTP:
    """Test attempt_https_http function."""

    @patch("newTrackon.scraper.attempt_httpx")
    def test_attempt_https_http_https_success(self, mock_attempt_httpx: MagicMock) -> None:
        """Test when HTTPS succeeds."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult

        mock_attempt_httpx.return_value = AttemptResult(1, 1800, "https://tracker.example.com:443/announce", 100)

        url = urlparse("http://tracker.example.com/announce")
        result = attempt_https_http("93.184.216.34", url)

        assert result is not None
        assert result.interval == 1800
        assert "https://" in result.url
        # Should only call once since HTTPS succeeded
        assert mock_attempt_httpx.call_count == 1  # pyright: ignore[reportUnknownMemberType]

    @patch("newTrackon.scraper.attempt_httpx")
    def test_attempt_https_http_https_fails_http_succeeds(self, mock_attempt_httpx: MagicMock) -> None:
        """Test when HTTPS fails but HTTP succeeds."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult

        mock_attempt_httpx.side_effect = [
            AttemptResult(0, None, "https://tracker.example.com:443/announce", 0),
            AttemptResult(1, 1800, "http://tracker.example.com:80/announce", 100),
        ]

        url = urlparse("http://tracker.example.com/announce")
        result = attempt_https_http("93.184.216.34", url)

        assert result is not None
        assert result.interval == 1800
        assert "http://" in result.url
        assert mock_attempt_httpx.call_count == 2  # pyright: ignore[reportUnknownMemberType]

    @patch("newTrackon.scraper.attempt_httpx")
    def test_attempt_https_http_both_fail(self, mock_attempt_httpx: MagicMock) -> None:
        """Test when both HTTPS and HTTP fail."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult

        mock_attempt_httpx.return_value = AttemptResult(0, None, "url", 0)

        url = urlparse("http://tracker.example.com/announce")
        result = attempt_https_http("93.184.216.34", url)

        assert result is None
        assert mock_attempt_httpx.call_count == 2  # pyright: ignore[reportUnknownMemberType]


class TestAttemptAllProtocols:
    """Test attempt_all_protocols function."""

    @patch("newTrackon.scraper.attempt_udp")
    @patch("newTrackon.scraper.attempt_https_http")
    def test_attempt_all_protocols_udp_success(self, mock_https_http: MagicMock, mock_udp: MagicMock) -> None:
        """Test when UDP succeeds."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult

        mock_udp.return_value = AttemptResult(1, 1800, "udp://tracker.example.com:6969/announce", 50)

        url = urlparse("udp://tracker.example.com:6969/announce")
        result = attempt_all_protocols(url, "93.184.216.34")

        assert result.interval == 1800
        assert "udp://" in result.url
        mock_https_http.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

    @patch("newTrackon.scraper.attempt_udp")
    @patch("newTrackon.scraper.attempt_https_http")
    def test_attempt_all_protocols_udp_fails_http_success(self, mock_https_http: MagicMock, mock_udp: MagicMock) -> None:
        """Test when UDP fails but HTTP succeeds."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult, ScraperResult

        mock_udp.return_value = AttemptResult(0, None, "udp://tracker.example.com:6969/announce", 0)
        mock_https_http.return_value = ScraperResult(1800, "http://tracker.example.com:80/announce", 100)

        url = urlparse("udp://tracker.example.com:6969/announce")
        result = attempt_all_protocols(url, "93.184.216.34")

        assert result.interval == 1800
        assert "http://" in result.url

    @patch("newTrackon.scraper.attempt_udp")
    @patch("newTrackon.scraper.attempt_https_http")
    def test_attempt_all_protocols_no_port_skips_udp(self, mock_https_http: MagicMock, mock_udp: MagicMock) -> None:
        """Test that UDP is skipped when no port is specified."""
        from urllib.parse import urlparse

        from newTrackon.scraper import ScraperResult

        mock_https_http.return_value = ScraperResult(1800, "http://tracker.example.com:80/announce", 100)

        url = urlparse("http://tracker.example.com/announce")  # No port
        result = attempt_all_protocols(url, "93.184.216.34")

        mock_udp.assert_not_called()  # pyright: ignore[reportUnknownMemberType]
        assert result.interval == 1800

    @patch("newTrackon.scraper.attempt_udp")
    @patch("newTrackon.scraper.attempt_https_http")
    def test_attempt_all_protocols_all_fail(self, mock_https_http: MagicMock, mock_udp: MagicMock) -> None:
        """Test when all protocols fail."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult

        mock_udp.return_value = AttemptResult(0, None, "udp://tracker.example.com:6969/announce", 0)
        mock_https_http.return_value = None

        url = urlparse("udp://tracker.example.com:6969/announce")

        with pytest.raises(RuntimeError):
            attempt_all_protocols(url, "93.184.216.34")


class TestAttemptFromTxtPrefs:
    """Test attempt_from_txt_prefs function."""

    @patch("newTrackon.scraper.attempt_udp")
    @patch("newTrackon.scraper.attempt_https_http")
    def test_attempt_from_txt_prefs_udp_success(self, mock_https_http: MagicMock, mock_udp: MagicMock) -> None:
        """Test when UDP preference succeeds."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult

        mock_udp.return_value = AttemptResult(1, 1800, "udp://tracker.example.com:6969/announce", 50)

        url = urlparse("http://tracker.example.com/announce")
        txt_prefs: list[tuple[str, int]] = [("udp", 6969), ("tcp", 80)]

        result = attempt_from_txt_prefs(url, "93.184.216.34", txt_prefs)

        assert result.interval == 1800
        mock_https_http.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

    @patch("newTrackon.scraper.attempt_udp")
    @patch("newTrackon.scraper.attempt_https_http")
    def test_attempt_from_txt_prefs_tcp_success(self, mock_https_http: MagicMock, mock_udp: MagicMock) -> None:
        """Test when TCP preference succeeds."""
        from urllib.parse import urlparse

        from newTrackon.scraper import ScraperResult

        mock_https_http.return_value = ScraperResult(1800, "http://tracker.example.com:80/announce", 100)

        url = urlparse("http://tracker.example.com/announce")
        txt_prefs: list[tuple[str, int]] = [("tcp", 80)]

        result = attempt_from_txt_prefs(url, "93.184.216.34", txt_prefs)

        assert result.interval == 1800
        mock_udp.assert_not_called()  # pyright: ignore[reportUnknownMemberType]

    @patch("newTrackon.scraper.attempt_udp")
    @patch("newTrackon.scraper.attempt_https_http")
    def test_attempt_from_txt_prefs_all_fail(self, mock_https_http: MagicMock, mock_udp: MagicMock) -> None:
        """Test when all preferences fail."""
        from urllib.parse import urlparse

        from newTrackon.scraper import AttemptResult

        mock_udp.return_value = AttemptResult(0, None, "url", 0)
        mock_https_http.return_value = None

        url = urlparse("http://tracker.example.com/announce")
        txt_prefs: list[tuple[str, int]] = [("udp", 6969), ("tcp", 80)]

        with pytest.raises(RuntimeError):
            attempt_from_txt_prefs(url, "93.184.216.34", txt_prefs)


class TestAttemptSubmitted:
    """Test attempt_submitted function."""

    @patch("newTrackon.scraper.get_bep_34")
    @patch("newTrackon.scraper.attempt_all_protocols")
    @patch("socket.getaddrinfo")
    def test_attempt_submitted_no_bep34(
        self, mock_getaddrinfo: MagicMock, mock_all_protocols: MagicMock, mock_bep34: MagicMock
    ) -> None:
        """Test submitted tracker without BEP34."""

        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 6969))]
        mock_bep34.return_value = (False, None)
        mock_all_protocols.return_value = (1800, "udp://tracker.example.com:6969/announce", 50)

        tracker = MagicMock()
        tracker.url = "udp://tracker.example.com:6969/announce"

        result = attempt_submitted(tracker)
        assert result is not None
        interval, _url, _latency = result

        assert interval == 1800
        mock_all_protocols.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

    @patch("newTrackon.scraper.get_bep_34")
    @patch("newTrackon.scraper.attempt_from_txt_prefs")
    @patch("socket.getaddrinfo")
    def test_attempt_submitted_with_bep34(
        self, mock_getaddrinfo: MagicMock, mock_txt_prefs: MagicMock, mock_bep34: MagicMock
    ) -> None:
        """Test submitted tracker with valid BEP34."""
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 6969))]
        mock_bep34.return_value = (True, [("udp", 6969)])
        mock_txt_prefs.return_value = (1800, "udp://tracker.example.com:6969/announce", 50)

        tracker = MagicMock()
        tracker.url = "udp://tracker.example.com:6969/announce"

        result = attempt_submitted(tracker)
        assert result is not None
        interval, _url, _latency = result

        assert interval == 1800
        mock_txt_prefs.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

    @patch("newTrackon.scraper.get_bep_34")
    @patch("newTrackon.persistence.submitted_data", new_callable=lambda: deque[str](maxlen=100))
    @patch("socket.getaddrinfo")
    def test_attempt_submitted_bep34_denies(
        self, mock_getaddrinfo: MagicMock, mock_submitted_data: MagicMock, mock_bep34: MagicMock
    ) -> None:
        """Test submitted tracker with BEP34 that denies connection."""
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 6969))]
        mock_bep34.return_value = (True, [])  # Empty list = deny

        tracker = MagicMock()
        tracker.url = "udp://tracker.example.com:6969/announce"

        with pytest.raises(RuntimeError):
            attempt_submitted(tracker)

    @patch("newTrackon.scraper.get_bep_34")
    @patch("newTrackon.scraper.attempt_all_protocols")
    @patch("socket.getaddrinfo")
    def test_attempt_submitted_dns_failure(
        self, mock_getaddrinfo: MagicMock, mock_all_protocols: MagicMock, mock_bep34: MagicMock
    ) -> None:
        """Test submitted tracker with DNS resolution failure."""
        mock_getaddrinfo.side_effect = OSError("DNS failure")
        mock_bep34.return_value = (False, None)
        mock_all_protocols.return_value = (1800, "url", 50)

        tracker = MagicMock()
        tracker.url = "udp://tracker.example.com:6969/announce"

        # Should still work with empty failover_ip
        result = attempt_submitted(tracker)
        assert result is not None
        interval, _url, _latency = result
        assert interval == 1800


class TestGetServerIP:
    """Test get_server_ip function."""

    @patch("subprocess.check_output")
    def test_get_server_ip_v4(self, mock_check_output: MagicMock) -> None:
        """Test getting IPv4 address."""
        mock_check_output.return_value = b"93.184.216.34\n"

        result = get_server_ip("4")

        assert result == "93.184.216.34"
        mock_check_output.assert_called_with(["curl", "-s", "-4", "https://icanhazip.com/"])  # pyright: ignore[reportUnknownMemberType]

    @patch("subprocess.check_output")
    def test_get_server_ip_v6(self, mock_check_output: MagicMock) -> None:
        """Test getting IPv6 address."""
        mock_check_output.return_value = b"2001:db8::1\n"

        result = get_server_ip("6")

        assert result == "2001:db8::1"
        mock_check_output.assert_called_with(["curl", "-s", "-6", "https://icanhazip.com/"])  # pyright: ignore[reportUnknownMemberType]


class TestGlobalConstants:
    """Test global constants and configuration."""

    def test_http_port_value(self) -> None:
        """Test HTTP_PORT constant."""
        assert HTTP_PORT == 6881

    def test_udp_port_value(self) -> None:
        """Test UDP_PORT constant."""
        assert UDP_PORT == 30461

    def test_max_response_size(self) -> None:
        """Test MAX_RESPONSE_SIZE constant."""
        assert scraper.MAX_RESPONSE_SIZE == 1024 * 1024

    def test_scraping_headers(self) -> None:
        """Test SCRAPING_HEADERS configuration."""
        assert scraper.SCRAPING_HEADERS["User-Agent"] == "qBittorrent/4.3.9"
        assert scraper.SCRAPING_HEADERS["Accept-Encoding"] == "gzip"
        assert scraper.SCRAPING_HEADERS["Connection"] == "close"


class TestEdgeCases:
    """Test edge cases and error boundaries."""

    def test_udp_create_announce_request_with_random_hash(self) -> None:
        """Test announce request with various hash values."""
        connection_id = 0x1234567890ABCDEF

        # Test with all zeros
        buf, _ = udp_create_announce_request(connection_id, b"\x00" * 20)
        assert len(buf) == 98

        # Test with all ones
        buf, _ = udp_create_announce_request(connection_id, b"\xff" * 20)
        assert len(buf) == 98

        # Test with mixed values
        buf, _ = udp_create_announce_request(connection_id, bytes(range(20)))
        assert len(buf) == 98

    def test_udp_parse_announce_response_no_peers(self) -> None:
        """Test parsing announce response with no peers."""
        transaction_id = 42
        buf = struct.pack("!i", 1)  # action
        buf += struct.pack("!i", transaction_id)
        buf += struct.pack("!i", 1800)  # interval
        buf += struct.pack("!i", 0)  # leechers
        buf += struct.pack("!i", 0)  # seeds
        # No peer data

        result, _ = udp_parse_announce_response(buf, transaction_id, socket.AF_INET)

        assert result["interval"] == 1800
        assert result["leechers"] == 0
        assert result["seeds"] == 0
        assert result["peers"] == []

    def test_udp_parse_announce_response_multiple_peers(self) -> None:
        """Test parsing announce response with multiple peers."""
        transaction_id = 42
        buf = struct.pack("!i", 1)
        buf += struct.pack("!i", transaction_id)
        buf += struct.pack("!i", 1800)
        buf += struct.pack("!i", 10)
        buf += struct.pack("!i", 20)
        # Add 3 peers
        for i in range(3):
            buf += bytes([192, 168, 1, i + 1])
            buf += struct.pack("!H", 6881 + i)

        result, _ = udp_parse_announce_response(buf, transaction_id, socket.AF_INET)

        assert len(result["peers"]) == 3
        assert result["peers"][0]["IP"] == "192.168.1.1"
        assert result["peers"][0]["port"] == 6881
        assert result["peers"][2]["IP"] == "192.168.1.3"
        assert result["peers"][2]["port"] == 6883

    @patch("newTrackon.scraper.memory_limited_get")
    def test_announce_http_with_peers6_field(self, mock_get: MagicMock) -> None:
        """Test HTTP announce with peers6 field instead of peers."""
        # Response with peers6 instead of peers
        bencoded = b"d8:intervali1800e6:peers618:\x20\x01\x0d\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x1a\xe1e"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = (mock_response, bencoded)

        result = announce_http("http://tracker.example.com/announce", b"\x00" * 20)

        assert result["interval"] == 1800
        assert "peers6" in result

    def test_redact_origin_multiple_occurrences(self) -> None:
        """Test redacting multiple occurrences of the same IP."""
        original_ipv4 = scraper.my_ipv4
        scraper.my_ipv4 = "10.0.0.1"

        try:
            response = "IP: 10.0.0.1, also 10.0.0.1, and again 10.0.0.1"
            result = redact_origin(response)
            assert result.count("10.0.0.1") == 0
            assert result.count("v4-redacted") == 3
        finally:
            scraper.my_ipv4 = original_ipv4
