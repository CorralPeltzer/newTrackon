import pprint
import re
import socket
from collections import deque
from datetime import datetime
from ipaddress import ip_address
from logging import getLogger
from time import time, sleep, gmtime, strftime
from urllib import request, parse

from newTrackon import scraper, persistence

logger = getLogger("newtrackon_logger")

max_downtime = 47304000  # 1.5 years


class Tracker:
    def __init__(
        self,
        url,
        host,
        ips,
        latency,
        last_checked,
        interval,
        status,
        uptime,
        countries,
        country_codes,
        networks,
        historic,
        added,
        last_downtime,
        last_uptime,
    ):
        self.url = url
        self.host = host
        self.ips = ips
        self.latency = latency
        self.last_checked = last_checked
        self.interval = interval
        self.status = status
        self.uptime = uptime
        self.countries = countries
        self.country_codes = country_codes
        self.networks = networks
        self.historic = historic
        self.added = added
        self.last_downtime = last_downtime
        self.last_uptime = last_uptime
        self.to_be_deleted = False

    @classmethod
    def from_url(cls, url):
        tracker = cls(
            url,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            [],
            [],
            [],
            None,
            None,
            None,
            None,
        )
        tracker.validate_url()
        logger.info(f"Preprocessing {url}")
        tracker.host = parse.urlparse(tracker.url).hostname
        tracker.update_ips()
        tracker.historic = deque(maxlen=1000)
        date = datetime.now()
        tracker.added = "{}-{}-{}".format(date.day, date.month, date.year)
        return tracker

    def update_status(self):
        try:
            now = int(time())
            if self.last_uptime < (now - max_downtime):
                self.to_be_deleted = True
                raise RuntimeError("Tracker unresponsive for too long, removed")

            self.update_from_bep_34()
            self.update_ips()
        except RuntimeError as reason:
            self.clear_tracker(reason=str(reason))
            return

        self.update_ipapi_data()
        self.last_checked = int(time())
        pp = pprint.PrettyPrinter(width=999999, compact=True)
        t1 = time()
        debug = {
            "url": self.url,
            "ip": list(self.ips)[0],
            "time": strftime("%H:%M:%S UTC", gmtime(t1)),
        }
        try:
            if parse.urlparse(self.url).scheme == "udp":
                response, _ = scraper.announce_udp(self.url)
            else:
                response = scraper.announce_http(self.url)

            self.interval = response["interval"]
            pretty_data = scraper.redact_origin(pp.pformat(response))
            debug["info"] = pretty_data
            persistence.raw_data.appendleft(debug)
            self.latency = int((time() - t1) * 1000)
            self.is_up()
            debug["status"] = 1
            logger.info(f"{self.url} status is UP")
        except RuntimeError as e:
            logger.info(f"{self.url} status is DOWN. Cause: {str(e)}")
            debug.update({"info": str(e), "status": 0})
            persistence.raw_data.appendleft(debug)
            self.is_down()
        if self.uptime == 0:
            self.interval = 10800
        self.update_uptime()

    def update_from_bep_34(self):
        valid_bep_34, bep_34_info = scraper.get_bep_34(self.host)
        if valid_bep_34:  # Hostname has a valid TXT record as per BEP34
            if not bep_34_info:
                logger.info(
                    f"Hostname denies connection via BEP34, removing tracker {self.url}"
                )
                self.to_be_deleted = True
                raise RuntimeError(
                    "Tracker denied connection according to BEP34, removed"
                )
            elif bep_34_info:
                logger.info(
                    f"Tracker {self.url} sets protocol and port preferences from BEP34: {str(bep_34_info)}"
                )
                parsed_url = parse.urlparse(self.url)
                # Update tracker with the first protocol and URL set by TXT record
                first_bep_34_result = bep_34_info[0]
                new_scheme = "https" if first_bep_34_result[0] == "tcp" else "udp"
                self.url = parsed_url._replace(
                    scheme=new_scheme,
                    netloc="{}:{}".format(parsed_url.hostname, first_bep_34_result[1]),
                ).geturl()
                return
        else:  # No valid BEP34, attempting existing URL
            return

    def clear_tracker(self, reason):
        self.countries, self.networks, self.country_codes = None, None, None
        self.latency = None
        self.last_checked = int(time())
        self.is_down()
        self.update_uptime()
        if self.uptime == 0:
            self.interval = 10800
        debug = {
            "url": self.url,
            "ip": None,
            "time": strftime("%H:%M:%S UTC", gmtime(time())),
            "status": 0,
            "info": reason,
        }
        persistence.raw_data.appendleft(debug)

    def validate_url(self):
        uchars = re.compile("^[a-zA-Z0-9_\-\./:]+$")
        url = parse.urlparse(self.url)
        if url.scheme not in ["udp", "http", "https"]:
            raise RuntimeError(
                "Tracker URLs have to start with 'udp://', 'http://' or 'https://'"
            )
        if uchars.match(url.netloc):
            url = url._replace(path="/announce")
            self.url = url.geturl()
        else:
            raise RuntimeError("Invalid announce URL")

    def update_uptime(self):
        uptime = float(0)
        for s in self.historic:
            uptime += s
        self.uptime = (uptime / len(self.historic)) * 100

    def update_ips(self):
        self.ips = []
        temp_ips = set()
        try:
            for res in socket.getaddrinfo(self.host, None):
                temp_ips.add(res[4][0])
        except socket.error:
            pass
        if temp_ips:  # Order IPs per protocol, IPv6 first
            parsed_ips = []
            [parsed_ips.append(ip_address(ip)) for ip in temp_ips]
            [self.ips.append(str(ip)) for ip in parsed_ips if ip.version == 6]
            [self.ips.append(str(ip)) for ip in parsed_ips if ip.version == 4]
        elif not self.ips:
            self.ips = None
            raise RuntimeError("Can't resolve IP")

    def update_ipapi_data(self):
        self.countries, self.networks, self.country_codes = [], [], []
        for ip in self.ips:
            ip_data = self.ip_api(ip).splitlines()
            if len(ip_data) == 3:
                self.countries.append(ip_data[0])
                self.country_codes.append(ip_data[1].lower())
                self.networks.append(ip_data[2])

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
            response = request.urlopen(
                "http://ip-api.com/line/" + ip + "?fields=country,countryCode,isp"
            )
            tracker_info = response.read().decode("utf-8")
            sleep(1.35)  # Respect the queries per minute limit of IP-API
        except IOError:
            tracker_info = "Error"
        return tracker_info
