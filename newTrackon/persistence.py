from os import path
from collections import deque
import json

submitted_trackers = deque(maxlen=10000)
raw_history_file = "data/raw_data.json"
submitted_history_file = "data/submitted_data.json"

if path.exists(raw_history_file):
    raw_data = deque(json.load(open(raw_history_file, "r")), maxlen=600)
else:
    raw_data = deque(maxlen=600)
if path.exists(submitted_history_file):
    submitted_data = deque(json.load(open(submitted_history_file, "r")), maxlen=600)
else:
    submitted_data = deque(maxlen=600)


def save_deque_to_disk(obj, filename):
    json.dump(list(obj), open(filename, "w"))
