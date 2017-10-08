from urllib import request, parse
from time import time, sleep, gmtime, strftime
import re
import scraper
import logging
import trackon
from collections import deque
from datetime import datetime
import pprint
from dns import resolver
logger = logging.getLogger('trackon_logger')


class Tracker:

    def __init__(self, url, host, ip, latency, last_checked, interval, status, uptime, country, country_code,
                 network, historic, added, last_downtime, last_uptime):
        self.url = url
        self.host = host
        self.ip = ip
        self.latency = latency
        self.last_checked = last_checked
        self.interval = interval
        self.status = status
        self.uptime = uptime
        self.country = country
        self.country_code = country_code
        self.network = network
        self.historic = historic
        self.added = added
        self.last_downtime = last_downtime
        self.last_uptime = last_uptime

    @classmethod
    def from_url(cls, url):
        tracker = cls(url, None, None, None, None, None, None, None, [], [], [], None, None, None, None)
        tracker.validate_url()
        print('URL is ', url)
        tracker.host = parse.urlparse(tracker.url).hostname
        tracker.update_ips()
        if not tracker.ip:
            raise RuntimeError("Can't resolve IP")
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
        self.last_checked = int(time())
        pp = pprint.PrettyPrinter(width=999999, compact=True)
        t1 = time()
        debug = {'url': self.url, 'ip': self.ip[0], 'time': strftime("%H:%M:%S UTC", gmtime(t1))}
        try:
            if parse.urlparse(self.url).scheme == 'udp':
                parsed, raw, ip = scraper.announce_udp(self.url)
                self.interval = parsed['interval']
                pretty_data = pp.pformat(parsed)
                debug['info'] = pretty_data.replace(scraper.my_ip, 'redacted')
                trackon.raw_data.appendleft(debug)
            else:
                response = scraper.announce_http(self.url)
                self.interval = response['interval']
                pretty_data = pp.pformat(response)
                debug['info'] = pretty_data.replace(scraper.my_ip, 'redacted')
                trackon.raw_data.appendleft(debug)
            self.latency = int((time() - t1) * 1000)
            self.is_up()
            debug['status'] = 1
            print("TRACKER UP")
        except RuntimeError as e:
            logger.info('Tracker down: ' + self.url + ' Cause: ' + str(e))
            debug.update({'info': str(e), 'status': 0})
            trackon.raw_data.appendleft(debug)
            print("TRACKER DOWN")
            self.is_down()
        self.update_uptime()

        trackon.update_in_db(self)

    def validate_url(self):
        uchars = re.compile('^[a-zA-Z0-9_\-\./:]+$')
        url = parse.urlparse(self.url)
        if url.scheme not in ['udp', 'http', 'https']:
            raise RuntimeError("Tracker URLs have to start with 'udp://', 'http://' or 'https://'")
        if uchars.match(url.netloc) and uchars.match(url.path):
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
        previous_ips = self.ip
        self.ip = []
        try:
            ipv4 = resolver.query(self.host, 'A')
            for rdata in ipv4:
                self.ip.append(str(rdata))
        except Exception:
            pass
        try:
            ipv6 = resolver.query(self.host, 'AAAA')
            for rdata in ipv6:
                self.ip.append(str(rdata))
        except Exception:
            pass
        if not self.ip:  # If DNS query fails, just preserve the previous IPs. Considering showing "Not found" instead.
            self.ip = previous_ips

    def update_ipapi_data(self):
        self.country = []
        self.network = []
        self.country_code = []
        for ip in self.ip:
            ip_data = self.ip_api(ip).splitlines()
            if len(ip_data) == 3:
                self.country.append(ip_data[0])
                self.country_code.append(ip_data[1].lower())
                self.network.append(ip_data[2])

    def scrape(self):
        return scraper.scrape_submitted(self.url)

    def is_up(self):
        self.status = 1
        self.last_uptime = int(time())
        self.historic.append(self.status)

    def is_down(self):
        self.status = 0
        self.last_downtime = int(time())
        self.historic.append(self.status)

    @staticmethod
    def ip_api(ip):
        try:
            response = request.urlopen('http://ip-api.com/line/' + ip + '?fields=country,countryCode,org')
            tracker_info = response.read().decode('utf-8')
            sleep(0.5)  # This wait is to respect the queries per minute limit of IP-API and not get banned
        except IOError:
            tracker_info = 'Error'
        return tracker_info
