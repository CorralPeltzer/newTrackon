import os.path as path
import logging
import sqlite3
import pickle
from collections import deque
from ipaddress import ip_address
from itertools import islice
from threading import Lock
from time import time, sleep
from urllib.parse import urlparse

from tracker import Tracker

max_input_length = 20000
submitted_trackers = deque(maxlen=10000)

if path.exists('raw_data.pickle'):
    raw_data = pickle.load(open('raw_data.pickle', 'rb'))
else:
    raw_data = deque(maxlen=300)
if path.exists('submitted_data.pickle'):
    submitted_data = pickle.load(open('submitted_data.pickle', 'rb'))
else:
    submitted_data = deque(maxlen=300)


deque_lock = Lock()
list_lock = Lock()
trackers_list = []
processing_trackers = False
logger = logging.getLogger('trackon_logger')


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_all_data_from_db():
    conn = sqlite3.connect('trackon.db')
    conn.row_factory = dict_factory
    c = conn.cursor()
    trackers_from_db = []
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
                                country_code=eval(row['country_code']),
                                historic=eval(row['historic']),
                                added=row['added'],
                                network=eval(row['network']))
        trackers_from_db.append(tracker_in_db)
    conn.close()
    return trackers_from_db


def enqueue_new_trackers(input_string):
    global trackers_list
    trackers_list = get_all_data_from_db()
    if len(input_string) > max_input_length:
        return
    new_trackers_list = input_string.split()
    for url in new_trackers_list:
        print("SUBMITTED " + url)
        add_one_tracker_to_submitted_deque(url)
    if processing_trackers is False:
        process_submitted_deque()


def add_one_tracker_to_submitted_deque(url):
    try:
        ip_address(urlparse(url).hostname)
        print("ADDRESS IS IP")
        return
    except ValueError:
        pass
    with deque_lock:
        for tracker_in_deque in submitted_trackers:
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
        submitted_trackers.append(tracker_candidate)
    print("Tracker added to the submitted queue")


def process_submitted_deque():
    global processing_trackers
    processing_trackers = True
    while submitted_trackers:
        with deque_lock:
            tracker = submitted_trackers.popleft()
        print("Size of deque: ", len(submitted_trackers))
        process_new_tracker(tracker)
        pickle.dump(submitted_data, open('submitted_data.pickle', 'wb'))
    print("Finished processing new trackers")
    processing_trackers = False


def process_new_tracker(tracker_candidate):
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
    if 300 > tracker_candidate.interval or tracker_candidate.interval > 10800:  # trackers with an update interval
        # less than 5' and more than 3h
        debug = {'url': tracker_candidate.url, 'time': int(time()), 'status': 0,
                 'info': 'Tracker rejected for having an interval shorter than 5 minutes or longer than 3 hours'}
        submitted_data.appendleft(debug)
        return
    tracker_candidate.update_ipapi_data()
    tracker_candidate.is_up()
    tracker_candidate.update_uptime()
    insert_in_db(tracker_candidate)
    logger.info('TRACKER ADDED TO LIST: ' + tracker_candidate.url)


def update_outdated_trackers():
    while True:
        now = int(time())
        trackers_outdated = []
        for tracker in get_all_data_from_db():
            if (now - tracker.last_checked) > tracker.interval:
                trackers_outdated.append(tracker)
        for tracker in trackers_outdated:
            print("GONNA UPDATE " + tracker.url)
            tracker.update_status()
            pickle.dump(raw_data, open('raw_data.pickle', 'wb'))
        sleep(10)


def insert_in_db(tracker):
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute('INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (tracker.url, tracker.host, str(tracker.ip), tracker.latency, tracker.last_checked, tracker.interval,
               tracker.status, tracker.uptime, str(tracker.country), str(tracker.country_code), str(tracker.network),
               tracker.added, str(tracker.historic)))
    conn.commit()
    conn.close()


def update_in_db(tracker):
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute(
        "UPDATE status SET ip=?, latency=?, last_checked=?, status=?, interval=?, uptime=?,"
        " historic=?, country=?, country_code=?, network=? WHERE url=?",
        (str(tracker.ip), tracker.latency, tracker.last_checked, tracker.status, tracker.interval, tracker.uptime,
         str(tracker.historic), str(tracker.country), str(tracker.country_code), str(tracker.network),
         tracker.url)).fetchone()
    conn.commit()
    conn.close()


def get_all_ips_tracked():
    all_ips_of_all_trackers = []
    all_data = get_all_data_from_db()
    for tracker_in_list in all_data:
        for ip in tracker_in_list.ip:
            all_ips_of_all_trackers.append(ip)
    return all_ips_of_all_trackers


def list_live():
    all_data = get_all_data_from_db()
    raw_list = []
    for t in all_data:
        if t.status == 1:
            raw_list.append(t.url)
    return format_list(raw_list)


def list_uptime(uptime):
    all_data = get_all_data_from_db()
    raw_list = []
    length = 0
    for t in all_data:
        if t.uptime >= uptime:
            raw_list.append(t.url)
            length += 1
    return format_list(raw_list), length


def list_udp():
    all_data = get_all_data_from_db()
    raw_list = []
    for t in all_data:
        if urlparse(t.url).scheme == 'udp' and t.uptime >= 95:
            raw_list.append(t.url)
    return format_list(raw_list)


def list_http():
    all_data = get_all_data_from_db()
    raw_list = []
    for t in all_data:
        if urlparse(t.url).scheme in ['http', 'https'] and t.uptime >= 95:
            raw_list.append(t.url)
    return format_list(raw_list)


def format_list(raw_list):
    formatted_list = ''
    for url in raw_list:
        formatted_list += url + '\n' + '\n'
    return formatted_list
