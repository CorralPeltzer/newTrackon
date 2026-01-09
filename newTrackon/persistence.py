import json
from collections import deque
from os import path
from typing import Any

submitted_trackers: deque[Any] = deque(maxlen=10000)
raw_history_file: str = "data/raw_data.json"
submitted_history_file: str = "data/submitted_data.json"
raw_data: deque[dict[str, Any]]
submitted_data: deque[dict[str, Any]]


if path.exists(raw_history_file):
    raw_data = deque(json.load(open(raw_history_file)), maxlen=600)
else:
    raw_data = deque(maxlen=600)

if path.exists(submitted_history_file):
    submitted_data = deque(json.load(open(submitted_history_file)), maxlen=600)
else:
    submitted_data = deque(maxlen=600)


def save_deque_to_disk(obj: deque[dict[str, Any]], filename: str) -> None:
    json.dump(list(obj), open(filename, "w"))
