import pprint
import random
import socket
import string
import struct
import subprocess
from logging import getLogger
from os import urandom
from time import time
from typing import TYPE_CHECKING, NamedTuple, TypedDict
from urllib.parse import ParseResult, urlencode, urlparse

import requests
from dns import resolver
from dns.exception import DNSException
from urllib3.exceptions import HTTPError

from newTrackon.bdecode import BDecodeResponse, PeerInfo, bdecode, decode_binary_peers_list
from newTrackon.persistence import HistoryData, submitted_data
from newTrackon.utils import ProtocolPref, build_httpx_url, process_txt_prefs

if TYPE_CHECKING:
    from newTrackon.tracker import Tracker

# Socket address types for getaddrinfo results
SockAddr = tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes]
AddrInfo = tuple[socket.AddressFamily, socket.SocketKind, int, str, SockAddr]


class ScraperResult(NamedTuple):
    """Result from a successful tracker scrape attempt."""

    interval: int
    url: str
    latency: int


class AttemptResult(NamedTuple):
    """Result from an individual protocol attempt (HTTP/UDP)."""

    status: int
    interval: int | None
    url: str
    latency: int


HTTP_PORT: int = 6881
UDP_PORT: int = 30461
my_ipv4: str | None = None
my_ipv6: str | None = None
SCRAPING_HEADERS: dict[str, str] = {
    "User-Agent": "qBittorrent/4.3.9",
    "Accept-Encoding": "gzip",
    "Connection": "close",
}
MAX_RESPONSE_SIZE: int = 1024 * 1024  # 1MB

logger = getLogger("newtrackon")

to_redact: list[str] = [str(HTTP_PORT), str(UDP_PORT)]


class UDPAnnounceResponse(TypedDict):
    interval: int
    leechers: int
    seeds: int
    peers: list[PeerInfo]


def attempt_submitted(tracker: Tracker) -> ScraperResult:
    submitted_url = urlparse(tracker.url)
    try:
        failover_ip: str = str(socket.getaddrinfo(submitted_url.hostname, None)[0][4][0])
    except OSError:
        failover_ip = ""

    valid_bep_34, bep_34_info = get_bep_34(submitted_url.hostname)

    if valid_bep_34:  # Hostname has a valid TXT record as per BEP34
        if not bep_34_info:
            logger.info(
                "Hostname denies connection via BEP34, giving up on submitted tracker %s",
                tracker.url,
            )
            submitted_data.appendleft(
                {
                    "url": tracker.url,
                    "time": int(time()),
                    "status": 0,
                    "ip": failover_ip,
                    "info": ["Host denied connection according to BEP34"],
                }
            )
            raise RuntimeError
        logger.info(
            "Tracker %s sets protocol and port preferences from BEP34: %s",
            tracker.url,
            bep_34_info,
        )
        return attempt_from_txt_prefs(submitted_url, failover_ip, bep_34_info)
    # No valid BEP34, attempting all protocols
    return attempt_all_protocols(submitted_url, failover_ip)


def attempt_from_txt_prefs(submitted_url: ParseResult, failover_ip: str, txt_prefs: list[ProtocolPref]) -> ScraperResult:
    for protocol, port in txt_prefs:
        preferred_url = submitted_url._replace(netloc=f"{submitted_url.hostname}:{port}")
        if protocol == "udp":
            result = attempt_udp(failover_ip, preferred_url.netloc)
            if result.status and result.interval is not None:
                return ScraperResult(result.interval, result.url, result.latency)
        elif protocol == "tcp":
            http_result = attempt_https_http(failover_ip, preferred_url)
            if http_result is not None:
                return ScraperResult(http_result.interval, http_result.url, http_result.latency)

    logger.info(
        "All DNS TXT protocol preferences failed, giving up on submitted tracker %s",
        submitted_url.geturl(),
    )
    raise RuntimeError


def attempt_all_protocols(submitted_url: ParseResult, failover_ip: str) -> ScraperResult:
    # UDP scrape
    if submitted_url.port:  # If the tracker netloc has a port, try with UDP
        result = attempt_udp(failover_ip, submitted_url.netloc)
        if result.status and result.interval is not None:
            return ScraperResult(result.interval, result.url, result.latency)

        logger.info("%s UDP failed", result.url)

    # HTTPS and HTTP scrape
    http_result = attempt_https_http(failover_ip, submitted_url)
    if http_result is not None:
        return ScraperResult(http_result.interval, http_result.url, http_result.latency)
    logger.info(
        "All protocols failed, giving up on submitted tracker %s",
        submitted_url.geturl(),
    )
    raise RuntimeError


def attempt_https_http(failover_ip: str, url: ParseResult, log_to_submitted: bool = True) -> ScraperResult | None:
    # HTTPS scrape
    https_result = attempt_httpx(failover_ip, url, tls=True, log_to_submitted=log_to_submitted)
    if https_result.status and https_result.interval is not None:
        return ScraperResult(https_result.interval, https_result.url, https_result.latency)

    logger.info("%s HTTPS failed", https_result.url)

    # HTTP scrape
    http_result = attempt_httpx(failover_ip, url, tls=False, log_to_submitted=log_to_submitted)
    if http_result.status and http_result.interval is not None:
        return ScraperResult(http_result.interval, http_result.url, http_result.latency)

    logger.info("%s HTTP failed", http_result.url)
    return None


def attempt_httpx(failover_ip: str, submitted_url: ParseResult, tls: bool = True, log_to_submitted: bool = True) -> AttemptResult:
    http_url = build_httpx_url(submitted_url, tls)
    pp = pprint.PrettyPrinter(width=999999, compact=True)
    t1 = time()
    latency = 0
    status = 0
    interval: int | None = None
    info: list[str] = []
    try:
        http_response = announce_http(http_url)
        latency = int((time() - t1) * 1000)
        pretty_data = redact_origin(pp.pformat(http_response))
        info = [pretty_data]
        status = 1
        raw_interval = http_response.get("interval")
        if isinstance(raw_interval, int):
            interval = raw_interval
    except RuntimeError as e:
        info = [redact_origin(str(e))]
        status = 0
    if log_to_submitted:
        debug_http: HistoryData = {"url": http_url, "time": int(t1), "ip": failover_ip, "info": info, "status": status}
        submitted_data.appendleft(debug_http)
    return AttemptResult(status, interval, http_url, latency)


def attempt_udp(failover_ip: str, tracker_netloc: str) -> AttemptResult:
    pp = pprint.PrettyPrinter(width=999999, compact=True)
    udp_url = "udp://" + tracker_netloc + "/announce"
    t1 = time()
    latency = 0
    status = 0
    interval: int | None = None
    info: list[str] = []
    ip = failover_ip
    try:
        parsed_response, resolved_ip = announce_udp(udp_url)
        latency = int((time() - t1) * 1000)
        pretty_data = redact_origin(pp.pformat(parsed_response))
        info = [pretty_data]
        status = 1
        interval = parsed_response["interval"]
        if resolved_ip is not None:
            ip = resolved_ip
    except RuntimeError as e:
        error_msg = str(e)
        info = [error_msg]
        status = 0
        if error_msg == "Can't resolve IP":
            ip = ""
    udp_attempt_result: HistoryData = {"url": udp_url, "time": int(t1), "ip": ip, "info": info, "status": status}
    submitted_data.appendleft(udp_attempt_result)
    return AttemptResult(status, interval, udp_url, latency)


def get_bep_34(hostname: str | None) -> tuple[bool, list[ProtocolPref] | None]:
    """Querying for http://bittorrent.org/beps/bep_0034.html"""
    if hostname is None:
        return False, None
    try:
        answer: resolver.Answer = resolver.resolve(hostname, "TXT")
        for rdata in answer:
            record_text = str(rdata).strip('"')
            if record_text.startswith("BITTORRENT"):
                return True, process_txt_prefs(record_text)
    except DNSException:
        pass
    return False, None


def announce_http(url: str, thash: bytes = urandom(20)) -> BDecodeResponse:
    logger.info("%s Scraping HTTP(S)", url)
    pid = "-qB4390-" + "".join([random.choice(string.ascii_letters + string.digits) for _ in range(12)])

    args_dict = {
        "info_hash": thash,
        "peer_id": pid,
        "port": HTTP_PORT,
        "uploaded": 0,
        "downloaded": 0,
        "left": 0,
        "compact": 1,
        "ipv6": my_ipv6,
        "ipv4": my_ipv4,
    }
    arguments = urlencode(args_dict)
    url = url + "?" + arguments
    try:
        response, content = memory_limited_get(url)
    except RuntimeError as too_big:
        raise too_big
    except requests.Timeout:
        raise RuntimeError("HTTP timeout")
    except requests.ConnectionError:
        raise RuntimeError("HTTP connection failed")
    except HTTPError, requests.RequestException:
        raise RuntimeError("Unhandled HTTP error")
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} status code returned")

    elif not content:
        raise RuntimeError("Got empty HTTP response")

    else:
        try:
            tracker_response = bdecode(content)
        except Exception as e:
            raise RuntimeError(f"Failed bdecoding HTTP response: {e}")

    if "failure reason" in tracker_response:
        raise RuntimeError(f"Tracker error message: {tracker_response['failure reason']}")
    if "peers" not in tracker_response and "peers6" not in tracker_response:
        raise RuntimeError(f"Invalid response, both 'peers' and 'peers6' field are missing: {tracker_response}")
    logger.info("%s response: %s", url, tracker_response)
    return tracker_response


def announce_udp(udp_url: str, thash: bytes = urandom(20)) -> tuple[UDPAnnounceResponse, str | None]:
    parsed_tracker = urlparse(udp_url)
    logger.info("%s Scraping UDP", udp_url)
    ip: str | None = None
    getaddr_responses: list[AddrInfo] = []
    try:
        for res in socket.getaddrinfo(parsed_tracker.hostname, parsed_tracker.port, 0, socket.SOCK_DGRAM):
            getaddr_responses.append(res)
    except OSError as err:
        raise RuntimeError(f"UDP error: {err}")

    last_error = RuntimeError("UDP announce failed")
    for attempt in range(2):
        logger.info("%s UDP attempt %d", udp_url, attempt + 1)

        sock: socket.socket | None = None
        for res in getaddr_responses:
            af, socktype, proto, _, sa = res
            ip = str(sa[0])
            try:
                sock = socket.socket(af, socktype, proto)
                sock.settimeout(10)
            except OSError:
                sock = None
                continue
            try:
                sock.connect(sa)
            except OSError:
                sock.close()
                sock = None
                continue
            break
        if sock is None:
            raise RuntimeError("UDP connection error")

        try:
            # Get connection ID
            req, transaction_id = udp_create_binary_connection_request()
            sock.sendall(req)
            buf = sock.recv(2048)
            connection_id = udp_parse_connection_response(buf, transaction_id)

            # Announce
            req, transaction_id = udp_create_announce_request(connection_id, thash)
            sock.sendall(req)
            buf = sock.recv(2048)
            ip_family = sock.family
            sock.close()

            parsed_response, _raw_response = udp_parse_announce_response(buf, transaction_id, ip_family)
            logger.info("%s response: %s", udp_url, parsed_response)
            return parsed_response, ip
        except ConnectionRefusedError:
            last_error = RuntimeError("UDP connection failed")
        except TimeoutError:
            last_error = RuntimeError("UDP timeout")
        except OSError as err:
            last_error = RuntimeError(f"UDP error: {err}")
        except RuntimeError as err:
            last_error = err
        sock.close()

    raise last_error


def udp_create_binary_connection_request() -> tuple[bytes, int]:
    connection_id = 0x41727101980  # default connection id
    action = 0x0  # action (0 = give me a new connection id)
    transaction_id = udp_get_transaction_id()
    buf = struct.pack("!q", connection_id)  # first 8 bytes is connection id
    buf += struct.pack("!i", action)  # next 4 bytes is action
    buf += struct.pack("!i", transaction_id)  # next 4 bytes is transaction id
    return buf, transaction_id


def udp_parse_connection_response(buf: bytes, sent_transaction_id: int) -> int | None:
    if len(buf) < 16:
        raise RuntimeError(f"Wrong response length getting connection id: {len(buf)}")
    action = struct.unpack_from("!i", buf)[0]  # first 4 bytes is action

    res_transaction_id = struct.unpack_from("!i", buf, 4)[0]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError(
            f"Transaction ID doesn't match in connection response. Expected {sent_transaction_id}, got {res_transaction_id}"
        )

    if action == 0x0:
        connection_id = struct.unpack_from("!q", buf, 8)[0]  # unpack 8 bytes from byte 8, should be the connection_id
        return connection_id
    elif action == 0x3:
        error = struct.unpack_from("!s", buf, 8)
        raise RuntimeError(f"Error while trying to get a connection response: {error}")


def udp_create_announce_request(connection_id: int | None, thash: bytes) -> tuple[bytes, int]:
    action = 0x1  # action (1 = announce)
    transaction_id = udp_get_transaction_id()
    buf = struct.pack("!q", connection_id)  # first 8 bytes is connection id
    buf += struct.pack("!i", action)  # next 4 bytes is action
    buf += struct.pack("!i", transaction_id)  # followed by 4 byte transaction id
    buf += struct.pack("!20s", thash)  # hash
    buf += struct.pack("!20s", thash)  # peer id, should be random
    buf += struct.pack("!q", 0x0)  # number of bytes downloaded
    buf += struct.pack("!q", 0x0)  # number of bytes left
    buf += struct.pack("!q", 0x0)  # number of bytes uploaded
    buf += struct.pack("!i", 0x2)  # event 0 denotes start of downloading
    buf += struct.pack("!i", 0x0)  # IP address set to 0. Response received to the sender of this packet
    key = udp_get_transaction_id()  # Unique key randomized by client
    buf += struct.pack("!i", key)
    buf += struct.pack("!i", -1)  # Number of peers required. Set to -1 for default
    buf += struct.pack("!H", 0x76FD)  # port on which response will be sent
    return buf, transaction_id


def udp_parse_announce_response(
    buf: bytes, sent_transaction_id: int, ip_family: socket.AddressFamily
) -> tuple[UDPAnnounceResponse, str]:
    if len(buf) < 20:
        raise RuntimeError(f"Wrong response length while announcing: {len(buf)}")
    action = struct.unpack_from("!i", buf)[0]  # first 4 bytes is action
    res_transaction_id = struct.unpack_from("!i", buf, 4)[0]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError(
            f"Transaction ID doesnt match in announce response! Expected {sent_transaction_id}, got {res_transaction_id}"
        )
    if action == 0x1:
        offset = 8  # next 4 bytes after action is transaction_id, so data doesnt start till byte 8
        interval = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        leechers = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        seeds = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        peers = decode_binary_peers_list(buf, offset, ip_family)
        ret: UDPAnnounceResponse = {"interval": interval, "leechers": leechers, "seeds": seeds, "peers": peers}
        return ret, buf.hex()
    # an error occured, try and extract the error string
    error = struct.unpack_from("!s", buf, 8)
    raise RuntimeError(f"Error while annoucing: {error}")


def udp_get_transaction_id() -> int:
    return int(random.randrange(0, 255))


def get_server_ip(ip_version: str) -> str:
    return subprocess.check_output(["curl", "-s", "-" + ip_version, "https://icanhazip.com/"]).decode("utf-8").strip()


def memory_limited_get(url: str) -> tuple[requests.Response, bytes]:
    response = requests.get(url, headers=SCRAPING_HEADERS, timeout=10, stream=True, allow_redirects=False)
    content = None
    content = response.raw.read(MAX_RESPONSE_SIZE + 1, decode_content=True)
    if len(content) > MAX_RESPONSE_SIZE:
        raise RuntimeError("HTTP response size above 1 MB")
    return response, content


def redact_origin(response: str) -> str:
    if my_ipv4:
        response = response.replace(my_ipv4, "v4-redacted")
    if my_ipv6:
        response = response.replace(my_ipv6, "v6-redacted")
    for port in to_redact:
        response = response.replace(port, "redacted")
    return response
