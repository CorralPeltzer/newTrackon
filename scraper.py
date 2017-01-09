import binascii
import logging
import random
import socket
import struct
from hashlib import md5
from time import time
from urlparse import urlparse

import requests

from bencode import bdecode

logger = logging.getLogger('trackon_logger')


def scrape(t):
    """
    Returns the update interval, time taken for the announcement and the first URL version correctly contacted

    Args:
        tracker (str): The announce url for a tracker
    """

    tnetloc = urlparse(t).netloc
    # UDP scrape
    if urlparse(t).port:  # If the tracker netloc has a port, try with udp
        udp_version = 'udp://' + tnetloc + '/announce'
        logger.info('Request ' + udp_version)
        try:
            t1 = time()
            interval = scrape_udp(udp_version)
            latency = int((time() - t1) * 1000)
            return latency, interval, udp_version
        except RuntimeError, e:
            logger.info("Error: " + str(e))
            print "UDP not working, trying HTTPS"

    # HTTPS scrape
    if not urlparse(t).port:
        https_version = 'https://' + tnetloc + ':443/announce'
    else:
        https_version = 'https://' + tnetloc + '/announce'
    try:
        logger.info('Request ' + https_version)
        t1 = time()
        interval = scrape_http(https_version)
        latency = int((time() - t1) * 1000)
        return latency, interval, https_version
    except RuntimeError as e:
        logger.info("Error: " + e.message.encode('utf-8'))
        "HTTPS not working, trying HTTP"

    # HTTP scrape
    if not urlparse(t).port:
        http_version = 'http://' + tnetloc + ':80/announce'
    else:
        http_version = 'http://' + tnetloc + '/announce'
    try:
        logger.info('Request ' + http_version)
        t1 = time()
        interval = scrape_http(http_version)
        latency = int((time() - t1) * 1000)
        return latency, interval, http_version
    except RuntimeError as e:
        logger.info("Error: " + e.message.encode('utf-8'))

        raise RuntimeError


def scrape_http(tracker):
    print "Scraping HTTP: %s" % tracker
    thash = trackerhash(tracker)
    pid = "-TO0001-XX" + str(int(time()))
    request = "?info_hash=%s&port=999&peer_id=%s&compact=1&uploaded=0&downloaded=0&left=0" % (thash, pid)
    url = tracker + request
    print url
    try:
        response = requests.get(url, timeout=10)
    except requests.Timeout:
        raise RuntimeError("HTTP timeout")
    except requests.HTTPError:
        raise RuntimeError("HTTP response error code")
    except requests.exceptions.RequestException, e:
        raise RuntimeError("HTTP error: " + str(e))

    info = {}
    if response.status_code is not 200:
        raise RuntimeError("%s status code returned" % response.status_code)

    elif not response.content:
        raise RuntimeError("Got empty HTTP response")

    else:
        try:
            info['response'] = bdecode(response.text)
        except:
            raise RuntimeError("Can't decode the tracker binary response")

    if 'response' in info:
        if 'failure reason' in info['response']:
            raise RuntimeError("Tracker failure reason: \"%s\"." % (info['response']['failure reason']))
        elif 'peers' not in info['response']:
            raise RuntimeError("Invalid response, 'peers' field is missing")

    # TODO Do a more extensive check of what was returned
    print "interval: ", info['response']['interval']
    return info['response']['interval']


def trackerhash(t):
    """Generate a 'fake' info_hash to be used with this tracker."""
    return md5(t).hexdigest()[:20]


def genqstr(h):
    pid = "-TO0001-XX" + str(int(time()))  # 'random' peer id
    return "?info_hash=%s&port=999&peer_id=%s&compact=1&uploaded=0&downloaded=0&left=0" % (h, pid)


def scrape_udp(udp_version):
    thash = trackerhash(udp_version)
    parsed_tracker = urlparse(udp_version)
    print "Scraping UDP: %s " % udp_version
    transaction_id = "\x00\x00\x04\x12\x27\x10\x19\x70";
    connection_id = "\x00\x00\x04\x17\x27\x10\x19\x80";
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10)
    try:
        conn = (socket.gethostbyname(parsed_tracker.hostname), parsed_tracker.port)
    except socket.error:
        raise RuntimeError("Can't resolve DNS")

    # Get connection ID
    req, transaction_id = udp_create_connection_request()
    sock.sendto(req, conn)
    try:
        buf = sock.recvfrom(2048)[0]
    except socket.timeout:
        raise RuntimeError("UDP timeout")
    connection_id = udp_parse_connection_response(buf, transaction_id)

    # Scrape away
    req, transaction_id = udp_create_announce_request(connection_id, thash)
    sock.sendto(req, conn)
    try:
        buf = sock.recvfrom(2048)[0]
    except socket.timeout:
        raise RuntimeError("UDP timeout")
    return udp_parse_announce_response(buf, transaction_id)


def udp_create_connection_request():
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

    res_transaction_id = struct.unpack_from("!i", buf, 4)[0]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError("Transaction ID doesnt match in connection response! Expected %s, got %s"
                           % (sent_transaction_id, res_transaction_id))

    if action == 0x0:
        connection_id = struct.unpack_from("!q", buf, 8)[0]  # unpack 8 bytes from byte 8, should be the connection_id
        return connection_id
    elif action == 0x3:
        error = struct.unpack_from("!s", buf, 8)
        raise RuntimeError("Error while trying to get a connection response: %s" % error)
    pass


def udp_create_announce_request(connection_id, thash):
    action = 0x1  # action (1 = announce)
    transaction_id = udp_get_transaction_id()
    buf = struct.pack("!q", connection_id)  # first 8 bytes is connection id
    buf += struct.pack("!i", action)  # next 4 bytes is action
    buf += struct.pack("!i", transaction_id)  # followed by 4 byte transaction id
    hex_repr = binascii.a2b_hex(thash)
    buf += struct.pack("!20s", hex_repr)  # hash
    buf += struct.pack("!20s", hex_repr)  # peer id, should be random
    buf += struct.pack("!q", 0x0)  # number of bytes downloaded
    buf += struct.pack("!q", 0x0)  # number of bytes left
    buf += struct.pack("!q", 0x0)  # number of bytes uploaded
    buf += struct.pack("!i", 0x2)  # event 0 denotes start of downloading
    buf += struct.pack("!i", 0x0)  # IP address set to 0. Response received to the sender of this packet
    key = udp_get_transaction_id()  # Unique key randomized by client
    buf += struct.pack("!i", key)
    buf += struct.pack("!i", -1)  # Number of peers required. Set to -1 for default
    buf += struct.pack("!i", 0x3E7)  # port on which response will be sent
    return buf, transaction_id


def udp_parse_announce_response(buf, sent_transaction_id):
    if len(buf) < 20:
        raise RuntimeError("Wrong response length while announcing: %s" % len(buf))
    action = struct.unpack_from("!i", buf)[0]  # first 4 bytes is action
    res_transaction_id = struct.unpack_from("!i", buf, 4)[0]  # next 4 bytes is transaction id
    if res_transaction_id != sent_transaction_id:
        raise RuntimeError("Transaction ID doesnt match in announce response! Expected %s, got %s"
                           % (sent_transaction_id, res_transaction_id))
    if action == 0x1:
        ret = dict()
        offset = 8;  # next 4 bytes after action is transaction_id, so data doesnt start till byte 8
        ret['interval'] = struct.unpack_from("!i", buf, offset)[0]
        print "Interval:" + str(ret['interval'])
        offset += 4
        ret['leeches'] = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        ret['seeds'] = struct.unpack_from("!i", buf, offset)[0]
        offset += 4
        peers = list()
        x = 0
        while offset != len(buf):
            peers.append(dict())
            peers[x]['IP'] = struct.unpack_from("!i", buf, offset)[0]
            # print "IP: "+socket.inet_ntoa(struct.pack("!i",peers[x]['IP']))
            offset += 4
            if offset >= len(buf):
                raise RuntimeError("Error while reading peer port")
            peers[x]['port'] = struct.unpack_from("!H", buf, offset)[0]
            offset += 2
            x += 1
        return ret['interval']
    else:
        # an error occured, try and extract the error string
        error = struct.unpack_from("!s", buf, 8)
        raise RuntimeError("Error while annoucing: %s" % error)


def udp_get_transaction_id():
    return int(random.randrange(0, 255))
