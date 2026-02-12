import logging
from ipaddress import ip_address
from queue import Empty, Full
from threading import Lock
from time import time
from typing import NoReturn, cast
from urllib.parse import urlparse

from newTrackon import db
from newTrackon.persistence import (
    HistoryData,
    save_deque_to_disk,
    submitted_data,
    submitted_history_file,
    submitted_queue,
)
from newTrackon.scraper import attempt_submitted
from newTrackon.tracker import Tracker

list_lock: Lock = Lock()

logger: logging.Logger = logging.getLogger("newtrackon")


def log_grouped_ip_conflicts(conflicts: dict[str, set[str]], label: str, tracker_url: str) -> None:
    grouped: dict[tuple[str, ...], list[str]] = {}
    for ip, hosts in conflicts.items():
        key = tuple(sorted(hosts))
        grouped.setdefault(key, []).append(ip)
    for hosts, ips in grouped.items():
        ips_sorted = sorted(ips)
        hosts_str = ", ".join(hosts)
        logger.info(
            "Tracker %s denied, %s IP overlap with %s, ips=%s",
            tracker_url,
            label,
            hosts_str,
            ips_sorted,
        )


def collect_ip_conflicts(tracker_candidate: Tracker, trackers: list[Tracker]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    current_conflicts: dict[str, set[str]] = {}
    recent_conflicts: dict[str, set[str]] = {}
    candidate_host = urlparse(tracker_candidate.url).hostname
    candidate_ips = tracker_candidate.ips or []

    for tracker in trackers:
        if candidate_host and tracker.host == candidate_host:
            continue
        tracker_ips = set(tracker.ips or [])
        tracker_recent_ips = set((tracker.recent_ips or {}).keys())
        for ip in candidate_ips:
            if ip in tracker_ips:
                current_conflicts.setdefault(ip, set()).add(tracker.host)
            elif ip in tracker_recent_ips:
                recent_conflicts.setdefault(ip, set()).add(tracker.host)

    return current_conflicts, recent_conflicts


def log_ip_conflicts(tracker_candidate: Tracker, trackers: list[Tracker]) -> bool:
    if not tracker_candidate.ips:
        return False
    current_conflicts, recent_conflicts = collect_ip_conflicts(tracker_candidate, trackers)
    if current_conflicts:
        log_grouped_ip_conflicts(current_conflicts, "current", tracker_candidate.url)
    if recent_conflicts:
        log_grouped_ip_conflicts(recent_conflicts, "recent", tracker_candidate.url)
    return bool(current_conflicts or recent_conflicts)


def enqueue_new_trackers(input_string: str) -> None:
    input_string = input_string.lower()
    new_trackers_list = input_string.split()
    for url in new_trackers_list:
        logger.info("Tracker %s submitted to the queue", url)
        add_one_tracker_to_submitted_queue(url)


def add_one_tracker_to_submitted_queue(url: str) -> None:
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname:
            ip_address(parsed_url.hostname)
            logger.info("Tracker %s denied, hostname is IP", url)
            return
    except ValueError:
        pass
    with submitted_queue.mutex:
        queued_trackers = cast(list[Tracker], list(submitted_queue.queue))
    for tracker_in_queue in queued_trackers:
        if urlparse(tracker_in_queue.url).netloc == urlparse(url).netloc:
            logger.info("Tracker %s denied, already in the queue", url)
            return
    with list_lock:
        trackers_in_db = db.get_all_data()
    for tracker in trackers_in_db:
        if tracker.host == urlparse(url).hostname:
            logger.info(
                "Tracker %s denied, already being tracked as %s",
                url,
                tracker.url,
            )
            return
    try:
        tracker_candidate = Tracker.from_url(url)
    except (RuntimeError, ValueError) as e:
        logger.info("Tracker %s preprocessing failed, reason: %s", url, e)
        return
    if tracker_candidate.ips and trackers_in_db:
        if log_ip_conflicts(tracker_candidate, trackers_in_db):
            return
    try:
        submitted_queue.put_nowait(tracker_candidate)
    except Full:
        logger.info("Tracker %s denied, submission queue is full", url)
        return
    logger.info("Tracker %s added to the submitted queue", url)


def process_submitted_queue() -> None:
    while True:
        try:
            tracker = submitted_queue.get_nowait()
        except Empty:
            break
        process_new_tracker(tracker)
        save_deque_to_disk(submitted_data, submitted_history_file)
        submitted_queue.task_done()


def submission_worker() -> NoReturn:
    while True:
        tracker = submitted_queue.get()
        try:
            process_new_tracker(tracker)
            save_deque_to_disk(submitted_data, submitted_history_file)
        except Exception:
            logger.exception("Unhandled error while processing submitted tracker %s", tracker.url)
        finally:
            submitted_queue.task_done()


def process_new_tracker(tracker_candidate: Tracker) -> None:
    logger.info("Processing new tracker: %s", tracker_candidate.url)
    with list_lock:
        trackers_in_db = db.get_all_data()
    for tracker in trackers_in_db:
        if tracker.host == urlparse(tracker_candidate.url).hostname:
            logger.info(
                "Tracker %s denied, already being tracked as %s",
                tracker_candidate.url,
                tracker.url,
            )
            return
    if tracker_candidate.ips and trackers_in_db:
        if log_ip_conflicts(tracker_candidate, trackers_in_db):
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
    except RuntimeError, ValueError:
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
    logger.info("New tracker %s added to newTrackon", tracker_candidate.url)


def log_wrong_interval_denial(reason: str) -> None:
    if not submitted_data:
        logger.warning("Interval rejection without submitted debug entry: %s", reason)
        return
    debug: HistoryData = submitted_data.popleft()
    info = debug["info"]
    first_info = info[0] if isinstance(info, list) and info else info if isinstance(info, str) else ""
    debug.update(
        {
            "status": 0,
            "info": [
                first_info,
                f"Tracker rejected for {reason}",
            ],
        }
    )
    submitted_data.appendleft(debug)
