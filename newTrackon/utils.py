import sqlite3
import sys
from collections.abc import Sequence
from ipaddress import IPv4Address, IPv6Address, ip_address
from time import time
from typing import TYPE_CHECKING
from urllib.parse import ParseResult

from flask import Response

if TYPE_CHECKING:
    from newTrackon.tracker import Tracker

# Type alias for BEP34 protocol preferences: (protocol, port)
ProtocolPref = tuple[str, int]

# Type alias for tracker URL with its IP addresses
TrackerEndpoint = tuple[str, list[str]]


def add_api_headers(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.mimetype = "text/plain"
    return resp


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict[str, object]:
    d: dict[str, object] = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def format_uptime_and_downtime_time(trackers_unprocessed: list[Tracker]) -> list[Tracker]:
    for tracker in trackers_unprocessed:
        if tracker.status == 1:
            tracker.status_epoch = tracker.last_downtime
            if not tracker.last_downtime:
                tracker.status_readable = "Working"
            else:
                time_string = format_time(tracker.last_downtime)
                tracker.status_readable = "Working for " + time_string
        elif tracker.status == 0:
            tracker.status_epoch = sys.maxsize
            if not tracker.last_uptime:
                tracker.status_readable = "Down"
            else:
                time_string = format_time(tracker.last_uptime)
                tracker.status_readable = "Down for " + time_string

    return trackers_unprocessed


def format_time(last_time: int | float) -> str:
    now = int(time())
    relative = now - int(last_time)
    if relative < 60:
        if relative == 1:
            return str(round(relative)) + " second"
        else:
            return str(round(relative)) + " seconds"
    minutes = round(relative / 60)
    if minutes < 60:
        if minutes == 1:
            return str(minutes) + " minute"
        else:
            return str(minutes) + " minutes"
    hours = round(relative / 3600)
    if hours < 24:
        if hours == 1:
            return str(hours) + " hour"
        else:
            return str(hours) + " hours"
    days = round(relative / 86400)
    if days < 31:
        if days == 1:
            return str(days) + " day"
        else:
            return str(days) + " days"
    months = round(relative / 2592000)
    if months < 12:
        if months == 1:
            return str(months) + " month"
        else:
            return str(months) + " months"
    years = round(relative / 31536000)
    if years == 1:
        return str(years) + " year"
    else:
        return str(years) + " years"


def remove_ipvx_only_trackers(raw_list: list[TrackerEndpoint], version: int) -> list[TrackerEndpoint]:
    ip_type_to_keep: type[IPv4Address | IPv6Address]
    if version == 6:
        ip_type_to_keep = IPv4Address
    else:
        ip_type_to_keep = IPv6Address
    cleaned_list: list[TrackerEndpoint] = []
    for url, ips_list in raw_list:
        if ips_list:
            ips_parsed = [ip_address(ip) for ip in ips_list]
            if any(isinstance(ip, ip_type_to_keep) for ip in ips_parsed):
                cleaned_list.append((url, ips_list))
    return cleaned_list


def format_list(raw_list: Sequence[TrackerEndpoint]) -> str:
    formatted_list = ""
    for url in raw_list:
        url_string = url[0]
        formatted_list += url_string + "\n" + "\n"
    return formatted_list


def process_txt_prefs(txt_record: str) -> list[ProtocolPref]:
    words = txt_record.split()
    txt_preferences: list[ProtocolPref] = []
    for word in words[1:11]:  # Get only the first 10 advertised trackers to avoid DoS
        if word.startswith("UDP:") and word[4:].isdigit():
            txt_preferences.append(("udp", int(word[4:])))
        elif word.startswith("TCP:") and word[4:].isdigit():
            txt_preferences.append(("tcp", int(word[4:])))
    return txt_preferences


def build_httpx_url(submitted_url: ParseResult, tls: bool) -> str:
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
