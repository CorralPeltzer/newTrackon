import os.path as path
import logging
import sqlite3
import pickle
from collections import deque
from ipaddress import ip_address
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
        tracker_in_db = Tracker(url=row.get('url'),
                                host=row.get('host'),
                                ip=eval(row.get('ip')),
                                latency=row.get('latency'),
                                last_checked=row.get('last_checked'),
                                interval=row.get('interval'),
                                status=row.get('status'),
                                uptime=row.get('uptime'),
                                country=eval(row.get('country')),
                                country_code=eval(row.get('country_code')),
                                historic=eval(row.get('historic')),
                                added=row.get('added'),
                                network=eval(row.get('network')),
                                last_downtime=row.get('last_downtime'),
                                last_uptime=row.get('last_uptime'))
        trackers_from_db.append(tracker_in_db)
    conn.close()
    return trackers_from_db


def process_uptime_and_downtime_time(trackers_unprocessed):
    for tracker in trackers_unprocessed:
        if tracker.status == 1:
            if not tracker.last_downtime:
                tracker.status_string = "Working"
            else:
                time_string = calculate_time_ago(tracker.last_downtime)
                tracker.status_string = "Working for " + time_string
        elif tracker.status == 0:
            if not tracker.last_uptime:
                tracker.status_string = "Down"
            else:
                time_string = calculate_time_ago(tracker.last_uptime)
                tracker.status_string = "Down for " + time_string
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
        debug = submitted_data.popleft()
        info = debug['info']
        debug.update({'status': 0,
                 'info': info + '<br>Tracker rejected for having an interval shorter than 5 minutes or longer than 3 hours'})
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
        detect_new_ip_duplicates()
        sleep(5)


def detect_new_ip_duplicates():
    all_ips = get_all_ips_tracked()
    non_duplicates = set()
    for ip in all_ips:
        if ip not in non_duplicates:
            non_duplicates.add(ip)
        else:
            logger.info('IP' + ip + 'is duplicated, manual action required')
            print("IP DUPLICATED: " + ip)


def insert_in_db(tracker):
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute('INSERT INTO status VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (tracker.url, tracker.host, str(tracker.ip), tracker.latency, tracker.last_checked, tracker.interval,
               tracker.status, tracker.uptime, str(tracker.country), str(tracker.country_code), str(tracker.network),
               tracker.added, str(tracker.historic), tracker.last_downtime, tracker.last_uptime,))
    conn.commit()
    conn.close()


def update_in_db(tracker):
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute(
        "UPDATE status SET ip=?, latency=?, last_checked=?, status=?, interval=?, uptime=?,"
        " historic=?, country=?, country_code=?, network=?, last_downtime=?, last_uptime=? WHERE url=?",
        (str(tracker.ip), tracker.latency, tracker.last_checked, tracker.status, tracker.interval, tracker.uptime,
         str(tracker.historic), str(tracker.country), str(tracker.country_code), str(tracker.network),
         tracker.last_downtime, tracker.last_uptime, tracker.url)).fetchone()
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
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute('SELECT URL FROM STATUS WHERE STATUS = 1 ORDER BY UPTIME DESC')
    raw_list = c.fetchall()
    conn.close()
    return format_list(raw_list)


def list_uptime(uptime):
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute('SELECT URL FROM STATUS WHERE UPTIME >= ? ORDER BY UPTIME DESC', (uptime,))
    raw_list = c.fetchall()
    conn.close()
    return format_list(raw_list), len(raw_list)


def api_udp():
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute('SELECT URL FROM STATUS WHERE URL LIKE "udp://%" AND UPTIME >= 95 ORDER BY UPTIME DESC')
    raw_list = c.fetchall()
    conn.close()
    return format_list(raw_list)


def api_http():
    conn = sqlite3.connect('trackon.db')
    c = conn.cursor()
    c.execute('SELECT URL FROM STATUS WHERE URL LIKE "http%" AND UPTIME >= 95 ORDER BY UPTIME DESC')
    raw_list = c.fetchall()
    conn.close()
    return format_list(raw_list)


def format_list(raw_list):
    formatted_list = ''
    for url in raw_list:
        url_string = url[0]
        formatted_list += url_string + '\n' + '\n'
    return formatted_list
