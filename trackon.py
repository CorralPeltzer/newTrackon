
import logging
import sqlite3
from copy import deepcopy

from threading import Lock
from collections import deque
from itertools import islice
from time import time, sleep
from urllib.parse import urlparse

import scraper
from tracker import Tracker

max_input_length = 20000
incoming_trackers = deque(maxlen=10000)
deque_lock = Lock()
list_lock = Lock()

processing_trackers = False
logger = logging.getLogger('trackon_logger')


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# When the program is started, create all tracker objects from sqlite table
conn = sqlite3.connect('trackon.db')
conn.row_factory = dict_factory
c = conn.cursor()
trackers_list = []
for row in c.execute("SELECT * FROM STATUS ORDER BY uptime DESC"):
    tracker_in_db = Tracker(url=row['url'],
                            host=row['host'],
                            ip=eval(row['ip']),
                            latency=row['latency'],
                            last_checked=row['last_checked'],
                            interval=row['interval'],
                            status=row['status'],
                            uptime=row['uptime'],
                            country=eval(row['country']),
                            historic=eval(row['historic']),
                            added=row['added'],
                            network=eval(row['network']))
    trackers_list.append(tracker_in_db)
#closing database cursor?


def enqueue_new_trackers(input_string):
    if len(input_string) > max_input_length:
        return
    new_trackers_list = input_string.split()
    for url in new_trackers_list:
        enqueue_one_tracker(url)
    if processing_trackers is False:
        process_new_trackers()


def enqueue_one_tracker(url):
    with deque_lock:
        for tracker_in_deque in incoming_trackers:
            if urlparse(tracker_in_deque.url).netloc == urlparse(url).netloc:
                print("Tracker already in the queue.")
                return
    with list_lock:
        for tracker_in_list in trackers_list:
            if tracker_in_list.host == urlparse(url).hostname:
                print("Tracker already being tracked.")
                return
    try:
        tracker_candidate = Tracker.from_url(url)
    except (RuntimeError, ValueError) as e:
        print(e)
        return
    all_ips_tracked = get_all_ips_tracked()
    exists_ip = set(tracker_candidate.ip).intersection(all_ips_tracked)
    if exists_ip:
        print("IP of the tracker already in the list.")
        return
    with deque_lock:
        incoming_trackers.append(tracker_candidate)
    print("Tracker added to the incoming queue")


def process_new_trackers():
    global processing_trackers
    processing_trackers = True
    while incoming_trackers:
        with deque_lock:
            tracker = incoming_trackers.popleft()
        print("Size of deque: ", len(incoming_trackers))
        process_new_tracker(tracker)
    print("Finished processing  new trackers")
    processing_trackers = False


def get_main():
    with list_lock:
        html_list = deepcopy(trackers_list)
    for tracker in html_list:
        string = ''
        for ip in tracker.ip:
            string += ip + '<br/>'
        tracker.ip = string

        string = ''
        for country in tracker.country:
            string += country + '<br/>'
        tracker.country = string

        string = ''
        for network in tracker.network:
            string += network + '<br/>'
        tracker.network = string
    return html_list


def process_new_tracker(tracker_candidate):
    print('---------------------------------------------------------------')
    print('New tracker: ' + tracker_candidate.url)

    all_ips_tracked = get_all_ips_tracked()
    exists_ip = set(tracker_candidate.ip).intersection(all_ips_tracked)
    if exists_ip:
        print("IP of the tracker already in the list.")
        return

    with list_lock:
        for tracker_in_list in trackers_list:
            if tracker_in_list.host == urlparse(tracker_candidate.url).hostname:
                print("Tracker already being tracked.")
                return

    logger.info('Contact new tracker ' + tracker_candidate.url)
    tracker_candidate.last_checked = int(time())
    try:
        tracker_candidate.latency, tracker_candidate.interval, tracker_candidate.url = tracker_candidate.scrape()
    except (RuntimeError, ValueError):
        return
    tracker_candidate.update_ipapi_data()
    tracker_candidate.is_up()
    tracker_candidate.update_uptime()
    print('Adding tracker to list')
    with list_lock:
        trackers_list.append(tracker_candidate)
    insert_in_db(tracker_candidate)
    logger.info('TRACKER ADDED TO LIST: ' + tracker_candidate.url)
    return


def update_status():
    while True:
        print("UPDATE STATUS LOOP")
        now = int(time())
        trackers_outdated = []
        with list_lock:
            for tracker in trackers_list:
                if (now - tracker.last_checked) > tracker.interval:
                    trackers_outdated.append(tracker)
        for tracker in trackers_outdated:
            tracker.update_status()
        print("Finished updating tracker status")
        sleep(10)


def get_150_incoming():
    string = ''
    if incoming_trackers:
        with deque_lock:
            for tracker in islice(incoming_trackers, 150):
                string += tracker.url + '<br>'
        return len(incoming_trackers), string
    else:
        return 0, "None"


def insert_in_db(tracker):
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute('INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
              (tracker.url, tracker.host, str(tracker.ip), tracker.latency, tracker.last_checked, tracker.interval,
               tracker.status, tracker.uptime, str(tracker.country), str(tracker.historic), tracker.added,
               str(tracker.network)))
    conn.commit()
    conn.close()


def update_db(tracker):
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute(
        "UPDATE status SET ip=?, latency=?, last_checked=?, status=?, interval=?, uptime=?,"
        " historic=?, country=?, network=? WHERE url=?",
        (str(tracker.ip), tracker.latency, tracker.last_checked, tracker.status, tracker.interval, tracker.uptime,
         str(tracker.historic), str(tracker.country), str(tracker.network), tracker.url)).fetchone()
    conn.commit()
    conn.close()


def get_all_ips_tracked():
    all_ips_of_all_trackers = []
    with list_lock:
        for tracker_in_list in trackers_list:
            for ip in tracker_in_list.ip:
                all_ips_of_all_trackers.append(ip)
    return all_ips_of_all_trackers
