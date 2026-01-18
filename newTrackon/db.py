import json
import sqlite3
from collections import deque
from os import path

from newTrackon.tracker import Tracker
from newTrackon.utils import dict_factory, format_list, remove_ipvx_only_trackers

db_file = "data/trackon.db"


def ensure_db_existence() -> None:
    if not path.exists(db_file):
        create_db()


def create_db() -> None:
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE `status` (
        `host`	TEXT NOT NULL,
        `url`	TEXT NOT NULL,
        `ip`	TEXT,
        `latency`	INTEGER,
        `last_checked`	INTEGER,
        `interval`	INTEGER,
        `status`	INTEGER,
        `uptime`	INTEGER,
        `country`	TEXT,
        `country_code`	TEXT,
        `network`	TEXT,
        `added`		TEXT,
        `historic`	TEXT,
        `last_downtime` INTEGER,
        `last_uptime`	INTEGER,
        PRIMARY KEY(`host`)
        );"""
    )
    conn.commit()
    conn.close()


def update_tracker(tracker: Tracker) -> None:
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        "UPDATE status SET url=?, ip=?, latency=?, last_checked=?, status=?, interval=?, uptime=?,"
        " historic=?, country=?, country_code=?, network=?, last_downtime=?, last_uptime=? WHERE host=?",
        (
            tracker.url,
            json.dumps(tracker.ips),
            tracker.latency,
            tracker.last_checked,
            tracker.status,
            tracker.interval,
            tracker.uptime,
            json.dumps(list(tracker.historic)),
            json.dumps(tracker.countries),
            json.dumps(tracker.country_codes),
            json.dumps(tracker.networks),
            tracker.last_downtime,
            tracker.last_uptime,
            tracker.host,
        ),
    ).fetchone()
    conn.commit()
    conn.close()


def delete_tracker(tracker: Tracker) -> None:
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        "DELETE FROM status WHERE host=?",
        (tracker.host,),
    ).fetchone()
    conn.commit()
    conn.close()


def get_all_data() -> list[Tracker]:
    conn = sqlite3.connect(db_file)
    conn.row_factory = dict_factory
    c = conn.cursor()
    trackers_from_db = []
    for row in c.execute("SELECT * FROM STATUS ORDER BY uptime DESC"):
        tracker_in_db = Tracker(
            host=row.get("host"),
            url=row.get("url"),
            ips=json.loads(row.get("ip")),
            latency=row.get("latency"),
            last_checked=row.get("last_checked"),
            interval=row.get("interval"),
            status=row.get("status"),
            uptime=row.get("uptime"),
            countries=json.loads(row.get("country")),
            country_codes=json.loads(row.get("country_code")),
            historic=deque(json.loads(row.get("historic")), maxlen=1000),
            added=row.get("added"),
            networks=json.loads(row.get("network")),
            last_downtime=row.get("last_downtime"),
            last_uptime=row.get("last_uptime"),
        )
        trackers_from_db.append(tracker_in_db)
    conn.close()
    return trackers_from_db


def get_api_data(query: str, uptime: int = 0, include_ipv4_only: bool = True, include_ipv6_only: bool = True) -> str:
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    if query == "/api/http":
        c.execute('SELECT URL, IP FROM STATUS WHERE URL LIKE "http%" AND UPTIME >= 95 ORDER BY UPTIME DESC')
    elif query == "/api/udp":
        c.execute('SELECT URL, IP FROM STATUS WHERE URL LIKE "udp://%" AND UPTIME >= 95 ORDER BY UPTIME DESC')
    elif query == "/api/live":
        c.execute("SELECT URL, IP FROM STATUS WHERE STATUS = 1 ORDER BY UPTIME DESC")
    elif query == "percentage":
        c.execute(
            "SELECT URL, IP FROM STATUS WHERE UPTIME >= ? ORDER BY UPTIME DESC",
            (uptime,),
        )
    urls_and_ips = c.fetchall()
    conn.close()

    urls_and_ips = [(url, json.loads(ips)) for url, ips in urls_and_ips]

    if not include_ipv4_only:
        urls_and_ips = remove_ipvx_only_trackers(urls_and_ips, version=4)

    if not include_ipv6_only:
        urls_and_ips = remove_ipvx_only_trackers(urls_and_ips, version=6)

    return format_list(urls_and_ips)


def insert_new_tracker(tracker: Tracker) -> None:
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            tracker.host,
            tracker.url,
            json.dumps(tracker.ips),
            tracker.latency,
            tracker.last_checked,
            tracker.interval,
            tracker.status,
            tracker.uptime,
            json.dumps(tracker.countries),
            json.dumps(tracker.country_codes),
            json.dumps(tracker.networks),
            tracker.added,
            json.dumps(list(tracker.historic)),
            tracker.last_downtime,
            tracker.last_uptime,
        ),
    )
    conn.commit()
    conn.close()
