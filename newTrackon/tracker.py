import pprint
import re
import socket
from collections import deque
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address, ip_address
from logging import getLogger
from time import sleep, time
from urllib import parse, request

from newTrackon import persistence, scraper
from newTrackon.persistence import HistoryData

logger = getLogger("newtrackon")

max_downtime: int = 47304000  # 1.5 years


class Tracker:
    url: str
    host: str
    ips: list[str] | None
    latency: int | None
    last_checked: int
    interval: int
    status: int
    uptime: float
    countries: list[str] | None
    country_codes: list[str] | None
    networks: list[str] | None
    historic: deque[int]
    added: str
    last_downtime: int
    last_uptime: int
    to_be_deleted: bool
    status_epoch: int | None
    status_readable: str | None

    def __init__(
        self,
        url: str,
        host: str,
        ips: list[str] | None,
        latency: int | None,
        last_checked: int,
        interval: int,
        status: int,
        uptime: float,
        countries: list[str] | None,
        country_codes: list[str] | None,
        networks: list[str] | None,
        historic: deque[int],
        added: str,
        last_downtime: int,
        last_uptime: int,
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
        # Parse the URL to get hostname first (validate_url will normalize it)
        parsed = parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise RuntimeError("Invalid URL: cannot extract hostname")

        date = datetime.now()
        tracker = cls(
            url=url,
            host=hostname,
            ips=None,
            latency=None,
            last_checked=0,
            interval=10800,  # Default interval (3 hours)
            status=0,
            uptime=0.0,
            countries=[],
            country_codes=[],
            networks=[],
            historic=deque(maxlen=1000),
            added=f"{date.day}-{date.month}-{date.year}",
            last_downtime=0,
            last_uptime=0,
        )
        tracker.validate_url()
        logger.info("Preprocessing %s", url)
        # Update host from the validated/normalized URL
        tracker.host = parse.urlparse(tracker.url).hostname or hostname
        tracker.update_ips()
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
        try:
            if parse.urlparse(self.url).scheme == "udp":
                response, _ = scraper.announce_udp(self.url)
            else:
                response = scraper.announce_http(self.url)

            interval = response.get("interval")
            if isinstance(interval, int):
                self.interval = interval
            pretty_data = scraper.redact_origin(pp.pformat(response))
            debug: HistoryData = {
                "url": self.url,
                "ip": next(iter(self.ips)) if self.ips else "",
                "time": int(t1),
                "info": pretty_data,
                "status": 1,
            }
            persistence.raw_data.appendleft(debug)
            self.latency = int((time() - t1) * 1000)
            self.is_up()
            logger.info("%s status is UP", self.url)
        except RuntimeError as e:
            logger.info("%s status is DOWN. Cause: %s", self.url, e)
            debug_down: HistoryData = {
                "url": self.url,
                "ip": next(iter(self.ips)) if self.ips else "",
                "time": int(t1),
                "info": str(e),
                "status": 0,
            }
            persistence.raw_data.appendleft(debug_down)
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
            else:
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
        debug: HistoryData = {
            "url": self.url,
            "ip": "",
            "time": int(time()),
            "status": 0,
            "info": reason,
        }
        persistence.raw_data.appendleft(debug)

    def validate_url(self) -> None:
        uchars = re.compile(r"^[a-zA-Z0-9_\-\./:]+$")
        url = parse.urlparse(self.url)
        if url.scheme not in ["udp", "http", "https"]:
            raise RuntimeError("Tracker URLs have to start with 'udp://', 'http://' or 'https://'")
        netloc = url.netloc
        assert isinstance(netloc, str)
        if uchars.match(netloc):
            url = url._replace(path="/announce")
            new_url = url.geturl()
            assert isinstance(new_url, str)
            self.url = new_url
        else:
            raise RuntimeError("Invalid announce URL")

    def update_uptime(self) -> None:
        uptime = float(0)
        for s in self.historic:
            uptime += s
        self.uptime = (uptime / len(self.historic)) * 100

    def update_ips(self) -> None:
        self.ips = []
        temp_ips: set[str] = set()
        try:
            for res in socket.getaddrinfo(self.host, None):
                temp_ips.add(str(res[4][0]))
        except OSError:
            pass
        if temp_ips:  # Order IPs per protocol, IPv6 first
            parsed_ips: list[IPv4Address | IPv6Address] = []
            for ip in temp_ips:
                parsed_ips.append(ip_address(ip))
            # Check that all IPs are globally routable
            for ip in parsed_ips:
                if not ip.is_global:
                    self.ips = None
                    self.to_be_deleted = True
                    raise RuntimeError(f"IP {ip} is not globally routable, removed")
            for ip in parsed_ips:
                if ip.version == 6:
                    self.ips.append(str(ip))
            for ip in parsed_ips:
                if ip.version == 4:
                    self.ips.append(str(ip))
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
