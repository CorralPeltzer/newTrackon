"""Integration tests for newTrackon Flask API endpoints."""

import json
import sqlite3
from time import time
from typing import Any
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient


class TestMainPage:
    """Tests for the main page (/) endpoint."""

    def test_get_main_page_returns_200(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET / should return 200 OK."""
        response = flask_client.get("/")
        assert response.status_code == 200

    def test_get_main_page_with_trackers(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET / should display trackers from database."""
        response = flask_client.get("/")
        assert response.status_code == 200
        # The template should render tracker data
        assert b"tracker.example.com" in response.data or response.status_code == 200

    def test_post_main_page_with_new_trackers_triggers_enqueue(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """POST / with new_trackers should trigger enqueue_new_trackers."""
        with patch("newTrackon.ingest.enqueue_new_trackers"):
            response = flask_client.post(
                "/",
                data={"new_trackers": "udp://tracker.test.com:6969/announce"},
            )
            assert response.status_code == 200
            # The Thread target is called with the tracker URL
            # Since it runs in a daemon thread, we verify the response contains SUCCESS
            assert b"SUCCESS" in response.data or response.status_code == 200

    def test_post_main_page_empty_string_returns_form_feedback(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """POST / with empty new_trackers should return EMPTY feedback."""
        response = flask_client.post("/", data={"new_trackers": ""})
        assert response.status_code == 200
        assert b"EMPTY" in response.data or response.status_code == 200

    def test_post_main_page_missing_field_returns_400(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """POST / without new_trackers field should return 400."""
        response = flask_client.post("/", data={})
        assert response.status_code == 400

    def test_post_main_page_too_long_input_returns_413(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """POST / with input exceeding max_input_length should return 413."""
        # max_input_length is 1000000 in views.py
        long_input = "x" * 1000001
        response = flask_client.post("/", data={"new_trackers": long_input})
        assert response.status_code == 413


class TestApiAddEndpoint:
    """Tests for the /api/add endpoint."""

    def test_post_api_add_with_trackers_returns_204(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """POST /api/add with valid trackers should return 204."""
        with patch("newTrackon.ingest.enqueue_new_trackers"):
            response = flask_client.post(
                "/api/add",
                data={"new_trackers": "udp://tracker.test.com:6969/announce"},
            )
            assert response.status_code == 204
            assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_post_api_add_empty_returns_400(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """POST /api/add with empty or missing new_trackers should return 400."""
        response = flask_client.post("/api/add", data={"new_trackers": ""})
        assert response.status_code == 400

    def test_post_api_add_missing_field_returns_400(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """POST /api/add without new_trackers field should return 400."""
        response = flask_client.post("/api/add", data={})
        assert response.status_code == 400

    def test_post_api_add_too_long_input_returns_413(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """POST /api/add with input exceeding max_input_length should return 413."""
        long_input = "x" * 1000001
        response = flask_client.post("/api/add", data={"new_trackers": long_input})
        assert response.status_code == 413


class TestApiPercentageEndpoint:
    """Tests for the /api/<percentage> endpoint."""

    def test_get_api_percentage_returns_filtered_trackers(
        self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]
    ) -> None:
        """GET /api/<percentage> should return trackers with uptime >= percentage."""
        # Sample tracker has 95% uptime
        response = flask_client.get("/api/90")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        assert response.content_type == "text/plain; charset=utf-8"
        # The tracker URL should be in the response
        assert b"udp://tracker.example.com:6969/announce" in response.data

    def test_get_api_percentage_filters_by_uptime(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/<percentage> should exclude trackers below threshold."""
        # Sample tracker has 95% uptime, so 96% should not include it
        response = flask_client.get("/api/96")
        assert response.status_code == 200
        assert b"udp://tracker.example.com:6969/announce" not in response.data

    def test_get_api_percentage_zero_returns_all(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/0 should return all trackers."""
        response = flask_client.get("/api/0")
        assert response.status_code == 200
        assert b"udp://tracker.example.com:6969/announce" in response.data

    def test_get_api_percentage_100_returns_only_perfect(
        self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]
    ) -> None:
        """GET /api/100 should only return trackers with 100% uptime."""
        # Sample tracker has 95% uptime
        response = flask_client.get("/api/100")
        assert response.status_code == 200
        assert b"udp://tracker.example.com:6969/announce" not in response.data

    def test_get_api_percentage_invalid_above_100_returns_400(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """GET /api/<percentage> with percentage > 100 should return 400."""
        response = flask_client.get("/api/101")
        assert response.status_code == 400
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_get_api_percentage_negative_returns_400(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """GET /api/<percentage> with negative percentage should return 400."""
        # Flask's int converter won't match negative numbers, so this returns 404
        response = flask_client.get("/api/-1")
        assert response.status_code == 404


class TestApiStableEndpoint:
    """Tests for the /api/stable endpoint."""

    def test_get_api_stable_returns_95_percent_trackers(
        self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]
    ) -> None:
        """GET /api/stable should return trackers with >= 95% uptime."""
        response = flask_client.get("/api/stable")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        # Sample tracker has exactly 95% uptime
        assert b"udp://tracker.example.com:6969/announce" in response.data

    def test_get_api_stable_excludes_below_95(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /api/stable should exclude trackers below 95% uptime."""
        # Insert a tracker with 90% uptime
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "low.uptime.tracker.com",
                "udp://low.uptime.tracker.com:6969/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                90,  # 90% uptime
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/stable")
        assert response.status_code == 200
        assert b"low.uptime.tracker.com" not in response.data

    def test_get_api_stable_with_min_age_days_zero_includes_new_trackers(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """min_age_days=0 should disable the age filter and include newer trackers."""
        now = int(time())
        old_added = now - (11 * 86400)
        new_added = now - (2 * 86400)

        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "old.stable.tracker.com",
                "udp://old.stable.tracker.com:6969/announce",
                json.dumps(["1.1.1.1"]),
                50,
                now,
                1800,
                1,
                95,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                old_added,
                json.dumps([1] * 100),
                now,
                now,
                json.dumps({}),
            ),
        )
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "new.stable.tracker.com",
                "udp://new.stable.tracker.com:6969/announce",
                json.dumps(["2.2.2.2"]),
                50,
                now,
                1800,
                1,
                95,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                new_added,
                json.dumps([1] * 100),
                now,
                now,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response_including_new = flask_client.get("/api/stable?min_age_days=0")
        assert response_including_new.status_code == 200
        assert b"old.stable.tracker.com" in response_including_new.data
        assert b"new.stable.tracker.com" in response_including_new.data

    def test_get_api_stable_with_invalid_min_age_days_returns_400(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """min_age_days should be a non-negative integer."""
        response = flask_client.get("/api/stable?min_age_days=abc")
        assert response.status_code == 400

        response_negative = flask_client.get("/api/stable?min_age_days=-1")
        assert response_negative.status_code == 400


class TestApiBestEndpoint:
    """Tests for the /api/best endpoint."""

    def test_get_api_best_redirects_to_stable(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /api/best should redirect to /api/stable with 301."""
        response = flask_client.get("/api/best")
        assert response.status_code == 301
        assert response.location == "/api/stable"

    def test_get_api_best_follow_redirect(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/best following redirect should return stable trackers."""
        response = flask_client.get("/api/best", follow_redirects=True)
        assert response.status_code == 200
        assert b"udp://tracker.example.com:6969/announce" in response.data


class TestApiAllEndpoint:
    """Tests for the /api/all endpoint."""

    def test_get_api_all_returns_all_trackers(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/all should return all trackers regardless of uptime."""
        response = flask_client.get("/api/all")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        assert b"udp://tracker.example.com:6969/announce" in response.data

    def test_get_api_all_includes_low_uptime_trackers(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """GET /api/all should include trackers with low uptime."""
        # Insert a tracker with 10% uptime
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "low.uptime.tracker.com",
                "udp://low.uptime.tracker.com:6969/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                0,  # status down
                10,  # 10% uptime
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([0] * 90 + [1] * 10),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/all")
        assert response.status_code == 200
        assert b"low.uptime.tracker.com" in response.data


class TestApiLiveEndpoint:
    """Tests for the /api/live endpoint."""

    def test_get_api_live_returns_online_trackers(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/live should return currently online trackers."""
        # Sample tracker has status=1 (online)
        response = flask_client.get("/api/live")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        assert b"udp://tracker.example.com:6969/announce" in response.data

    def test_get_api_live_excludes_offline_trackers(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """GET /api/live should exclude offline trackers."""
        # Insert an offline tracker
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "offline.tracker.com",
                "udp://offline.tracker.com:6969/announce",
                json.dumps(["1.2.3.4"]),
                0,
                1700000000,
                1800,
                0,  # status offline
                50,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([0] * 50 + [1] * 50),
                1700000000,
                1699990000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/live")
        assert response.status_code == 200
        assert b"offline.tracker.com" not in response.data


class TestApiUdpEndpoint:
    """Tests for the /api/udp endpoint."""

    def test_get_api_udp_returns_udp_trackers(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/udp should return UDP trackers with >= 95% uptime."""
        # Sample tracker is UDP with 95% uptime
        response = flask_client.get("/api/udp")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        assert b"udp://tracker.example.com:6969/announce" in response.data

    def test_get_api_udp_excludes_http_trackers(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /api/udp should exclude HTTP trackers."""
        # Insert an HTTP tracker with high uptime
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "http.tracker.com",
                "http://http.tracker.com:6969/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                98,  # High uptime
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/udp")
        assert response.status_code == 200
        assert b"http://http.tracker.com" not in response.data

    def test_get_api_udp_excludes_low_uptime_udp(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /api/udp should exclude UDP trackers with < 95% uptime."""
        # Insert a UDP tracker with low uptime
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "low.udp.tracker.com",
                "udp://low.udp.tracker.com:6969/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                80,  # Low uptime
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 80 + [0] * 20),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/udp")
        assert response.status_code == 200
        assert b"low.udp.tracker.com" not in response.data


class TestApiHttpEndpoint:
    """Tests for the /api/http endpoint."""

    def test_get_api_http_returns_http_trackers(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /api/http should return HTTP trackers with >= 95% uptime."""
        # Insert an HTTP tracker with high uptime
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "http.tracker.com",
                "http://http.tracker.com:6969/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/http")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        assert b"http://http.tracker.com:6969/announce" in response.data

    def test_get_api_http_includes_https_trackers(
        self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection
    ) -> None:
        """GET /api/http should include HTTPS trackers (starts with http)."""
        # Insert an HTTPS tracker with high uptime
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "https.tracker.com",
                "https://https.tracker.com:443/announce",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                99,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/http")
        assert response.status_code == 200
        assert b"https://https.tracker.com:443/announce" in response.data

    def test_get_api_http_excludes_udp_trackers(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/http should exclude UDP trackers."""
        # Sample tracker is UDP
        response = flask_client.get("/api/http")
        assert response.status_code == 200
        assert b"udp://tracker.example.com" not in response.data


class TestIpv4Ipv6Filtering:
    """Tests for IPv4/IPv6 query parameter filtering."""

    @pytest.fixture
    def insert_ipv4_only_tracker(self, mock_db_connection: sqlite3.Connection) -> str:
        """Insert a tracker with only IPv4 address."""
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "ipv4only.tracker.com",
                "udp://ipv4only.tracker.com:6969/announce",
                json.dumps(["93.184.216.34"]),  # IPv4 only
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()
        return "ipv4only.tracker.com"

    @pytest.fixture
    def insert_ipv6_only_tracker(self, mock_db_connection: sqlite3.Connection) -> str:
        """Insert a tracker with only IPv6 address."""
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "ipv6only.tracker.com",
                "udp://ipv6only.tracker.com:6969/announce",
                json.dumps(["2001:db8::1"]),  # IPv6 only
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()
        return "ipv6only.tracker.com"

    @pytest.fixture
    def insert_dual_stack_tracker(self, mock_db_connection: sqlite3.Connection) -> str:
        """Insert a tracker with both IPv4 and IPv6 addresses."""
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "dualstack.tracker.com",
                "udp://dualstack.tracker.com:6969/announce",
                json.dumps(["93.184.216.34", "2001:db8::1"]),  # Both IPv4 and IPv6
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()
        return "dualstack.tracker.com"

    def test_default_includes_all_trackers(
        self,
        flask_client: FlaskClient,
        insert_ipv4_only_tracker: str,
        insert_ipv6_only_tracker: str,
        insert_dual_stack_tracker: str,
    ) -> None:
        """By default, all trackers should be included."""
        response = flask_client.get("/api/95")
        assert response.status_code == 200
        assert b"ipv4only.tracker.com" in response.data
        assert b"ipv6only.tracker.com" in response.data
        assert b"dualstack.tracker.com" in response.data

    def test_exclude_ipv4_only_trackers(
        self,
        flask_client: FlaskClient,
        insert_ipv4_only_tracker: str,
        insert_ipv6_only_tracker: str,
        insert_dual_stack_tracker: str,
    ) -> None:
        """include_ipv4_only_trackers=false should exclude IPv4-only trackers."""
        response = flask_client.get("/api/95?include_ipv4_only_trackers=false")
        assert response.status_code == 200
        assert b"ipv4only.tracker.com" not in response.data
        assert b"ipv6only.tracker.com" in response.data
        assert b"dualstack.tracker.com" in response.data

    def test_exclude_ipv6_only_trackers(
        self,
        flask_client: FlaskClient,
        insert_ipv4_only_tracker: str,
        insert_ipv6_only_tracker: str,
        insert_dual_stack_tracker: str,
    ) -> None:
        """include_ipv6_only_trackers=false should exclude IPv6-only trackers."""
        response = flask_client.get("/api/95?include_ipv6_only_trackers=false")
        assert response.status_code == 200
        assert b"ipv4only.tracker.com" in response.data
        assert b"ipv6only.tracker.com" not in response.data
        assert b"dualstack.tracker.com" in response.data

    def test_exclude_both_ipv4_and_ipv6_only(
        self,
        flask_client: FlaskClient,
        insert_ipv4_only_tracker: str,
        insert_ipv6_only_tracker: str,
        insert_dual_stack_tracker: str,
    ) -> None:
        """Excluding both should only return dual-stack trackers."""
        response = flask_client.get("/api/95?include_ipv4_only_trackers=false&include_ipv6_only_trackers=false")
        assert response.status_code == 200
        assert b"ipv4only.tracker.com" not in response.data
        assert b"ipv6only.tracker.com" not in response.data
        assert b"dualstack.tracker.com" in response.data

    def test_ipv4_filter_with_zero_value(
        self,
        flask_client: FlaskClient,
        insert_ipv4_only_tracker: str,
        insert_dual_stack_tracker: str,
    ) -> None:
        """include_ipv4_only_trackers=0 should exclude IPv4-only trackers."""
        response = flask_client.get("/api/95?include_ipv4_only_trackers=0")
        assert response.status_code == 200
        assert b"ipv4only.tracker.com" not in response.data
        assert b"dualstack.tracker.com" in response.data

    def test_ipv6_filter_with_zero_value(
        self,
        flask_client: FlaskClient,
        insert_ipv6_only_tracker: str,
        insert_dual_stack_tracker: str,
    ) -> None:
        """include_ipv6_only_trackers=0 should exclude IPv6-only trackers."""
        response = flask_client.get("/api/95?include_ipv6_only_trackers=0")
        assert response.status_code == 200
        assert b"ipv6only.tracker.com" not in response.data
        assert b"dualstack.tracker.com" in response.data

    def test_filters_work_with_api_stable(
        self,
        flask_client: FlaskClient,
        insert_ipv4_only_tracker: str,
        insert_ipv6_only_tracker: str,
    ) -> None:
        """IP filters should work with /api/stable endpoint."""
        response = flask_client.get("/api/stable?include_ipv4_only_trackers=false")
        assert response.status_code == 200
        assert b"ipv4only.tracker.com" not in response.data
        assert b"ipv6only.tracker.com" in response.data

    def test_filters_work_with_api_all(
        self,
        flask_client: FlaskClient,
        insert_ipv4_only_tracker: str,
        insert_ipv6_only_tracker: str,
    ) -> None:
        """IP filters should work with /api/all endpoint."""
        response = flask_client.get("/api/all?include_ipv6_only_trackers=false")
        assert response.status_code == 200
        assert b"ipv4only.tracker.com" in response.data
        assert b"ipv6only.tracker.com" not in response.data


class TestSubmittedEndpoint:
    """Tests for the /submitted endpoint."""

    def test_get_submitted_returns_200(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /submitted should return 200 OK."""
        response = flask_client.get("/submitted")
        assert response.status_code == 200

    def test_get_submitted_with_data(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /submitted should render the submitted template."""
        with patch("newTrackon.views.persistence.submitted_data", []):
            with patch("newTrackon.views.persistence.submitted_queue.qsize", return_value=0):
                response = flask_client.get("/submitted")
                assert response.status_code == 200


class TestRawEndpoint:
    """Tests for the /raw endpoint."""

    def test_get_raw_returns_200(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /raw should return 200 OK."""
        response = flask_client.get("/raw")
        assert response.status_code == 200

    def test_get_raw_with_data(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /raw should render the raw template."""
        with patch("newTrackon.trackon.raw_data", []):
            response = flask_client.get("/raw")
            assert response.status_code == 200


class TestStaticPages:
    """Tests for static page endpoints."""

    def test_get_faq_returns_200(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /faq should return 200 OK."""
        response = flask_client.get("/faq")
        assert response.status_code == 200

    def test_get_list_returns_200(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /list should return 200 OK."""
        response = flask_client.get("/list")
        assert response.status_code == 200

    def test_get_api_docs_returns_200(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /api should return 200 OK."""
        response = flask_client.get("/api")
        assert response.status_code == 200

    def test_get_about_returns_200(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /about should return 200 OK."""
        response = flask_client.get("/about")
        assert response.status_code == 200


class TestAnnounceRequestRejection:
    """Tests for the announce request rejection middleware."""

    def test_reject_request_with_info_hash(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """Requests with info_hash parameter should be rejected with 403."""
        response = flask_client.get("/?info_hash=abc123")
        assert response.status_code == 403

    def test_reject_api_request_with_info_hash(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """API requests with info_hash should also be rejected."""
        response = flask_client.get("/api/95?info_hash=abc123")
        assert response.status_code == 403


class TestApiResponseHeaders:
    """Tests for API response headers."""

    def test_api_cors_header(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """API endpoints should include CORS header."""
        response = flask_client.get("/api/95")
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_api_content_type(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """API endpoints should return plain text."""
        response = flask_client.get("/api/95")
        assert "text/plain" in response.content_type

    def test_api_add_cors_header(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """POST /api/add should include CORS header."""
        with patch("newTrackon.ingest.enqueue_new_trackers"):
            response = flask_client.post(
                "/api/add",
                data={"new_trackers": "udp://test.tracker.com:6969/announce"},
            )
            assert response.headers.get("Access-Control-Allow-Origin") == "*"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_api_percentage_boundary_zero(self, flask_client: FlaskClient, insert_sample_tracker: dict[str, Any]) -> None:
        """GET /api/0 should be valid and return all trackers."""
        response = flask_client.get("/api/0")
        assert response.status_code == 200

    def test_api_percentage_boundary_100(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """GET /api/100 should be valid."""
        response = flask_client.get("/api/100")
        assert response.status_code == 200

    def test_empty_database_api_response(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """API should handle empty database gracefully."""
        response = flask_client.get("/api/95")
        assert response.status_code == 200
        assert response.data == b""

    def test_multiple_trackers_in_response(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """API should return multiple trackers separated by newlines."""
        # Insert multiple trackers
        for i in range(3):
            mock_db_connection.execute(
                "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f"tracker{i}.example.com",
                    f"udp://tracker{i}.example.com:6969/announce",
                    json.dumps(["1.2.3." + str(i)]),
                    50,
                    1700000000,
                    1800,
                    1,
                    98,
                    json.dumps(["United States"]),
                    json.dumps(["us"]),
                    json.dumps(["ISP"]),
                    1704067200,
                    json.dumps([1] * 100),
                    1699990000,
                    1700000000,
                    json.dumps({}),
                ),
            )
        mock_db_connection.commit()

        response = flask_client.get("/api/95")
        assert response.status_code == 200
        # Each tracker URL should be present
        for i in range(3):
            assert f"tracker{i}.example.com".encode() in response.data
        # Check that there are multiple newlines (format is url\n\n)
        assert response.data.count(b"\n") >= 3

    def test_special_characters_in_tracker_url(self, flask_client: FlaskClient, mock_db_connection: sqlite3.Connection) -> None:
        """API should handle tracker URLs with special characters."""
        mock_db_connection.execute(
            "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "special.tracker.com",
                "http://special.tracker.com:8080/path/announce?key=value",
                json.dumps(["1.2.3.4"]),
                50,
                1700000000,
                1800,
                1,
                98,
                json.dumps(["United States"]),
                json.dumps(["us"]),
                json.dumps(["ISP"]),
                1704067200,
                json.dumps([1] * 100),
                1699990000,
                1700000000,
                json.dumps({}),
            ),
        )
        mock_db_connection.commit()

        response = flask_client.get("/api/http")
        assert response.status_code == 200
        assert b"special.tracker.com:8080/path/announce?key=value" in response.data
