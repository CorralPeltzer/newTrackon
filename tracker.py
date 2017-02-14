import socket
import urllib.request, urllib.parse, urllib.error
from time import time, sleep
from urllib.parse import urlparse
import re
import scraper
import logging
import trackon
from collections import deque
from datetime import datetime
from ipaddress import ip_address

from dns import resolver
logger = logging.getLogger('trackon_logger')

class Tracker:

    def __init__(self, url, host, ip, latency, last_checked, interval, status, uptime, country, historic, added,
                 network):
        self.url = url
        self.host = host
        self.ip = ip
        self.latency = latency
        self.last_checked = last_checked
        self.interval = interval
        self.status = status
        self.uptime = uptime
        self.country = country
        self.historic = historic
        self.added = added
        self.network = network

    @classmethod
    def from_url(cls, url):
        tracker = cls(url, None, None, None, None, None, None, None, [], None, None, [])
        tracker.validate_url()
        print('URL is ', url)
        tracker.host = urlparse(tracker.url).hostname
        tracker.update_ips()
        tracker.historic = deque(maxlen=1000)
        date = datetime.now()
        tracker.added = "{}-{}-{}".format(date.day, date.month, date.year)

        return tracker

    def update_status(self):
        try:
            self.update_ips()
        except RuntimeError:
            logger.info('Hostname not found')
            return
        self.update_ipapi_data()
        print("TRACKER TO CHECK: " + self.url)
        self.last_checked = int(time())
        try:
            t1 = time()
            if urlparse(self.url).scheme == 'udp':
                self.interval = scraper.scrape_udp(self.url)
            else:
                self.interval = scraper.scrape_http(self.url)
            self.latency = int((time() - t1) * 1000)
            self.is_up()
            print("TRACKER UP")
        except RuntimeError as e:
            logger.info('Tracker down: ' + self.url + ' Cause: ' + str(e))
            print("TRACKER DOWN")
            self.is_down()
        self.update_uptime()

        trackon.update_db(self)

    def validate_url(self):
        UCHARS = re.compile('^[a-zA-Z0-9_\-\./:]+$')
        url = urlparse(self.url)
        if url.scheme not in ['udp', 'http', 'https']:
            raise RuntimeError("Tracker URLs have to start with 'udp://', 'http://' or 'https://'")
        if UCHARS.match(url.netloc) and UCHARS.match(url.path):
            url = url._replace(path='/announce')
            self.url = url.geturl()
        else:
            raise RuntimeError("Invalid announce URL")

    def update_uptime(self):
        uptime = float(0)
        for s in self.historic:
            uptime += s
        self.uptime = (uptime / len(self.historic)) * 100

    def update_ips(self):
        self.ip = []
        try:
            ip_address(self.host)
            print("ADDRESS IS IP")
            self.ip = self.host
            return
        except ValueError:
            pass
        previous_ip = self.ip
        try:
            ipv4 = resolver.query(self.host, 'A')
            for rdata in ipv4:
                self.ip.append(str(rdata))
                print(rdata)
        except Exception:
            pass
        try:
            ipv6 = resolver.query(self.host, 'AAAA')
            for rdata in ipv6:
                self.ip.append(str(rdata))
                print(rdata)
        except Exception:
            pass
        if not self.ip: # If DNS query fails, just preserve the previous IPs. Considering showing "Not found" instead.
            self.ip = previous_ip

    def update_ipapi_data(self):
        self.country = []
        self.network = []
        for ip in self.ip:
            self.country.append(self.ip_api(ip, 'country'))
            self.network.append(self.ip_api(ip, 'org'))

    def scrape(self):
        return scraper.scrape(self.url)

    def is_up(self):
        self.status = 1
        self.historic.append(self.status)

    def is_down(self):
        self.status = 0
        self.historic.append(self.status)

    @staticmethod
    def ip_api(ip, info_type):
        try:
            response = urllib.request.urlopen('http://ip-api.com/line/' + ip + '?fields=' + info_type)
            tracker_info = response.read().decode('utf-8')
            sleep(0.9)  # This wait is to respect the queries per minute limit of IP-API and not get banned
        except IOError:
            tracker_info = 'Error'
        return tracker_info
