import logging
from ipaddress import ip_address
from time import time, sleep
from urllib.parse import urlparse
from threading import Lock
from newTrackon.tracker import Tracker
from newTrackon.scraper import attempt_submitted
from newTrackon import db
from newTrackon.persistence import (
    submitted_history_file,
    save_deque_to_disk,
    raw_data,
    raw_history_file,
    submitted_trackers,
    submitted_data,
)

processing_trackers = False
deque_lock = Lock()
list_lock = Lock()

logger = logging.getLogger("newtrackon")


def enqueue_new_trackers(input_string: str):
    if not isinstance(input_string, str):
        return
    input_string = input_string.lower()
    new_trackers_list = input_string.split()
    for url in new_trackers_list:
        logger.info(f"Tracker {url} submitted to the queue")
        add_one_tracker_to_submitted_deque(url)
    if processing_trackers is False:
        process_submitted_deque()


def add_one_tracker_to_submitted_deque(url: str):
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname:
            ip_address(parsed_url.hostname)
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
        for tracker in db.get_all_data():
            if tracker.host == urlparse(url).hostname:
                logger.info(f"Tracker {url} denied, already being tracked")
                return
    try:
        tracker_candidate = Tracker.from_url(url)
    except (RuntimeError, ValueError) as e:
        logger.info(f"Tracker {url} preprocessing failed, reason: {str(e)}")
        return
    all_ips_tracked = get_all_ips_tracked()
    if tracker_candidate.ips and all_ips_tracked:
        exists_ip = set(tracker_candidate.ips).intersection(all_ips_tracked)
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
        save_deque_to_disk(submitted_data, submitted_history_file)
    logger.info("Finished processing new trackers")
    processing_trackers = False


def process_new_tracker(tracker_candidate: Tracker):
    logger.info(f"Processing new tracker: {tracker_candidate.url}")
    all_ips_tracked = get_all_ips_tracked()
    if tracker_candidate.ips and all_ips_tracked:
        exists_ip = set(tracker_candidate.ips).intersection(all_ips_tracked)
        if exists_ip:
            logger.info(f"Tracker {tracker_candidate.url} denied, IP of the tracker is already in the list")
            return
        with list_lock:
            for tracker in db.get_all_data():
                if tracker.host == urlparse(tracker_candidate.url).hostname:
                    logger.info(f"Tracker {tracker_candidate.url} denied, already being tracked")
                    return

    tracker_candidate.last_downtime = int(time())
    tracker_candidate.last_checked = int(time())
    try:
        attempt_results = attempt_submitted(tracker_candidate)
        if attempt_results:
            (
                tracker_candidate.interval,
                tracker_candidate.url,
                tracker_candidate.latency,
            ) = attempt_results
    except (RuntimeError, ValueError):
        return
    if not tracker_candidate.interval:
        log_wrong_interval_denial("missing interval field")
        return
    if 300 > tracker_candidate.interval or tracker_candidate.interval > 10800:  # trackers with an update interval
        # less than 5' and more than 3h
        log_wrong_interval_denial(reason="having an interval shorter than 5 minutes or longer than 3 hours")
        return
    tracker_candidate.update_ipapi_data()
    tracker_candidate.is_up()
    tracker_candidate.update_uptime()
    db.insert_new_tracker(tracker_candidate)
    logger.info(f"New tracker {tracker_candidate.url} added to newTrackon")


def update_outdated_trackers():
    while True:
        now = int(time())
        trackers_outdated: list[Tracker] = []
        for tracker in db.get_all_data():
            if (now - tracker.last_checked) > tracker.interval:
                trackers_outdated.append(tracker)
        for tracker in trackers_outdated:
            logger.info(f"Updating {tracker.url}")
            tracker.update_status()

            if tracker.to_be_deleted:
                logger.info(f"Removing {tracker.url}")
                db.delete_tracker(tracker)
            else:
                db.update_tracker(tracker)
            save_deque_to_disk(raw_data, raw_history_file)
        warn_of_duplicate_ips()
        sleep(5)


def log_wrong_interval_denial(reason):
    debug = submitted_data.popleft()
    info = debug["info"]
    debug.update(
        {
            "status": 0,
            "info": [
                info[0],
                f"Tracker rejected for {reason}",
            ],
        }
    )
    submitted_data.appendleft(debug)


def warn_of_duplicate_ips():
    all_ips = get_all_ips_tracked()
    if all_ips:
        seen, duplicates = set(), set()
        for ip in all_ips:
            if ip not in seen:
                seen.add(ip)
            else:
                duplicates.add(ip)
        for duplicate_ip in duplicates:
            logger.warning(f"IP {duplicate_ip} is duplicated, manual action required")


def get_all_ips_tracked() -> list[str] | None:
    all_ips_of_all_trackers = []
    all_data = db.get_all_data()
    for tracker_in_list in all_data:
        if tracker_in_list.ips:
            for ip in tracker_in_list.ips:
                all_ips_of_all_trackers.append(ip)
    return all_ips_of_all_trackers
