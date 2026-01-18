from time import sleep
from typing import NoReturn

import requests

from newTrackon import trackon


def main() -> NoReturn:
    while True:
        tlist = requests.get("https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt")
        trackon.enqueue_new_trackers(tlist.text)
        sleep(86400)
