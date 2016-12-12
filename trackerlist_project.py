import tracker
import requests
from time import sleep


def main():
    while True:
        tlist = requests.get('https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_all.txt')
        tracker.enqueue_new_trackers(tlist.text)
        sleep(86400)
