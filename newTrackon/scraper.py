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

import requests

from newTrackon.bdecode import bdecode, decode_binary_peers_list
from newTrackon.persistence import submitted_data
from newTrackon import utils

HTTP_PORT = 6881
UDP_PORT = 30461
SCRAPING_HEADERS = {
    "User-Agent": "qBittorrent/4.2.5",
    "Accept-Encoding": "gzip",
    "Connection": "close",
}

logger = getLogger("newtrackon_logger")

to_redact = [str(HTTP_PORT), str(UDP_PORT)]


def attempt_submitted(tracker):
    submitted_url = urlparse(tracker.url)
    try:
        failover_ip = socket.getaddrinfo(submitted_url.hostname, None)[0][4][0]
    except OSError:
        failover_ip = ""

    # UDP scrape
    if submitted_url.port:  # If the tracker netloc has a port, try with UDP
        udp_success, latency, udp_response, udp_url = attempt_udp(
            failover_ip, submitted_url.netloc
        )
        if udp_success:
            return latency, udp_response["interval"], udp_url

        logger.info(f"{udp_url} UDP failed, trying HTTPS")

    # HTTPS scrape
    https_success, https_response, https_url, latency = attempt_httpx(
        failover_ip, submitted_url, tls=True
    )
    if https_success:
        return latency, https_response["interval"], https_url

    logger.info(f"{https_url} HTTPS failed, trying HTTP")

    # HTTP scrape
    debug_success, http_response, http_url, latency = attempt_httpx(
        failover_ip, submitted_url, tls=False
    )
    if debug_success:
        return latency, http_response["interval"], http_url

    logger.info(f"{http_url} HTTP failed, giving up on submitted tracker {tracker.url}")
    raise RuntimeError


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
    return debug_http["status"], http_response, http_url, latency


def build_httpx_url(submitted_url, tls):
    if tls:
        scheme = "https://"
        default_port = 443
    else:
        scheme = "http://"
        default_port = 80
    if not submitted_url.port:
        http_url = scheme + submitted_url.netloc + ":" + str(default_port) + "/announce"
    else:
        http_url = scheme + submitted_url.netloc + "/announce"
    return http_url


def attempt_udp(failover_ip, tracker_netloc):
    pp = pprint.PrettyPrinter(width=999999, compact=True)
    udp_url = "udp://" + tracker_netloc + "/announce"
    t1 = time()
    udp_attempt_result = {"url": udp_url, "time": int(t1)}
    latency = 0
    parsed_response = ""
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
    return udp_attempt_result["status"], latency, parsed_response, udp_url


def announce_http(url):
    logger.info(f"{url} Scraping HTTP(S)")
    thash = urandom(20)
    pid = "-qB3360-" + "".join(
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
        "ipv6": utils.my_ipv6,
        "ipv4": utils.my_ipv4,
    }
    arguments = urlencode(args_dict)
    url = url + "?" + arguments
    try:
        response = requests.get(url, headers=SCRAPING_HEADERS, timeout=10)
    except requests.Timeout:
        raise RuntimeError("HTTP timeout")
    except requests.HTTPError:
        raise RuntimeError("HTTP error")
    except requests.ConnectionError:
        raise RuntimeError("HTTP connection failed")
    except requests.RequestException:
        raise RuntimeError("Ambiguous HTTP error")
    if response.status_code != 200:
        raise RuntimeError("HTTP %s status code returned" % response.status_code)

    elif not response.content:
        raise RuntimeError("Got empty HTTP response")

    else:
        try:
            tracker_response = bdecode(response.content)
        except:
            raise RuntimeError("Can't bdecode the response")

    if "failure reason" in tracker_response:
        raise RuntimeError(
            'Tracker error message: "%s"' % (tracker_response["failure reason"])
        )
    if "peers" not in tracker_response and "peers6" not in tracker_response:
        raise RuntimeError(
            "Invalid response, both 'peers' and 'peers6' field are missing: "
            + str(tracker_response)
        )
    logger.info(f"{url} response: {tracker_response}")
    return tracker_response


def announce_udp(udp_version):
    thash = urandom(20)
    parsed_tracker = urlparse(udp_version)
    logger.info(f"{udp_version} Scraping UDP")
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
    logger.info(f"{udp_version} response: {parsed_response}")
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
        raise RuntimeError("Wrong response length getting connection id: %s" % len(buf))
    action = struct.unpack_from("!i", buf)[0]  # first 4 bytes is action

    res_transaction_id = struct.unpack_from("!i", buf, 4)[
        0
    ]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError(
            "Transaction ID doesn't match in connection response. Expected %s, got %s"
            % (sent_transaction_id, res_transaction_id)
        )

    if action == 0x0:
        connection_id = struct.unpack_from("!q", buf, 8)[
            0
        ]  # unpack 8 bytes from byte 8, should be the connection_id
        return connection_id
    elif action == 0x3:
        error = struct.unpack_from("!s", buf, 8)
        raise RuntimeError(
            "Error while trying to get a connection response: %s" % error
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
        raise RuntimeError("Wrong response length while announcing: %s" % len(buf))
    action = struct.unpack_from("!i", buf)[0]  # first 4 bytes is action
    res_transaction_id = struct.unpack_from("!i", buf, 4)[
        0
    ]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError(
            "Transaction ID doesnt match in announce response! Expected %s, got %s"
            % (sent_transaction_id, res_transaction_id)
        )
    if action == 0x1:
        ret = dict()
        offset = (
            8
        )  # next 4 bytes after action is transaction_id, so data doesnt start till byte 8
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
        raise RuntimeError("Error while annoucing: %s" % error)


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


def redact_origin(response):
    if utils.my_ipv4:
        response = response.replace(utils.my_ipv4, "v4-redacted")
    if utils.my_ipv6:
        response = response.replace(utils.my_ipv6, "v6-redacted")
    for port in to_redact:
        response = response.replace(port, "redacted")
    return response
