import logging
from time import sleep, time
from typing import NoReturn

from newtrackon import db
from newtrackon.persistence import (
    raw_data,
    raw_history_file,
    save_deque_to_disk,
)
from newtrackon.tracker import Tracker

logger: logging.Logger = logging.getLogger("newtrackon")


def build_ip_indexes(trackers: list[Tracker]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    current_index: dict[str, set[str]] = {}
    recent_index: dict[str, set[str]] = {}
    for tracker in trackers:
        for ip in tracker.ips or []:
            current_index.setdefault(ip, set()).add(tracker.host)
        for ip in tracker.recent_ips:
            recent_index.setdefault(ip, set()).add(tracker.host)
    return current_index, recent_index


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


def warn_of_ip_conflicts() -> None:
    current_index, recent_index = build_ip_indexes(db.get_all_data())
    for ip, current_hosts in current_index.items():
        current_names = ", ".join(sorted(current_hosts))
        if len(current_hosts) > 1:
            logger.warning(
                "IP %s is currently shared by %s",
                ip,
                current_names,
            )

        historical_only_hosts = recent_index.get(ip, set()) - current_hosts
        if historical_only_hosts:
            logger.warning(
                "IP %s currently used by %s was recently seen on %s",
                ip,
                current_names,
                ", ".join(sorted(historical_only_hosts)),
            )


def warn_of_ip_conflicts_periodically() -> NoReturn:
    while True:
        warn_of_ip_conflicts()
        sleep(120)
