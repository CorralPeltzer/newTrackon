import json
import logging
import os.path as path
import pickle
import sqlite3
import sys
from collections import deque
from ipaddress import ip_address, IPv4Address
from threading import Lock
from time import time, sleep
from urllib.parse import urlparse

from newTrackon.tracker import Tracker

max_input_length = 20000
submitted_trackers = deque(maxlen=10000)
db_file = "data/trackon.db"
raw_history_file = "data/raw_data.pickle"
submitted_history_file = "data/submitted_data.pickle"

if path.exists(raw_history_file):
    raw_data = pickle.load(open(raw_history_file, "rb"))
else:
    raw_data = deque(maxlen=600)
if path.exists(submitted_history_file):
    submitted_data = pickle.load(open(submitted_history_file, "rb"))
else:
    submitted_data = deque(maxlen=600)

deque_lock = Lock()
list_lock = Lock()
processing_trackers = False

logger = logging.getLogger("newtrackon_logger")


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_all_data_from_db():
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


def process_uptime_and_downtime_time(trackers_unprocessed):
    for tracker in trackers_unprocessed:
        if tracker.status == 1:
            tracker.status_epoch = tracker.last_downtime
            if not tracker.last_downtime:
                tracker.status_readable = "Working"
            else:
                time_string = calculate_time_ago(tracker.last_downtime)
                tracker.status_readable = "Working for " + time_string
        elif tracker.status == 0:
            tracker.status_epoch = sys.maxsize
            if not tracker.last_uptime:
                tracker.status_readable = "Down"
            else:
                time_string = calculate_time_ago(tracker.last_uptime)
                tracker.status_readable = "Down for " + time_string

    return trackers_unprocessed


def calculate_time_ago(last_time):
    now = int(time())
    relative = now - int(last_time)
    if relative < 60:
        if relative == 1:
            return str(int(round(relative))) + " second"
        else:
            return str(int(round(relative))) + " seconds"
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


def enqueue_new_trackers(input_string):
    input_string = input_string.lower()
    if len(input_string) > max_input_length:
        return
    new_trackers_list = input_string.split()
    for url in new_trackers_list:
        logger.info(f"Tracker {url} submitted to the queue")
        add_one_tracker_to_submitted_deque(url)
    if processing_trackers is False:
        process_submitted_deque()


def add_one_tracker_to_submitted_deque(url):
    try:
        ip_address(urlparse(url).hostname)
        logger.info(f"Tracker {url} denied, hostname is IP")
        return
    except ValueError:
        pass
    with deque_lock:
        for tracker_in_deque in submitted_trackers:
            if urlparse(tracker_in_deque.url).netloc == urlparse(url).netloc:
                logger.info(f"Tracker {url} denied, already in the queue")
                return
    with list_lock:
        for tracker in get_all_data_from_db():
            if tracker.host == urlparse(url).hostname:
                logger.info(f"Tracker {url} denied, already being tracked")
                return
    try:
        tracker_candidate = Tracker.from_url(url)
    except (RuntimeError, ValueError) as e:
        logger.info(f"Tracker {url} preprocessing failed, reason: {str(e)}")
        return
    all_ips_tracked = get_all_ips_tracked()
    exists_ip = set(tracker_candidate.ip).intersection(all_ips_tracked)
    if exists_ip:
        logger.info(f"Tracker {url} denied, IP of the tracker is already in the list")
        return
    with deque_lock:
        submitted_trackers.append(tracker_candidate)
    logger.info(f"Tracker {url} added to the submitted queue")


def process_submitted_deque():
    global processing_trackers
    processing_trackers = True
    while submitted_trackers:
        with deque_lock:
            tracker = submitted_trackers.popleft()
        logger.info(f"Size of queue: {len(submitted_trackers)}")
        process_new_tracker(tracker)
        pickle.dump(submitted_data, open(submitted_history_file, "wb"))
    logger.info("Finished processing new trackers")
    processing_trackers = False


def process_new_tracker(tracker_candidate):
    logger.info(f"Processing new tracker: {tracker_candidate.url}")
    all_ips_tracked = get_all_ips_tracked()
    exists_ip = set(tracker_candidate.ip).intersection(all_ips_tracked)
    if exists_ip:
        logger.info(
            f"Tracker {tracker_candidate.url} denied, IP of the tracker is already in the list"
        )
        return
    with list_lock:
        for tracker in get_all_data_from_db():
            if tracker.host == urlparse(tracker_candidate.url).hostname:
                logger.info(
                    f"Tracker {tracker_candidate.url} denied, already being tracked"
                )
                return

    tracker_candidate.last_downtime = int(time())
    tracker_candidate.last_checked = int(time())
    try:
        tracker_candidate.latency, tracker_candidate.interval, tracker_candidate.url = (
            tracker_candidate.scrape()
        )
    except (RuntimeError, ValueError):
        return
    if (
        300 > tracker_candidate.interval or tracker_candidate.interval > 10800
    ):  # trackers with an update interval
        # less than 5' and more than 3h
        debug = submitted_data.popleft()
        info = debug["info"]
        debug.update(
            {
                "status": 0,
                "info": info
                + "<br>Tracker rejected for having an interval shorter than 5 minutes or longer than 3 hours",
            }
        )
        submitted_data.appendleft(debug)
        return
    tracker_candidate.update_ipapi_data()
    tracker_candidate.is_up()
    tracker_candidate.update_uptime()
    insert_in_db(tracker_candidate)
    logger.info(f"New tracker {tracker_candidate.url} added to newTrackon")


def update_outdated_trackers():
    while True:
        now = int(time())
        trackers_outdated = []
        for tracker in get_all_data_from_db():
            if (now - tracker.last_checked) > tracker.interval:
                trackers_outdated.append(tracker)
        for tracker in trackers_outdated:
            logger.info(f"Updating {tracker.url}")
            tracker.update_status()
            pickle.dump(raw_data, open(raw_history_file, "wb"))
        detect_new_ip_duplicates()
        sleep(5)


def detect_new_ip_duplicates():
    all_ips = get_all_ips_tracked()
    non_duplicates = set()
    for ip in all_ips:
        if ip not in non_duplicates:
            non_duplicates.add(ip)
        else:
            logger.info(f"IP {ip} is duplicated, manual action required")


def insert_in_db(tracker):
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


def update_in_db(tracker):
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


def get_all_ips_tracked():
    all_ips_of_all_trackers = []
    all_data = get_all_data_from_db()
    for tracker_in_list in all_data:
        if tracker_in_list.ip:
            for ip in tracker_in_list.ip:
                all_ips_of_all_trackers.append(ip)
    return all_ips_of_all_trackers


def api_general(query, uptime=0, include_ipv6_only=True):
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


def remove_ipv6_only_trackers(raw_list):
    cleaned_list = []
    for url, ips_list in raw_list:
        ips_list = json.loads(ips_list)
        if ips_list:
            ips_built = [ip_address(ip) for ip in ips_list]
            if any(isinstance(one_ip, IPv4Address) for one_ip in ips_built):
                cleaned_list.append((url, ips_list))
    return cleaned_list


def format_list(raw_list):
    formatted_list = ""
    for url in raw_list:
        url_string = url[0]
        formatted_list += url_string + "\n" + "\n"
    return formatted_list
