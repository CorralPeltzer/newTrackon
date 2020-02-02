import json
import sqlite3
from collections import deque
from os import path

from newTrackon.tracker import Tracker
from newTrackon.utils import dict_factory, remove_ipv6_only_trackers, format_list

db_file = "data/trackon.db"


def ensure_db_existence():
    if not path.exists(db_file):
        create_db()


def create_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE `status` (
        `url`	TEXT NOT NULL,
        `host`	TEXT NOT NULL,
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
        PRIMARY KEY(`url`)
        );""")
    conn.commit()
    conn.close()


def update_tracker(tracker):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        "UPDATE status SET ip=?, latency=?, last_checked=?, status=?, interval=?, uptime=?,"
        " historic=?, country=?, country_code=?, network=?, last_downtime=?, last_uptime=? WHERE url=?",
        (
            json.dumps(tracker.ip),
            tracker.latency,
            tracker.last_checked,
            tracker.status,
            tracker.interval,
            tracker.uptime,
            json.dumps(list(tracker.historic)),
            json.dumps(tracker.country),
            json.dumps(tracker.country_code),
            json.dumps(tracker.network),
            tracker.last_downtime,
            tracker.last_uptime,
            tracker.url,
        ),
    ).fetchone()
    conn.commit()
    conn.close()


def get_all_data():
    conn = sqlite3.connect(db_file)
    conn.row_factory = dict_factory
    c = conn.cursor()
    trackers_from_db = []
    for row in c.execute("SELECT * FROM STATUS ORDER BY uptime DESC"):
        tracker_in_db = Tracker(
            url=row.get("url"),
            host=row.get("host"),
            ip=json.loads(row.get("ip")),
            latency=row.get("latency"),
            last_checked=row.get("last_checked"),
            interval=row.get("interval"),
            status=row.get("status"),
            uptime=row.get("uptime"),
            country=json.loads(row.get("country")),
            country_code=json.loads(row.get("country_code")),
            historic=deque(json.loads((row.get("historic"))), maxlen=1000),
            added=row.get("added"),
            network=json.loads(row.get("network")),
            last_downtime=row.get("last_downtime"),
            last_uptime=row.get("last_uptime"),
        )
        trackers_from_db.append(tracker_in_db)
    conn.close()
    return trackers_from_db


def get_api_data(query, uptime=0, include_ipv6_only=True):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    if query == "/api/http":
        c.execute(
            'SELECT URL, IP FROM STATUS WHERE URL LIKE "http%" AND UPTIME >= 95 ORDER BY UPTIME DESC'
        )
    elif query == "/api/udp":
        c.execute(
            'SELECT URL, IP FROM STATUS WHERE URL LIKE "udp://%" AND UPTIME >= 95 ORDER BY UPTIME DESC'
        )
    elif query == "/api/live":
        c.execute("SELECT URL, IP FROM STATUS WHERE STATUS = 1 ORDER BY UPTIME DESC")
    elif query == "percentage":
        c.execute(
            "SELECT URL, IP FROM STATUS WHERE UPTIME >= ? ORDER BY UPTIME DESC",
            (uptime,),
        )
    raw_list = c.fetchall()
    conn.close()

    if not include_ipv6_only:
        raw_list = remove_ipv6_only_trackers(raw_list)

    return format_list(raw_list)


def insert_new_tracker(tracker):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute(
        "INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            tracker.url,
            tracker.host,
            json.dumps(tracker.ip),
            tracker.latency,
            tracker.last_checked,
            tracker.interval,
            tracker.status,
            tracker.uptime,
            json.dumps(tracker.country),
            json.dumps(tracker.country_code),
            json.dumps(tracker.network),
            tracker.added,
            json.dumps(list(tracker.historic)),
            tracker.last_downtime,
            tracker.last_uptime,
        ),
    )
    conn.commit()
    conn.close()
