import logging
from time import sleep, time
from typing import NoReturn

from newTrackon import db
from newTrackon.persistence import (
    raw_data,
    raw_history_file,
    save_deque_to_disk,
)
from newTrackon.tracker import Tracker

logger: logging.Logger = logging.getLogger("newtrackon")


def build_ip_indexes(trackers: list[Tracker]) -> tuple[list[str], dict[str, set[str]]]:
    all_ips_of_all_trackers: list[str] = []
    recent_index: dict[str, set[str]] = {}
    for tracker_in_list in trackers:
        if tracker_in_list.recent_ips:
            recent_ips = tracker_in_list.recent_ips.keys()
            all_ips_of_all_trackers.extend(recent_ips)
            for ip in recent_ips:
                recent_index.setdefault(ip, set()).add(tracker_in_list.host)
        elif tracker_in_list.ips:
            all_ips_of_all_trackers.extend(tracker_in_list.ips)
    return all_ips_of_all_trackers, recent_index


def update_outdated_trackers() -> NoReturn:
    while True:
        now = int(time())
        trackers_all = db.get_all_data()
        trackers_outdated: list[Tracker] = []
        for tracker in trackers_all:
            if (now - tracker.last_checked) > tracker.interval:
                trackers_outdated.append(tracker)
        for tracker in trackers_outdated:
            logger.info("Updating %s", tracker.url)
            tracker.update_status()

            if tracker.to_be_deleted:
                logger.info("Removing %s", tracker.url)
                db.delete_tracker(tracker)
                trackers_all.remove(tracker)
            else:
                db.update_tracker(tracker)
            save_deque_to_disk(raw_data, raw_history_file)
        sleep(5)


def warn_of_duplicate_ips(all_ips: list[str]) -> None:
    if all_ips:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for ip in all_ips:
            if ip not in seen:
                seen.add(ip)
            else:
                duplicates.add(ip)
        for duplicate_ip in duplicates:
            logger.warning("IP %s is duplicated, manual action required", duplicate_ip)


def warn_of_recent_ip_overlaps(trackers: list[Tracker], recent_index: dict[str, set[str]]) -> None:
    if not trackers:
        return
    if not recent_index:
        return
    warned: set[tuple[str, str, str]] = set()
    for tracker in trackers:
        if not tracker.ips:
            continue
        for ip in tracker.ips:
            other_hosts = recent_index.get(ip, set()) - {tracker.host}
            if not other_hosts:
                continue
            other_hosts_str = ", ".join(sorted(other_hosts))
            key = (tracker.host, ip, other_hosts_str)
            if key in warned:
                continue
            warned.add(key)
            logger.warning(
                "Tracker %s resolved to IP %s recently seen on %s",
                tracker.host,
                ip,
                other_hosts_str,
            )


def warn_of_ip_conflicts() -> None:
    trackers = db.get_all_data()
    all_ips, recent_index = build_ip_indexes(trackers)
    warn_of_duplicate_ips(all_ips)
    warn_of_recent_ip_overlaps(trackers, recent_index)


def warn_of_ip_conflicts_periodically() -> NoReturn:
    while True:
        warn_of_ip_conflicts()
        sleep(120)
