import pprint
import random
import socket
import string
import struct
import subprocess
from logging import getLogger
from os import urandom
from time import time
from urllib.parse import urlparse, urlencode
from dns import resolver
from dns.exception import DNSException

import requests

from newTrackon.bdecode import bdecode, decode_binary_peers_list
from newTrackon.persistence import submitted_data
from newTrackon.utils import process_txt_prefs, build_httpx_url
from urllib3.exceptions import HTTPError

HTTP_PORT = 6881
UDP_PORT = 30461
my_ipv4 = None
my_ipv6 = None
SCRAPING_HEADERS = {
    "User-Agent": "qBittorrent/4.3.9",
    "Accept-Encoding": "gzip",
    "Connection": "close",
}
MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB

logger = getLogger("newtrackon_logger")

to_redact = [str(HTTP_PORT), str(UDP_PORT)]


def attempt_submitted(tracker):
    submitted_url = urlparse(tracker.url)
    try:
        failover_ip = socket.getaddrinfo(submitted_url.hostname, None)[0][4][0]
    except OSError:
        failover_ip = ""

    valid_bep_34, bep_34_info = get_bep_34(submitted_url.hostname)

    if valid_bep_34:  # Hostname has a valid TXT record as per BEP34
        if not bep_34_info:
            logger.info(
                f"Hostname denies connection via BEP34, giving up on submitted tracker {tracker.url}"
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
        elif bep_34_info:
            logger.info(
                f"Tracker {tracker.url} sets protocol and port preferences from BEP34: {str(bep_34_info)}"
            )
            return attempt_from_txt_prefs(submitted_url, failover_ip, bep_34_info)
    else:  # No valid BEP34, attempting all protocols
        return attempt_all_protocols(submitted_url, failover_ip)


def attempt_from_txt_prefs(submitted_url, failover_ip, txt_prefs):
    for preference in txt_prefs:
        preferred_url = submitted_url._replace(
            netloc="{}:{}".format(submitted_url.hostname, preference[1])
        )
        if preference[0] == "udp":
            udp_success, udp_interval, udp_url, latency = attempt_udp(
                failover_ip, preferred_url.netloc
            )
            if udp_success:
                return udp_interval, udp_url, latency
        elif preference[0] == "tcp":
            http_success, http_interval, http_url, latency = attempt_https_http(
                failover_ip, preferred_url
            )
            if http_success:
                return http_interval, http_url, latency

    logger.info(
        f"All DNS TXT protocol preferences failed, giving up on submitted tracker {submitted_url.geturl()}"
    )
    raise RuntimeError


def attempt_all_protocols(submitted_url, failover_ip):
    # UDP scrape
    if submitted_url.port:  # If the tracker netloc has a port, try with UDP
        udp_success, udp_interval, udp_url, latency = attempt_udp(
            failover_ip, submitted_url.netloc
        )
        if udp_success:
            return udp_interval, udp_url, latency

        logger.info(f"{udp_url} UDP failed")

    # HTTPS and HTTP scrape
    http_success, http_interval, http_url, latency = attempt_https_http(
        failover_ip, submitted_url
    )
    if http_success:
        return http_interval, http_url, latency
    logger.info(
        f"All protocols failed, giving up on submitted tracker {submitted_url.geturl()}"
    )
    raise RuntimeError


def attempt_https_http(failover_ip, url):
    # HTTPS scrape
    https_success, https_interval, https_url, latency = attempt_httpx(
        failover_ip, url, tls=True
    )
    if https_success:
        return https_success, https_interval, https_url, latency

    logger.info(f"{https_url} HTTPS failed")

    # HTTP scrape
    http_success, http_interval, http_url, latency = attempt_httpx(
        failover_ip, url, tls=False
    )
    if http_success:
        return http_success, http_interval, http_url, latency

    logger.info(f"{http_url} HTTP failed")
    return None, None, None, None


def attempt_httpx(failover_ip, submitted_url, tls=True):
    http_url = build_httpx_url(submitted_url, tls)
    pp = pprint.PrettyPrinter(width=999999, compact=True)
    t1 = time()
    debug_http = {"url": http_url, "time": int(t1), "ip": failover_ip}
    latency = 0
    http_response = {}
    try:
        http_response = announce_http(http_url)
        latency = int((time() - t1) * 1000)
        pretty_data = redact_origin(pp.pformat(http_response))
        debug_http.update({"info": [pretty_data], "status": 1})
    except RuntimeError as e:
        debug_http.update({"info": [redact_origin(str(e))], "status": 0})
    submitted_data.appendleft(debug_http)
    return debug_http["status"], http_response.get("interval"), http_url, latency


def attempt_udp(failover_ip, tracker_netloc):
    pp = pprint.PrettyPrinter(width=999999, compact=True)
    udp_url = "udp://" + tracker_netloc + "/announce"
    t1 = time()
    udp_attempt_result = {"url": udp_url, "time": int(t1)}
    latency = 0
    parsed_response = {}
    try:
        parsed_response, ip = announce_udp(udp_url)
        latency = int((time() - t1) * 1000)
        pretty_data = redact_origin(pp.pformat(parsed_response))
        udp_attempt_result.update({"info": [pretty_data], "status": 1, "ip": ip})
    except RuntimeError as e:
        udp_attempt_result.update({"info": [str(e)], "status": 0})
        if udp_attempt_result["info"] != ["Can't resolve IP"]:
            udp_attempt_result["ip"] = failover_ip
    submitted_data.appendleft(udp_attempt_result)
    return (
        udp_attempt_result["status"],
        parsed_response.get("interval"),
        udp_url,
        latency,
    )


def get_bep_34(hostname):
    """Querying for http://bittorrent.org/beps/bep_0034.html"""
    try:
        answers = resolver.resolve(hostname, "TXT")
        for record in answers:
            record_text = str(record)[1:-1]
            if record_text.startswith("BITTORRENT"):
                return True, process_txt_prefs(record_text)
    except DNSException:
        pass
    return False, None


def announce_http(url, thash=urandom(20)):
    logger.info(f"{url} Scraping HTTP(S)")
    pid = "-qB4390-" + "".join(
        [random.choice(string.ascii_letters + string.digits) for _ in range(12)]
    )

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
    except (HTTPError, requests.RequestException):
        raise RuntimeError("Unhandled HTTP error")
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} status code returned")

    elif not content:
        raise RuntimeError("Got empty HTTP response")

    else:
        try:
            tracker_response = bdecode(content)
        except:
            raise RuntimeError("Can't bdecode the response")

    if "failure reason" in tracker_response:
        raise RuntimeError(
            f'Tracker error message: {tracker_response["failure reason"]}'
        )
    if "peers" not in tracker_response and "peers6" not in tracker_response:
        raise RuntimeError(
            f"Invalid response, both 'peers' and 'peers6' field are missing: {str(tracker_response)}"
        )
    logger.info(f"{url} response: {tracker_response}")
    return tracker_response


def announce_udp(udp_url, thash=urandom(20)):
    parsed_tracker = urlparse(udp_url)
    logger.info(f"{udp_url} Scraping UDP")
    sock = None
    ip = None
    getaddr_responses = []
    try:
        for res in socket.getaddrinfo(
            parsed_tracker.hostname, parsed_tracker.port, 0, socket.SOCK_DGRAM
        ):
            getaddr_responses.append(res)
    except OSError as err:
        raise RuntimeError("UDP error: " + str(err))

    for res in getaddr_responses:
        af, socktype, proto, _, sa = res
        ip = sa[0]
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

    # Get connection ID
    req, transaction_id = udp_create_binary_connection_request()
    try:
        sock.sendall(req)
        buf = sock.recv(2048)
    except ConnectionRefusedError:
        raise RuntimeError("UDP connection failed")
    except socket.timeout:
        raise RuntimeError("UDP timeout")
    except OSError as err:
        raise RuntimeError("UDP error: " + str(err))

    connection_id = udp_parse_connection_response(buf, transaction_id)
    # Scrape away
    req, transaction_id = udp_create_announce_request(connection_id, thash)
    try:
        sock.sendall(req)
        buf = sock.recv(2048)
    except ConnectionRefusedError:
        raise RuntimeError("UDP connection failed")
    except socket.timeout:
        raise RuntimeError("UDP timeout")
    except OSError as err:
        raise RuntimeError("UDP error: " + str(err))
    ip_family = sock.family
    sock.close()
    parsed_response, raw_response = udp_parse_announce_response(
        buf, transaction_id, ip_family
    )
    logger.info(f"{udp_url} response: {parsed_response}")
    return parsed_response, ip


def udp_create_binary_connection_request():
    connection_id = 0x41727101980  # default connection id
    action = 0x0  # action (0 = give me a new connection id)
    transaction_id = udp_get_transaction_id()
    buf = struct.pack("!q", connection_id)  # first 8 bytes is connection id
    buf += struct.pack("!i", action)  # next 4 bytes is action
    buf += struct.pack("!i", transaction_id)  # next 4 bytes is transaction id
    return buf, transaction_id


def udp_parse_connection_response(buf, sent_transaction_id):
    if len(buf) < 16:
        raise RuntimeError(f"Wrong response length getting connection id: {len(buf)}")
    action = struct.unpack_from("!i", buf)[0]  # first 4 bytes is action

    res_transaction_id = struct.unpack_from("!i", buf, 4)[
        0
    ]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError(
            f"Transaction ID doesn't match in connection response. Expected {sent_transaction_id}, got {res_transaction_id}"
        )

    if action == 0x0:
        connection_id = struct.unpack_from("!q", buf, 8)[
            0
        ]  # unpack 8 bytes from byte 8, should be the connection_id
        return connection_id
    elif action == 0x3:
        error = struct.unpack_from("!s", buf, 8)
        raise RuntimeError(
            f"Error while trying to get a connection response: {error}"
        )


def udp_create_announce_request(connection_id, thash):
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
    buf += struct.pack(
        "!i", 0x0
    )  # IP address set to 0. Response received to the sender of this packet
    key = udp_get_transaction_id()  # Unique key randomized by client
    buf += struct.pack("!i", key)
    buf += struct.pack("!i", -1)  # Number of peers required. Set to -1 for default
    buf += struct.pack("!H", 0x76FD)  # port on which response will be sent
    return buf, transaction_id


def udp_parse_announce_response(buf, sent_transaction_id, ip_family):
    if len(buf) < 20:
        raise RuntimeError(f"Wrong response length while announcing: {len(buf)}")
    action = struct.unpack_from("!i", buf)[0]  # first 4 bytes is action
    res_transaction_id = struct.unpack_from("!i", buf, 4)[
        0
    ]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError(
            f"Transaction ID doesnt match in announce response! Expected {sent_transaction_id}, got {res_transaction_id}"
        )
    if action == 0x1:
        ret = dict()
        offset = 8  # next 4 bytes after action is transaction_id, so data doesnt start till byte 8
        ret["interval"] = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        ret["leechers"] = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        ret["seeds"] = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        ret["peers"] = decode_binary_peers_list(buf, offset, ip_family)
        return ret, buf.hex()
    else:
        # an error occured, try and extract the error string
        error = struct.unpack_from("!s", buf, 8)
        raise RuntimeError(f"Error while annoucing: {error}")


def udp_get_transaction_id():
    return int(random.randrange(0, 255))


def get_server_ip(ip_version):
    return (
        subprocess.check_output(
            ["curl", "-s", "-" + ip_version, "https://icanhazip.com/"]
        )
        .decode("utf-8")
        .strip()
    )


def memory_limited_get(url):
    response = requests.get(url, headers=SCRAPING_HEADERS, timeout=10, stream=True)
    content = None
    content = response.raw.read(MAX_RESPONSE_SIZE + 1, decode_content=True)
    if len(content) > MAX_RESPONSE_SIZE:
        raise RuntimeError("HTTP response size above 1 MB")
    return response, content


def redact_origin(response):
    if my_ipv4:
        response = response.replace(my_ipv4, "v4-redacted")
    if my_ipv6:
        response = response.replace(my_ipv6, "v6-redacted")
    for port in to_redact:
        response = response.replace(port, "redacted")
    return response
