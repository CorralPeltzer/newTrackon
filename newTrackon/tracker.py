import pprint
import re
import socket
from collections import deque
from datetime import datetime
from ipaddress import ip_address
from logging import getLogger
from time import gmtime, sleep, strftime, time
from typing import Any
from urllib import parse, request

from newTrackon import persistence, scraper

logger = getLogger("newtrackon")

max_downtime: int = 47304000  # 1.5 years


class Tracker:
    url: str
    host: Any
    ips: Any
    latency: Any
    last_checked: Any
    interval: Any
    status: Any
    uptime: Any
    countries: Any
    country_codes: Any
    networks: Any
    historic: Any
    added: Any
    last_downtime: Any
    last_uptime: Any
    to_be_deleted: bool
    status_epoch: Any
    status_readable: Any

    def __init__(
        self,
        url: str,
        host: Any,
        ips: Any,
        latency: Any,
        last_checked: Any,
        interval: Any,
        status: Any,
        uptime: Any,
        countries: Any,
        country_codes: Any,
        networks: Any,
        historic: Any,
        added: Any,
        last_downtime: Any,
        last_uptime: Any,
    ) -> None:
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
        self.status_epoch = None
        self.status_readable = None

    @classmethod
    def from_url(cls, url: str) -> Tracker:
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
        logger.info("Preprocessing %s", url)
        tracker.host = parse.urlparse(tracker.url).hostname
        tracker.update_ips()
        tracker.historic = deque(maxlen=1000)
        date = datetime.now()
        tracker.added = f"{date.day}-{date.month}-{date.year}"
        return tracker

    def update_status(self) -> None:
        try:
            now = int(time())
            if self.last_uptime < (now - max_downtime):
                self.to_be_deleted = True
                raise RuntimeError("Tracker unresponsive for too long, removed")

            self.update_scheme_from_bep_34()
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
            "ip": next(iter(self.ips)) if self.ips else None,
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
            logger.info("%s status is UP", self.url)
        except RuntimeError as e:
            logger.info("%s status is DOWN. Cause: %s", self.url, e)
            debug.update({"info": str(e), "status": 0})
            persistence.raw_data.appendleft(debug)
            self.is_down()
        if self.uptime == 0:
            self.interval = 10800
        self.update_uptime()

    def update_scheme_from_bep_34(self) -> None:
        valid_bep_34, bep_34_info = scraper.get_bep_34(self.host)
        if valid_bep_34:  # Hostname has a valid TXT record as per BEP34
            if not bep_34_info:
                logger.info("Hostname denies connection via BEP34, removing tracker %s", self.url)
                self.to_be_deleted = True
                raise RuntimeError("Host denied connection according to BEP34, removed")
            elif bep_34_info:
                logger.info(
                    "Tracker %s sets protocol and port preferences from BEP34: %s",
                    self.url,
                    bep_34_info,
                )
                parsed_url = parse.urlparse(self.url)
                # Update tracker with the first protocol and URL set by TXT record
                first_bep_34_protocol, first_bep_34_port = bep_34_info[0]
                existing_scheme = parsed_url.scheme
                new_scheme = "udp" if first_bep_34_protocol == "udp" else existing_scheme
                self.url = parsed_url._replace(
                    scheme=new_scheme,
                    netloc=f"{parsed_url.hostname}:{first_bep_34_port}",
                ).geturl()
                return
        else:  # No valid BEP34, attempting existing URL
            return

    def clear_tracker(self, reason: str) -> None:
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

    def validate_url(self) -> None:
        uchars = re.compile(r"^[a-zA-Z0-9_\-\./:]+$")
        url = parse.urlparse(self.url)
        if url.scheme not in ["udp", "http", "https"]:
            raise RuntimeError("Tracker URLs have to start with 'udp://', 'http://' or 'https://'")
        if uchars.match(url.netloc):
            url = url._replace(path="/announce")
            self.url = url.geturl()
        else:
            raise RuntimeError("Invalid announce URL")

    def update_uptime(self) -> None:
        uptime = float(0)
        for s in self.historic:
            uptime += s
        self.uptime = (uptime / len(self.historic)) * 100

    def update_ips(self) -> None:
        self.ips = []
        temp_ips = set()
        try:
            for res in socket.getaddrinfo(self.host, None):
                temp_ips.add(res[4][0])
        except OSError:
            pass
        if temp_ips:  # Order IPs per protocol, IPv6 first
            parsed_ips = []
            [parsed_ips.append(ip_address(ip)) for ip in temp_ips]
            [self.ips.append(str(ip)) for ip in parsed_ips if ip.version == 6]
            [self.ips.append(str(ip)) for ip in parsed_ips if ip.version == 4]
        elif not self.ips:
            self.ips = None
            raise RuntimeError("Can't resolve IP")

    def update_ipapi_data(self) -> None:
        self.countries, self.networks, self.country_codes = [], [], []
        if self.ips:
            for ip in self.ips:
                ip_data = self.ip_api(ip).splitlines()
                if len(ip_data) == 3:
                    self.countries.append(ip_data[0])
                    self.country_codes.append(ip_data[1].lower())
                    self.networks.append(ip_data[2])

    def is_up(self) -> None:
        self.status = 1
        self.last_uptime = int(time())
        self.historic.append(self.status)

    def is_down(self) -> None:
        self.status = 0
        self.last_downtime = int(time())
        self.historic.append(self.status)

    @staticmethod
    def ip_api(ip: str) -> str:
        try:
            response = request.urlopen("http://ip-api.com/line/" + ip + "?fields=country,countryCode,isp")
            tracker_info = response.read().decode("utf-8")
            sleep(1.35)  # Respect the queries per minute limit of IP-API
        except OSError:
            tracker_info = "Error"
        return tracker_info
